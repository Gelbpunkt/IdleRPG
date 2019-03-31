from datetime import timedelta
import discord, traceback
from discord.ext import commands
import Levenshtein as lv
import utils.checks
import sys

try:
    from raven import Client
    from raven_aiohttp import AioHttpTransport
except ModuleNotFoundError:
    SENTRY_SUPPORT = False
else:
    SENTRY_SUPPORT = True


class Errorhandler:
    def __init__(self, bot):
        self.bot = bot
        bot.on_command_error = self._on_command_error
        self.client = None
        bot.queue.put_nowait(self.initialize_cog())

    async def _on_command_error(self, ctx, error, bypass=False):
        ctx.command.reset_cooldown(ctx)
        if (
            hasattr(ctx.command, "on_error")
            or (ctx.command and hasattr(ctx.cog, f"_{ctx.command.cog_name}__error"))
            and not bypass
        ):
            # Do nothing if the command/cog has its own error handler and the bypass is False
            return
        if isinstance(error, commands.CommandNotFound):
            async with self.bot.pool.acquire() as conn:
                try:
                    ret = await conn.fetchval(
                        'SELECT "unknown" FROM server WHERE "id"=$1;', ctx.guild.id
                    )
                except:
                    return
            if not ret:
                return
            nl = "\n"
            matches = []
            for command in list(self.bot.commands):
                if lv.distance(ctx.invoked_with, command.name) < 4:
                    matches.append(command.name)
            if len(matches) == 0:
                matches.append("Oops! I couldn't find any similar Commands!")
            try:
                await ctx.send(
                    f"**`Unknown Command`**\n\nDid you mean:\n{nl.join(matches)}\n\nNot what you meant? Type `{ctx.prefix}help` for a list of commands."
                )
            except:
                pass
        elif hasattr(error, "original") and isinstance(
            getattr(error, "original"), utils.checks.NoCharacter
        ):
            await ctx.send(
                f"You don't have a character yet. Use `{ctx.prefix}create` to create a new character!"
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"Oops! You forgot a required argument: `{error.param.name}`"
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"You used a wrong argument!")
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(
                f"You are on cooldown. Try again in {timedelta(seconds=int(error.retry_after))}."
            )
        elif hasattr(error, "original") and isinstance(
            error.original, discord.HTTPException
        ):
            return  # not our fault
        elif isinstance(error, commands.NotOwner):
            await ctx.send(
                embed=discord.Embed(
                    title="Permission denied",
                    description=":x: This command is only avaiable for the bot owner.",
                    colour=0xFF0000,
                )
            )
        elif isinstance(error, commands.CheckFailure):
            if type(error) == utils.checks.NoCharacter:
                return await ctx.send("You don't have a character yet.")
            await ctx.send(
                embed=discord.Embed(
                    title="Permission denied",
                    description=":x: You don't have the permissions to use this command. It is thought for other users.",
                    colour=0xFF0000,
                )
            )
        elif isinstance(error, discord.HTTPException):
            await ctx.send(
                f"There was a error responding to your message:\n`{error.text}`\nCommon issues: Bad Guild Icon or too long response"
            )
        elif isinstance(error, commands.CommandInvokeError) and hasattr(
            error, "original"
        ):
            print("In {}:".format(ctx.command.qualified_name), file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(
                "{0}: {1}".format(error.original.__class__.__name__, error.original),
                file=sys.stderr,
            )
            if self.client:
                try:
                    raise error.original
                except Exception:
                    if ctx.guild:
                        guild_id = ctx.guild.id
                    else:
                        guild_id = "None"
                    self.client.captureException(
                        data={
                            "message": ctx.message.content,
                            "tags": {"command": ctx.command.name},
                        },
                        extra={
                            "guild_id": str(guild_id),
                            "channel_id": str(ctx.channel.id),
                            "message_id": str(ctx.message.id),
                            "user_id": str(ctx.author.id),
                        },
                    )
        try:
            await ctx.bot.reset_cooldown(ctx)
        except:
            pass

    async def initialize_cog(self):
        """Saves the original cmd error handler"""
        if SENTRY_SUPPORT:
            self.client = Client(self.bot.config.sentry_url, transport=AioHttpTransport)

    async def unload_cog(self):
        """Readds the original error handler"""
        if SENTRY_SUPPORT:
            await self.client.remote.get_transport().close()

    def __unload(self):
        self.bot.queue.put_nowait(self.unload_cog())


def setup(bot):
    bot.add_cog(Errorhandler(bot))
