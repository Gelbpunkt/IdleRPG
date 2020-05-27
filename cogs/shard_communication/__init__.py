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
import asyncio
import json

from datetime import datetime, timedelta
from time import time
from uuid import uuid4

import discord

from async_timeout import timeout
from discord.ext import commands

from utils.eval import evaluate as _evaluate
from utils.i18n import _, locale_doc
from utils.misc import nice_join


# Cross-process cooldown check (pass this to commands)
def user_on_cooldown(cooldown: int, identifier: str = None):
    async def predicate(ctx):
        if identifier is None:
            cmd_id = ctx.command.qualified_name
        else:
            cmd_id = identifier
        command_ttl = await ctx.bot.redis.execute("TTL", f"cd:{ctx.author.id}:{cmd_id}")
        if command_ttl == -2:
            await ctx.bot.redis.execute(
                "SET", f"cd:{ctx.author.id}:{cmd_id}", cmd_id, "EX", cooldown,
            )
            return True
        else:
            raise commands.CommandOnCooldown(ctx, command_ttl)
            return False

    return commands.check(predicate)  # TODO: Needs a redesign


# Cross-process cooldown check (pass this to commands)
def guild_on_cooldown(cooldown: int):
    async def predicate(ctx):
        guild = getattr(ctx, "character_data", None)
        if not guild:
            guild = await ctx.bot.pool.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
            )
        else:
            guild = guild["guild"]
        command_ttl = await ctx.bot.redis.execute(
            "TTL", f"guildcd:{guild}:{ctx.command.qualified_name}"
        )
        if command_ttl == -2:
            await ctx.bot.redis.execute(
                "SET",
                f"guildcd:{guild}:{ctx.command.qualified_name}",
                ctx.command.qualified_name,
                "EX",
                cooldown,
            )
            return True
        else:
            raise commands.CommandOnCooldown(ctx, command_ttl)
            return False

    return commands.check(predicate)


# Cross-process cooldown check (pass this to commands)
def alliance_on_cooldown(cooldown: int):
    async def predicate(ctx):
        data = getattr(ctx, "character_data", None)
        if not data:
            alliance = await ctx.bot.pool.fetchval(
                'SELECT alliance FROM guild WHERE "id"=(SELECT guild FROM profile WHERE'
                ' "user"=$1);',
                ctx.author.id,
            )
        else:
            guild = data["guild"]
            alliance = await ctx.bot.pool.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', guild
            )

        command_ttl = await ctx.bot.redis.execute(
            "TTL", f"alliancecd:{alliance}:{ctx.command.qualified_name}"
        )
        if command_ttl == -2:
            await ctx.bot.redis.execute(
                "SET",
                f"alliancecd:{alliance}:{ctx.command.qualified_name}",
                ctx.command.qualified_name,
                "EX",
                cooldown,
            )
            return True
        else:
            raise commands.CommandOnCooldown(ctx, command_ttl)
            return False

    return commands.check(predicate)


def next_day_cooldown():
    async def predicate(ctx):
        command_ttl = await ctx.bot.redis.execute(
            "TTL", f"cd:{ctx.author.id}:{ctx.command.qualified_name}"
        )
        if command_ttl == -2:
            ctt = int(
                86400 - (time() % 86400)
            )  # Calculate the number of seconds until next UTC midnight
            await ctx.bot.redis.execute(
                "SET",
                f"cd:{ctx.author.id}:{ctx.command.qualified_name}",
                ctx.command.qualified_name,
                "EX",
                ctt,
            )
            return True
        else:
            raise commands.CommandOnCooldown(ctx, command_ttl)
            return False

    return commands.check(predicate)  # TODO: Needs a redesign


