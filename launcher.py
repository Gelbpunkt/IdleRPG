"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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

from enum import Enum
from pathlib import Path
from time import time
from typing import Iterable, Optional, Tuple

import aiohttp
import aioredis
import orjson

from utils import random
from utils.config import ConfigLoader

if sys.version_info < (3, 9):
    raise Exception("IdleRPG requires Python 3.9")

config = ConfigLoader("config.toml")

__version__ = "1.0.0"

BOT_FILE = "idlerpg.py"

payload = {
    "Authorization": f"Bot {config.bot.token}",
    "User-Agent": f"IdleRPG launcher (v{__version__})",
}


async def get_gateway_info() -> Tuple[int, int]:
    async with aiohttp.ClientSession() as session, session.get(
        "https://discord.com/api/gateway/bot", headers=payload
    ) as req:
        gateway_json = await req.json()
    shard_count: int = gateway_json["shards"]
    max_concurrency: int = gateway_json["session_start_limit"]["max_concurrency"]
    return shard_count, max_concurrency


async def get_app_info() -> tuple[str, int]:
    async with aiohttp.ClientSession() as session, session.get(
        "https://discord.com/api/oauth2/applications/@me", headers=payload
    ) as req:
        response = await req.json()
    return response["name"], response["id"]


def get_cluster_list(shards: int) -> list[list[int]]:
    return [
        list(range(0, shards)[i : i + config.launcher.shards_per_cluster])
        for i in range(0, shards, config.launcher.shards_per_cluster)
    ]


class Status(Enum):
    Initialized = "initialized"
    Running = "running"
    Stopped = "stopped"


class Instance:
    def __init__(
        self,
        instance_id: int,
        shard_list: list[int],
        shard_count: int,
        name: str,
        main: Optional[Main] = None,
    ):
        self.main = main
        self.shard_count = shard_count  # overall shard count
        self.shard_list = shard_list
        self.started_at = 0.0
        self.id = instance_id
        self.name = name
        self.command = (
            f'{sys.executable} -OO {Path.cwd() / BOT_FILE} "{shard_list}" {shard_count}'
            f" {self.id} {self.name}"
        )
        self._process: Optional[asyncio.subprocess.Process] = None
        self.status = Status.Initialized
        self.future: asyncio.Future[None] = asyncio.Future()

    @property
    def is_active(self) -> bool:
        return self._process is not None and not self._process.returncode

    def process_finished(self, stderr: bytes) -> None:
        if self._process is None:
            raise RuntimeError(
                "This callback cannot run without a process that exited."
            )
        print(
            f"[Cluster #{self.id} ({self.name})] Exited with code"
            f" [{self._process.returncode}]"
        )
        if self._process.returncode == 0:
            print(f"[Cluster #{self.id} ({self.name})] Stopped gracefully")
            self.future.set_result(None)
        elif self.status == Status.Stopped:
            print(
                f"[Cluster #{self.id} ({self.name})] Stopped by command, not"
                " restarting"
            )
            self.future.set_result(None)
        else:
            decoded_stderr = "\n".join(stderr.decode("utf-8").split("\n"))
            print(f"[Cluster #{self.id} ({self.name})] STDERR: {decoded_stderr}")
            print(f"[Cluster #{self.id} ({self.name})] Restarting...")
            asyncio.create_task(self.start())

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
        asyncio.create_task(self._run())
        print(f"[Cluster #{self.id}] Started successfully")
        self.status = Status.Running

    async def stop(self) -> None:
        self.status = Status.Stopped
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )
        self._process.terminate()
        await asyncio.sleep(5)
        if self.is_active:
            self._process.kill()
            print(f"[Cluster #{self.id} ({self.name})] Got force killed")
        else:
            print(f"[Cluster #{self.id} ({self.name})] Killed gracefully")

    async def restart(self) -> None:
        if self.is_active:
            await self.stop()
        await self.start()

    async def _run(self) -> None:
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )
        _, stderr = await self._process.communicate()
        self.process_finished(stderr)

    def __repr__(self) -> str:
        return (
            f"<Cluster ID={self.id} name={self.name}, active={self.is_active},"
            f" shards={self.shard_list}, started={self.started_at}>"
        )


class Main:
    def __init__(self) -> None:
        self.instances: list[Instance] = []
        pool = aioredis.ConnectionPool.from_url(
            "redis://localhost",
            max_connections=2,
        )
        self.redis = aioredis.Redis(connection_pool=pool)

    def get_instance(self, iterable: Iterable[Instance], id: int) -> Instance:
        for elem in iterable:
            if getattr(elem, "id") == id:
                return elem
        raise ValueError("Unknown instance")

    async def event_handler(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(config.database.redis_shard_announce_channel)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = orjson.loads(message["data"])
            except orjson.JSONDecodeError:
                continue
            if payload.get("scope") != "launcher" or not payload.get("action"):
                continue  # not the launcher's task
            args = payload.get("args", {})
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
                asyncio.create_task(instance.restart())
            elif payload["action"] == "stop" and id_exists:
                print(f"[INFO] Stop requested for cluster #{id_}")
                asyncio.create_task(instance.stop())
            elif payload["action"] == "start" and id_exists:
                print(f"[INFO] Start requested for cluster #{id_}")
                asyncio.create_task(instance.start())
            elif payload["action"] == "statuses" and payload.get("command_id"):
                statuses = {}
                for instance in self.instances:
                    statuses[str(instance.id)] = {
                        "active": instance.is_active,
                        "status": instance.status.value,
                        "name": instance.name,
                        "started_at": instance.started_at,
                        "shard_list": instance.shard_list,
                    }
                await self.redis.execute_command(
                    "PUBLISH",
                    config.database.redis_shard_announce_channel,
                    orjson.dumps(
                        {"command_id": payload["command_id"], "output": statuses}
                    ),
                )

    async def launch(self) -> None:
        with open("assets/data/names.txt", "r") as f:
            names = f.read().splitlines()

        asyncio.create_task(self.event_handler())

        (recommended_shard_count, max_concurrency) = await get_gateway_info()
        shard_count = recommended_shard_count + config.launcher.additional_shards
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
            instance = Instance(i, shard_list, shard_count, name, main=self)
            await instance.start()
            self.instances.append(instance)
            await asyncio.sleep(
                5 / max_concurrency / config.launcher.shards_per_cluster
            )

        try:
            await asyncio.wait([i.future for i in self.instances])
        except Exception:
            print("[MAIN] Shutdown requested, stopping clusters")
            for instance in self.instances:
                await instance.stop()


if __name__ == "__main__":
    try:
        asyncio.run(Main().launch())
    except KeyboardInterrupt:
        pass
