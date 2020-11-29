"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

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
from __future__ import annotations

import asyncio
import sys

from pathlib import Path
from socket import socket
from time import time
from traceback import print_exc
from typing import Any, Iterable, Optional, Union

import aiohttp
import aioredis
import orjson

from config import additional_shards, shard_announce_channel, shard_per_cluster, token

from utils import random

if sys.version_info < (3, 8):
    raise Exception("IdleRPG requires Python 3.8")

__version__ = "1.0.0"

BOT_FILE = "idlerpg.py"

payload = {
    "Authorization": f"Bot {token}",
    "User-Agent": f"IdleRPG launcher (v{__version__})",
}


async def get_shard_count() -> int:
    async with aiohttp.ClientSession() as session, session.get(
        "https://discord.com/api/gateway/bot", headers=payload
    ) as req:
        gateway_json = await req.json()
    shard_count: int = gateway_json["shards"]
    return shard_count


async def get_app_info() -> tuple[str, int]:
    async with aiohttp.ClientSession() as session, session.get(
        "https://discord.com/api/oauth2/applications/@me", headers=payload
    ) as req:
        response = await req.json()
    return response["name"], response["id"]


def get_cluster_list(shards: int) -> list[list[int]]:
    return [
        list(range(0, shards)[i : i + shard_per_cluster])
        for i in range(0, shards, shard_per_cluster)
    ]


class Instance:
    def __init__(
        self,
        instance_id: int,
        shard_list: list[int],
        shard_count: int,
        name: str,
        loop: asyncio.AbstractEventLoop,
        main: Optional["Main"] = None,
    ):
        self.main = main
        self.loop = loop
        self.shard_count = shard_count  # overall shard count
        self.shard_list = shard_list
        self.started_at = 0.0
        self.id = instance_id
        self.name = name
        self.command = (
            f'{sys.executable} {Path.cwd() / BOT_FILE} "{shard_list}" {shard_count}'
            f" {self.id} {self.name}"
        )
        self._process: Optional[asyncio.subprocess.Process] = None
        self.status = "initialized"
        loop.create_task(self.start())

    @property
    def is_active(self) -> bool:
        if self._process is not None and not self._process.returncode:
            return True
        return False

    async def start(self) -> None:
        if self.is_active:
            print(f"[Cluster #{self.id} ({self.name})] The cluster is already up")
            return
        if self.main is None:
            raise RuntimeError("This cannot be possible.")
        self.started_at = time()
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        task = self.loop.create_task(self._run())
        print(f"[Cluster #{self.id}] Started successfully")
        self.status = "running"
        task.add_done_callback(
            self.main.dead_process_handler
        )  # TODO: simply use it inline

    async def stop(self) -> None:
        self.status = "stopped"
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )
        self._process.terminate()
        await asyncio.sleep(5)
        if self.is_active:
            self._process.kill()
            print(f"[Cluster #{self.id} ({self.name})] Got force killed")
            return
        print(f"[Cluster #{self.id} ({self.name})] Killed gracefully")

    async def restart(self) -> None:
        if self.is_active:
            await self.stop()
        await self.start()

    async def _run(self) -> tuple["Instance", bytes, bytes]:
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )
        stdout, stderr = await self._process.communicate()
        return self, stdout, stderr

    def __repr__(self) -> str:
        return (
            f"<Cluster ID={self.id} name={self.name}, active={self.is_active},"
            f" shards={self.shard_list}, started={self.started_at}>"
        )


class Main:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.instances: list[Instance] = []
        self.redis: Optional[aioredis.Redis] = None

    def dead_process_handler(
        self, result: asyncio.Future[tuple[Instance, bytes, bytes]]
    ) -> None:
        instance, _, stderr = result.result()
        if instance._process is None:
            raise RuntimeError(
                "This callback cannot run without a process that exited."
            )
        print(
            f"[Cluster #{instance.id} ({instance.name})] Exited with code"
            f" [{instance._process.returncode}]"
        )
        if instance._process.returncode == 0:
            print(f"[Cluster #{instance.id} ({instance.name})] Stopped gracefully")
        elif instance.status == "stopped":
            print(
                f"[Cluster #{instance.id} ({instance.name})] Stopped by command, not"
                " restarting"
            )
        else:
            decoded_stderr = "\n".join(stderr.decode("utf-8").split("\n"))
            print(
                f"[Cluster #{instance.id} ({instance.name})] STDERR: {decoded_stderr}"
            )
            print(f"[Cluster #{instance.id} ({instance.name})] Restarting...")
            instance.loop.create_task(instance.start())

    def get_instance(self, iterable: Iterable[Instance], id: int) -> Instance:
        for elem in iterable:
            if getattr(elem, "id") == id:
                return elem
        raise ValueError("Unknown instance")

    async def event_handler(self) -> None:
        try:
            self.redis = await aioredis.create_pool(
                "redis://localhost", minsize=1, maxsize=2
            )
        except aioredis.RedisError:
            print_exc()
            exit("[ERROR] Redis must be installed properly")

        await self.redis.execute_pubsub("SUBSCRIBE", shard_announce_channel)
        channel = self.redis.pubsub_channels[bytes(shard_announce_channel, "utf-8")]
        while await channel.wait_message():
            try:
                payload = await channel.get_json(encoding="utf-8")
            except orjson.JSONDecodeError:
                continue  # not a valid JSON message
            if payload.get("scope") != "launcher" or not payload.get("action"):
                continue  # not the launcher's task
            # parse the JSON args
            if (args := payload.get("args", {})):
                args = orjson.loads(args)
            id_ = args.get("id")
            id_exists = id_ is not None

            if id_exists:
                try:
                    instance = self.get_instance(self.instances, id_)
                except ValueError:
                    # unknown instance
                    continue

            if payload["action"] == "restart" and id_exists:
                print(f"[INFO] Restart requested for cluster #{id_}")
                self.loop.create_task(instance.restart())
            elif payload["action"] == "stop" and id_exists:
                print(f"[INFO] Stop requested for cluster #{id_}")
                self.loop.create_task(instance.stop())
            elif payload["action"] == "start" and id_exists:
                print(f"[INFO] Start requested for cluster #{id_}")
                self.loop.create_task(instance.start())
            elif payload["action"] == "statuses" and payload.get("command_id"):
                statuses = {}
                for instance in self.instances:
                    statuses[str(instance.id)] = {
                        "active": instance.is_active,
                        "status": instance.status,
                        "name": instance.name,
                        "started_at": instance.started_at,
                        "shard_list": instance.shard_list,
                    }
                await self.redis.execute(
                    "PUBLISH",
                    shard_announce_channel,
                    orjson.dumps(
                        {"command_id": payload["command_id"], "output": statuses}
                    ),
                )

    async def launch(self) -> None:
        loop.create_task(self.event_handler())
        shard_count = await get_shard_count() + additional_shards
        clusters = get_cluster_list(shard_count)
        name, id = await get_app_info()
        print(f"[MAIN] Starting {name} ({id}) - {len(clusters)} clusters")
        used_names = []
        for i, shard_list in enumerate(clusters, 1):
            if not shard_list:
                continue
            name = ""
            while name == "" or name in used_names:
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

        def shutdown_handler(
            _loop: asyncio.AbstractEventLoop,
            context: dict[
                str,
                Union[
                    str,
                    Exception,
                    asyncio.Future[Any],
                    asyncio.Handle,
                    asyncio.Protocol,
                    asyncio.Transport,
                    socket,
                ],
            ],
        ) -> None:
            # all the types are from https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_exception_handler
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
