"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import json
import asyncio

from async_timeout import timeout
from discord.ext import commands
from datetime import timedelta


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


def dict_to_kwargs(**kwargs):
    return ", ".join("%s=%r" % x for x in kwargs.items())


class GuildCommunication:
    def __init__(self, bot):
        self.bot = bot
        self.communication_channel = "guild-channel"
        self.key_prefix = "idle:"
        self.handler = None
        bot.loop.create_task(self.register_sub())
        self.bot.reset_cooldown = self.reset_cooldown

    """
    async def stat_updater(self):
        await self.bot.redis.execute(
            "ZADD",
            f"{self.key_prefix}guilds",
            self.bot.process_id,
            len(self.bot.guilds),
        )
        await self.bot.redis.execute(
            "ZADD", f"{self.key_prefix}users", self.bot.process_id, len(self.bot.users)
        )

    async def on_ready(self):
        await self.stat_updater()

    async def on_guild_join(self, guild):
        await self.stat_updater()

    async def on_guild_remove(self, guild):
        await self.stat_updater()
    """

    async def get_guilds(self):
        return sum(
            [
                int(c.decode())
                for c in await self.bot.redis.execute(
                    "ZRANGE", f"{self.key_prefix}guilds", 0, -1
                )
            ]
        )

    async def get_users(self):
        return sum(
            [
                int(c.decode())
                for c in await self.bot.redis.execute(
                    "ZRANGE", f"{self.key_prefix}users", 0, -1
                )
            ]
        )

    async def register_sub(self):
        if self.communication_channel not in self.bot.redis.pubsub_channels:
            await self.bot.redis.execute_pubsub("SUBSCRIBE", self.communication_channel)
            self.handler = self.bot.loop.create_task(self.event_handler())

    async def unregister_sub(self):
        await self.bot.redis.execute_pubsub("UNSUBSCRIBE", self.communication_channel)

    async def fetch_first_result(self, expected_id):
        channel = self.bot.redis.pubsub_channels[self.communication_channel]
        try:
            async with timeout(5):
                while await channel.wait_message():
                    try:
                        payload = await channel.get_json(encoding="utf-8")
                    except json.decoder.JSONDecodeError:
                        return None  # not a valid JSON message
                    if (
                        payload.get("value")
                        and payload.get("command_id") == expected_id
                    ):
                        return payload["value"]
        except asyncio.TimeoutError:
            return None

    async def event_handler(self):
        channel = self.bot.redis.pubsub_channels[self.communication_channel]
        while await channel.wait_message():
            try:
                payload = await channel.get_json(encoding="utf-8")
            except json.decoder.JSONDecodeError:
                return  # not a valid JSON message
            if payload.get("action") and hasattr(self, payload.get("action")):
                try:
                    eval(
                        f"self.bot.loop.create_task(self.{payload.get('action')}({dict_to_kwargs(**payload.get('args'))}))"
                    )
                except Exception as e:
                    print(e)

    async def send_message(self, channel_id: int, message: str):
        await self.bot.get_channel(channel_id).send(message)

    async def get_properties_by_userid(self, command_id, user_id: int):
        user = self.bot.get_user(user_id)
        if user:
            payload = {
                "command_id": command_id,
                "value": {
                    "id": user.id,
                    "name": user.name,
                    "avatar_url": user.avatar_url_as(static_format="png"),
                    "discriminator": user.discriminator,
                    "display": f"{user.name}#{user.discriminator}",
                },
            }
            await self.bot.redis.execute(
                "PUBLISH", self.communication_channel, json.dumps(payload)
            )

    async def guild_count(self, command_id: int):
        payload = {"command_id": command_id, "guildcount": len(self.bot.guilds)}
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps(payload)
        )

    async def reload_cog(self, cog_name: str):
        if cog_name in self.bot.cogs:
            try:
                self.bot.unload_extension(cog_name)
            except Exception as e:
                print(e)
                return
        try:
            self.bot.load_extension(cog_name)
        except Exception as e:
            await self.bot.redis.execute(
                "PUBLISH",
                self.communication_channel,
                json.dumps({"status": "error", "error_message": str(e)}),
            )
            return
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps({"status": "Done"})
        )

    async def load_cog(self, cog_name: str):
        try:
            self.bot.load_extension(cog_name)
        except Exception as e:
            await self.bot.redis.execute(
                "PUBLISH",
                self.communication_channel,
                json.dumps({"status": "error", "error_message": str(e)}),
            )
            return
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps({"status": "Done"})
        )

    async def unload_cog(self, cog_name: str):
        if cog_name in self.bot.cogs:
            try:
                self.bot.unload_extension(cog_name)
            except Exception as e:
                await self.bot.redis.execute(
                    "PUBLISH",
                    self.communication_channel,
                    json.dumps({"status": "error", "error_message": str(e)}),
                )
                return
        await self.bot.redis.execute(
            "PUBLISH", self.communication_channel, json.dumps({"status": "Done"})
        )

    async def reset_cooldown(self, ctx):
        await self.bot.redis.execute("DEL", f"cd:{ctx.author.id}:{ctx.command.name}")

    """
    @user_on_cooldown(cooldown=20)
    @commands.command()
    async def diniboytestwontexecuteit(self, ctx):
        await ctx.send("I said, don't! :\\")
    """

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

    def __unload(self):
        self.bot.loop.create_task(self.unregister_sub())
        try:
            self.handler.cancel()
        except:  # noqa
            pass


def setup(bot):
    bot.add_cog(GuildCommunication(bot))
