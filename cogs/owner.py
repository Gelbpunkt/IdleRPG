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
import copy
import io
import textwrap
import traceback
from contextlib import redirect_stdout
from importlib import reload as importlib_reload

import discord
from async_timeout import timeout
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.config.owners

    @commands.command(name="load", hidden=True)
    @locale_doc
    async def _load(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="unload", hidden=True)
    @locale_doc
    async def _unload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="reload", hidden=True)
    @locale_doc
    async def _reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.reload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(hidden=True)
    @locale_doc
    async def reloadconf(self, ctx):
        try:
            importlib_reload(self.bot.config)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(hidden=True)
    @locale_doc
    async def shutdown(self, ctx):
        embed = discord.Embed(color=0xFF0000)
        embed.add_field(name="Shutting down...", value="Goodbye!", inline=False)
        await ctx.send(embed=embed)
        await self.bot.logout()

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip("` \n")

    @commands.command(hidden=True, name="eval")
    @locale_doc
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("blackcheck:441826948919066625")
            except discord.Forbidden:
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(hidden=True)
    @locale_doc
    async def evall(self, ctx, *, code: str):
        """[Owner only] Evaluates python code on all processes."""
        data = "".join(
            await self.bot.cogs["Sharding"].handler(
                "evaluate", self.bot.shard_count, {"code": code}
            )
        )
        if len(data) > 2000:
            data = data[:1997] + "..."
        await ctx.send(data)

    @commands.command(hidden=True)
    @locale_doc
    async def bash(self, ctx, *, command_to_run: str):
        """[Owner Only] Run shell commands."""
        process_embed = discord.Embed(
            title="Here is your result, Sir", color=self.bot.config.primary_colour
        )
        process_embed.set_thumbnail(url=self.bot.user.avatar_url)
        process = await asyncio.create_subprocess_shell(
            command_to_run,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            async with timeout(10), ctx.channel.typing():
                stdout, stderr = await process.communicate()
        except asyncio.TimeoutError:
            process_embed.title = "⌛ Timeout reached..."
            return await ctx.send(embed=process_embed)
        if process.returncode != 0 and stderr:
            process_embed.add_field(
                name=":x:Ouch, an error!",
                value=f"The process `{process.pid}` returned a nonzero exit status `{process.returncode}`.\n"
                f"```{stderr.decode()}```",
                inline=False,
            )
        elif process.returncode != 0:
            process_embed.add_field(
                name=":x:Ouch, an error!",
                value=f"The process `{process.pid}` returned a nonzero exit status `{process.returncode}`.",
                inline=False,
            )
        elif stderr:  # Print errors with graceful shutdown aswell
            process_embed.add_field(
                name=":x:Ouch, an error!",
                value=f"```{stderr.decode()}```",
                inline=False,
            )
        if stdout:
            process_embed.add_field(
                name="<:cmd:472468557998063636>Output:",
                value=f"```{stdout.decode()}```",
                inline=False,
            )
        else:
            process_embed.add_field(
                name="<:cmd:472468557998063636>Output:",
                value=f"```--- Empty output ---\nHere is a coffee: ☕```",
                inline=False,
            )
        await ctx.send(embed=process_embed)

    @commands.command(hidden=True)
    @locale_doc
    async def sql(self, ctx, *, query: str):
        """[Owner Only] Very basic SQL command."""
        async with self.bot.pool.acquire() as conn:
            try:
                ret = await conn.fetch(query)
            except Exception:
                return await ctx.send(f"```py\n{traceback.format_exc()}```")
            if ret:
                await ctx.send(f"```{ret}```")
            else:
                await ctx.send("No results to fetch.")

    @commands.command(hidden=True)
    @locale_doc
    async def runas(self, ctx, member: discord.Member, *, command: str):
        """[Owner Only] Run a command as if you were the user."""
        fake_msg = copy.copy(ctx.message)
        fake_msg._update(ctx.message.channel, dict(content=ctx.prefix + command))
        fake_msg.author = member
        new_ctx = await ctx.bot.get_context(fake_msg)
        try:
            await ctx.bot.invoke(new_ctx)
        except Exception:
            await ctx.send(f"```py\n{traceback.format_exc()}```")


def setup(bot):
    bot.add_cog(Owner(bot))