class Sharding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.communication_channel = bot.config.shard_announce_channel
        self.router = None
        bot.loop.create_task(self.register_sub())
        self._messages = dict()
        """
        _messages should be a dict with the syntax {"<command_id>": [outputs]}
        """

    def cog_unload(self):
        self.bot.loop.create_task(self.unregister_sub())

    async def register_sub(self):
        if (
            not bytes(self.communication_channel, "utf-8")
            in self.bot.redis.pubsub_channels
        ):
            await self.bot.redis.execute_pubsub("SUBSCRIBE", self.communication_channel)
        self.router = self.bot.loop.create_task(self.event_handler())

    async def unregister_sub(self):
        if self.router and not self.router.cancelled:
            self.router.cancel()
        await self.bot.redis.execute_pubsub("UNSUBSCRIBE", self.communication_channel)

    async def event_handler(self):
        """
        main router

        Possible messages to come:
        {"scope":<bot/launcher>, "action": "<name>", "args": "<dict of args>", "command_id": "<uuid4>"}
        {"output": "<string>", "command_id": "<uuid4>"}
        """
        channel = self.bot.redis.pubsub_channels[
            bytes(self.communication_channel, "utf-8")
        ]
        while await channel.wait_message():
            try:
                payload = await channel.get_json(encoding="utf-8")
            except json.JSONDecodeError:
                continue  # not a valid JSON message
            if payload.get("action") and hasattr(self, payload.get("action")):
                if payload.get("scope") != "bot":
                    continue  # it's not our cup of tea
                if payload.get("args"):
                    self.bot.loop.create_task(
                        getattr(self, payload["action"])(
                            **json.loads(payload["args"]),
                            command_id=payload["command_id"],
                        )
                    )
                else:
                    self.bot.loop.create_task(
                        getattr(self, payload["action"])(
                            command_id=payload["command_id"]
                        )
                    )
            if payload.get("output") and payload["command_id"] in self._messages:
                self._messages[payload["command_id"]].append(payload["output"])

    async def temp_ban(self, user_id: int, command_id: int):
        self.bot.bans.append(user_id)

    async def temp_unban(self, user_id: int, command_id: int):
        self.bot.bans.remove(user_id)

    async def guild_count(self, command_id: str):
        payload = {"output": len(self.bot.guilds), "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def send_latency_and_shard_count(self, command_id: str):
        payload = {
            "output": {
                f"{self.bot.cluster_id}": [
                    self.bot.cluster_name,
                    self.bot.shard_ids,
                    round(self.bot.latency * 1000),
                ]
            },
            "command_id": command_id,
        }
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def evaluate(self, code, command_id: str):
        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.split("\n")[1:-1])
        code = code.strip("` \n")
        payload = {"output": await _evaluate(self.bot, code), "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def latency(self, command_id: str):
        payload = {
            "output": round(self.bot.latency * 1000, 2),
            "command_id": command_id,
        }
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def wait_for_dms(self, event, check, timeout, command_id: str):
        """
        This uses socket raw events
        The predicate is a dictionary with key-values from the event data to match 1:1
        """
        if 0 not in self.bot.shards.keys():
            return
        if event == "reaction_add":
            event = "MESSAGE_REACTION_ADD"
        elif event == "message":
            event = "MESSAGE_CREATE"

        check = {k: str(v) if isinstance(v, int) else v for k, v in check.items()}

        def data_matches(dict1, dict2):
            for key, val in dict1.items():
                val2 = dict2[key]
                if isinstance(val2, dict):
                    if not data_matches(val, val2):
                        return False
                elif isinstance(val, (list, set)):
                    if val2 not in val:
                        return False
                elif val2 != val:
                    return False
            return True

        def pred(e):
            return e["op"] == 0 and e["t"] == event and data_matches(check, e["d"])

        out = await self.bot.wait_for("socket_response", check=pred, timeout=timeout)
        payload = {"output": out["d"], "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def handler(
        self,
        action: str,
        expected_count: int,
        args: dict = {},
        _timeout: int = 2,
        scope: str = "bot",
    ):  # TODO: think of a better name
        """
        coro
        A function that sends an event and catches all incoming events. Can be used anywhere.

        ex:
          await ctx.send(await bot.cogs["Sharding"].handler("evaluate", 4, {"code": '", ".join([f"{a} - {round(b*1000,2)} ms" for a,b in self.bot.latencies])'}))

        action: str          Must be the function's name you need to call
        expected_count: int  Minimal amount of data to send back. Can be more than the given and less on timeout
        args: dict           A dictionary for the action function's args to pass
        _timeout: int=2      Maximal amount of time waiting for incoming responses
        scope: str="bot"     Can be either launcher or bot. Used to differentiate them
        """
        # Preparation
        command_id = f"{uuid4()}"  # str conversion
        self._messages[command_id] = []  # must create it (see the router)

        # Sending
        payload = {"scope": scope, "action": action, "command_id": command_id}
        if args:
            payload["args"] = args
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )
        # Message collector
        try:
            async with timeout(_timeout):
                while len(self._messages[command_id]) < expected_count:
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pass
        return self._messages.pop(command_id, None)  # Cleanup

    @commands.command(
        aliases=["cooldowns", "t", "cds"], brief=_("Lists all your cooldowns")
    )
    @locale_doc
    async def timers(self, ctx):
        _("""Lists all your cooldowns, including your adventure timer.""")
        cooldowns = await self.bot.redis.execute("KEYS", f"cd:{ctx.author.id}:*")
        adv = await self.bot.get_adventure(ctx.author)
        if not cooldowns and (not adv or adv[2]):
            return await ctx.send(
                _("You don't have any active cooldown at the moment.")
            )
        timers = _("Commands on cooldown:")
        for key in cooldowns:
            key = key.decode()
            cooldown = await self.bot.redis.execute("TTL", key)
            cmd = key.replace(f"cd:{ctx.author.id}:", "")
            text = _("{cmd} is on cooldown and will be available after {time}").format(
                cmd=cmd, time=timedelta(seconds=int(cooldown))
            )
            timers = f"{timers}\n{text}"
        if adv and not adv[2]:
            text = _("Adventure is running and will be done after {time}").format(
                time=adv[1]
            )
            timers = f"{timers}\n{text}"
        await ctx.send(f"```{timers}```")

    @commands.command(aliases=["botstatus", "shards"], brief=_("Show the clusters"))
    @locale_doc
    async def clusters(self, ctx):
        _("""Lists all clusters and their current status.""")
        launcher_res = await self.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(_("Launcher is dead, that is really bad."))
        process_status = launcher_res[0]
        # We have to calculate number of processes
        processes, shards_left = divmod(
            self.bot.shard_count, self.bot.config.shard_per_cluster
        )
        if shards_left:
            processes += 1
        process_res = await self.handler(
            "send_latency_and_shard_count", processes, scope="bot"
        )
        actual_status = []
        for cluster_id, cluster_data in process_status.items():
            process_data = discord.utils.find(lambda x: cluster_id in x, process_res)
            if process_data:
                cluster_data["latency"] = f"{process_data[cluster_id][2]}ms"
            else:
                cluster_data["latency"] = "NaN"
            cluster_data["cluster_id"] = cluster_id
            cluster_data["started_at"] = datetime.fromtimestamp(
                cluster_data["started_at"]
            )
            actual_status.append(cluster_data)
        # actual_status.keys = active: bool, status: str, name: str, started_at: float, latency: str, cluster_id: int, shard_list: list[int]
        status = "\n".join(
            [
                f"Cluster #{i['cluster_id']} ({i['name']}), shards"
                f" {nice_join(i['shard_list'])}:"
                f" {'Active' if i['active'] else 'Inactive'} {i['status']}, latency"
                f" {i['latency']}. Started at: {i['started_at']}"
                for i in actual_status
            ]
        )
        await ctx.send(status)


def setup(bot):
    bot.add_cog(Sharding(bot))
