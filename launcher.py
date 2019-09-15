"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio
import json
import random
import sys

from pathlib import Path
from time import time
from traceback import print_exc

import aiohttp
import aioredis

from config import token, shard_per_cluster, additional_shards, shard_announce_channel

if sys.version_info < (3, 8):
    raise Exception("IdleRPG requires Python 3.8")

__version__ = "0.7.0a"

BOT_FILE = "idlerpg.py"

payload = {
    "Authorization": f"Bot {token}",
    "User-Agent": f"IdleRPG launcher (v{__version__})",
}


async def get_shard_count():
    async with aiohttp.ClientSession() as session, session.get(
        "https://discordapp.com/api/gateway/bot", headers=payload
    ) as req:
        return (await req.json()).get("shards")


async def get_app_info():
    async with aiohttp.ClientSession() as session, session.get(
        "https://discordapp.com/api/oauth2/applications/@me", headers=payload
    ) as req:
        response = await req.json()
    return response["name"], response["id"]


def get_cluster_list(shards: int):
    return [
        list(range(0, shards)[i : i + shard_per_cluster])
        for i in range(0, shards, shard_per_cluster)
    ]


class Instance:
    def __init__(
        self,
        instance_id: int,
        shard_list: list,
        shard_count: int,
        name: str,
        loop,
        main=None,
    ):
        self.main = main
        self.loop = loop
        print(shard_list)
        self.shard_count = shard_count  # overall shard count
        self.started_at = None
        self.id = instance_id
        self.name = name
        self.command = f'{sys.executable} {Path.cwd() / BOT_FILE} "{shard_list}" {shard_count} {self.id} {self.name}'
        self._process = None
        loop.create_task(self.start())

    @property
    def is_active(self):
        if self._process is not None and not self._process.returncode:
            return True
        return False

    async def start(self):
        if self.is_active:
            print(f"[Cluster #{self.id} ({self.name})] The cluster is already up")
            return
        self.started_at = time()
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            loop=self.loop,
        )
        task = self.loop.create_task(self._run())
        print(f"[Cluster #{self.id}] Started successfully")
        task.add_done_callback(
            self.main.dead_process_handler
        )  # TODO: simply use it inline

    async def stop(self):
        self._process.terminate()
        await asyncio.sleep(5)
        if self.is_active:
            self._process.kill()
            print(f"[Cluster #{self.id} ({self.name})] Got force killed")
            return
        print(f"[Cluster #{self.id} ({self.name})] Killed gracefully")

    async def restart(self):
        if self.is_active:
            await self.stop()
        await self.start()

    async def _run(self):
        stdout, stderr = await self._process.communicate()
        return self, stdout, stderr

    def __repr__(self):
        return f"<Cluster ID={self.id} name={self.name}, active={self.is_active}, shards={self.shard_list}, started={self.started_at}>"


class Main:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.instances = []
        self.redis = None

    def dead_process_handler(self, result):
        instance, stdout, stderr = result.result()
        print(
            f"[Cluster #{instance.id} ({instance.name})] Exited with code [{instance._process.returncode}]"
        )
        if instance._process.returncode == 0:
            print(f"[Cluster #{instance.id} ({instance.name})] Stopped gracefully")
        else:
            stderr = "\n".join(stderr.decode("utf-8").split("\n")[-20:])
            print(
                f"[Cluster #{instance.id} ({instance.name})] STDERR (last 20 lines): {stderr}"
            )
            print(f"[Cluster #{instance.id} ({instance.name})] Restarting...")
            instance.loop.create_task(instance.start())

    def get_instance(iterable, id: int):
        for elem in iterable:
            if getattr(elem, "id") == id:
                return elem
        return None

    async def event_handler(self):
        try:
            self.redis = await aioredis.create_pool(
                "redis://localhost", minsize=1, maxsize=2
            )
        except aioredis.RedisError:
            print_exc()
            exit("[ERROR] Redis must be installed properly")

        channel = self.redis.pubsub_channels[bytes(shard_announce_channel, "utf-8")]
        while await channel.wait_message():
            try:
                payload = await channel.get_json(encoding="utf-8")
            except json.decoder.JSONDecodeError:
                return  # not a valid JSON message
            if payload.get("scope") != "launcher" or not payload.get("action"):
                return  # not the launcher's task
            if payload["action"] == "restart":
                self.loop.create_task(
                    self.get_instance(self.instances, payload["id"]).restart()
                )
                return
            if payload["action"] == "stop":
                self.loop.create_task(
                    self.get_instance(self.instances, payload["id"]).stop()
                )
            if payload["action"] == "start":
                self.loop.create_task(
                    self.get_instance(self.instances, payload["id"]).start()
                )
            if payload["action"] == "statuses" and payload.get("command_id"):
                statuses = {}
                for instance in self.instances:
                    payload[instance.name] = instance.is_active
                await self.redis.execute(
                    "PUBLISH",
                    communication_channel,
                    json.dumps(
                        {"command_id": payload["command_id"], "output": statuses}
                    ),
                )

    async def launch(self):
        loop.create_task(self.event_handler())
        shard_count = await get_shard_count() + additional_shards
        clusters = get_cluster_list(shard_count)
        name, id = await get_app_info()
        print(f"[MAIN] Starting {name} ({id}) - {len(clusters)} clusters")
        used_names = []
        for i, shard_list in enumerate(clusters, 1):
            if not shard_list:
                continue
            name = None
            while name is None or name in used_names:
                name = random.choice(names)
            used_names.append(name)
            self.instances.append(
                Instance(i, shard_list, shard_count, name, self.loop, main=self)
            )
            await asyncio.sleep(shard_per_cluster * 5)


if __name__ == "__main__":
    with open("assets/data/names.txt", "r") as f:
        names = f.read().splitlines()

    if sys.platform.startswith("win"):
        loop = (
            asyncio.ProactorEventLoop()
        )  # subprocess pipes only work with this under Win
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    loop.create_task(Main().launch())
    try:
        loop.run_forever()
    except KeyboardInterrupt:

        def shutdown_handler(_loop, context):
            if "exception" not in context or not isinstance(
                context["exception"], asyncio.CancelledError
            ):
                _loop.default_exception_handler(context)  # TODO: fix context

        loop.set_exception_handler(shutdown_handler)
        tasks = asyncio.gather(
            *asyncio.all_tasks(loop=loop), loop=loop, return_exceptions=True
        )
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()

        while not tasks.done() and not loop.is_closed():
            loop.run_forever()
    finally:
        if hasattr(loop, "shutdown_asyncgens"):
            loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
