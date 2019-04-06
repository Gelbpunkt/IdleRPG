"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""

from traceback import format_exc
import asyncio

try:
    import ujson as json  # faster, but linux only
except ImportError:
    import json
from uuid import uuid4
from async_timeout import timeout
from datetime import timedelta
import discord
import re
from discord.ext import commands


# Cross-process cooldown check (pass this to commands)
def user_on_cooldown(cooldown: int):
    async def predicate(ctx):
        command_ttl = await ctx.bot.redis.execute(
            "TTL", f"cd:{ctx.author.id}:{ctx.command.qualified_name}"
        )
        if command_ttl == -2:
            await ctx.bot.redis.execute(
                "SET",
                f"cd:{ctx.author.id}:{ctx.command.qualified_name}",
                ctx.command.qualified_name,
                "EX",
                cooldown,
            )
            return True
        else:
            raise commands.CommandOnCooldown(ctx, command_ttl)
            return False

    return commands.check(predicate)  # TODO: Needs a redesign


class Sharding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.communication_channel = "guild-channel"
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
            except json.decoder.JSONDecodeError:
                return  # not a valid JSON message
            if payload.get("action") and hasattr(self, payload.get("action")):
                try:
                    if payload.get("scope") != "bot":
                        return  # it's not our cup of tea
                    self.bot.loop.create_task(
                        getattr(self, payload.get("action"))(
                            **json.loads(payload.get("args")),
                            command_id=payload["command_id"],
                        )
                    )
                except Exception:
                    payload = {
                        "error": True,
                        "output": format_exc(),
                        "command_id": payload["command_id"],
                    }
                    await self.bot.redis.execute(
                        "PUBLISH", self.communication_channel, json.dumps(payload)
                    )
            if payload.get("output") and payload["command_id"] in self._messages:
                self._messages[payload["command_id"]].append(payload["output"])

    async def user_is_patreon(self, member_id: int, command_id: str):
        if not self.bot.get_user(member_id):
            return  # if the instance cannot see them, we can't do much
        member = self.bot.get_guild(self.bot.config.support_server_id).get_member(
            member_id
        )
        if not member:
            return  # when the bot can only see DMs with the user

        if any(
            (
                discord.utils.get(member.roles, name="Donators"),
                discord.utils.get(member.roles, name="Administrators"),
            )
        ):
            payload = {"output": True, "command_id": command_id}
        else:
            payload = {"output": False, "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def user_is_helper(self, member_id: int, command_id: str):
        if not self.bot.get_user(member_id):
            return  # if the instance cannot see them, we can't do much
        member = self.bot.get_guild(self.bot.config.support_server_id).get_member(
            member_id
        )
        if not member:
            return  # when the bot can only see DMs with the user

        if discord.utils.get(member.roles, name="Support Team"):
            payload = {"output": True, "command_id": command_id}
        else:
            payload = {"output": False, "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def get_user(self, user_id: int, command_id: str):
        if not self.bot.get_user(user_id):
            return
        payload = {"output": self.bot.get_user(int(user_id)), "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def fetch_user(self, user_inp, command_id: str):
        user = None
        matches = re.search(r"<@!?(\d+)>", user_inp)
        if matches:
            user_inp = matches.group(1)
        if isinstance(user_inp, int) or (
            isinstance(user_inp, str) and user_inp.isdigit()
        ):
            user = self.bot.get_user(int(user_inp))
        else:
            if len(user_inp) > 5 and user_inp[-5] == "#":
                discrim = user_inp[-4:]
                name = user_inp[:-5]
                predicate = lambda u: u.name == name and u.discriminator == discrim
                user = discord.utils.find(predicate, self.bot.users)
            else:
                predicate = lambda u: u.name == user_inp
                user = discord.utils.find(predicate, self.bot.users)
        if not user:
            return
        payload = {"output": user, "command_id": command_id}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def evaluate(self, code, command_id: str):
        payload = {"output": eval(code), "command_id": command_id}
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
            payload["args"] = json.dumps(args)
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

    @commands.command()
    async def timers(self, ctx):
        cooldowns = await self.bot.redis.execute("KEYS", f"cd:{ctx.author.id}:*")
        if not cooldowns:
            return await ctx.send("You don't have any active cooldown at the moment.")
        timers = "Commands on cooldown:"
        for key in cooldowns:
            key = key.decode()
            cooldown = await self.bot.redis.execute("TTL", key)
            cmd = key.replace(f"cd:{ctx.author.id}:", "")
            timers = f"{timers}\n{cmd} is on cooldown and will be available after {str(timedelta(seconds=cooldown)).split('.')[0]}"
        await ctx.send(f"```{timers}```")


def setup(bot):
    bot.add_cog(Sharding(bot))
