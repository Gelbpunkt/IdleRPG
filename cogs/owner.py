"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import traceback
import textwrap
import io
import subprocess
import copy

from contextlib import redirect_stdout
from importlib import reload as importlib_reload
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.config.owners

    @commands.command(hidden=True)
    async def addowner(self, ctx, user: discord.Member):
        if user.id in self.bot.config.owners:
            return await ctx.send("Sudo mode alreay enabled for that guy")
        self.bot.config.owners.append(user.id)
        await ctx.send(f"Glj! You can now abuse this botto, {user.mention}!")

    @commands.command(
        hidden=True, aliases=["remowner", "rmowner", "delowner", "deleteowner"]
    )
    async def removeowner(self, ctx, user: discord.Member):
        if user.id == self.bot.owner_id:
            return await ctx.send("Don't you dare deleting my creator!")
        try:
            self.bot.config.owners.remove(user.id)
        except ValueError:
            return await ctx.send("Failed, that guy is not an owner")
        await ctx.send(f"Oooof... You can no longer abuse this botto, {user.mention}!")

        # Hidden means it won't show up on the default help.

    @commands.command(name="load", hidden=True)
    async def cog_load(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="unload", hidden=True)
    async def cog_unload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(name="reload", hidden=True)
    async def cog_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(hidden=True)
    async def reloadconf(self, ctx):
        try:
            importlib_reload(self.bot.config)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(hidden=True)
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

    @commands.command(description="[Owner only] Evaluates Bash Commands.", hidden=True)
    async def bash(self, ctx, *, command_to_run: str):
        output = subprocess.check_output(
            command_to_run.split(), stderr=subprocess.STDOUT
        ).decode("utf-8")
        await ctx.send(f"```py\n{output}\n```")

    @commands.command(hidden=True, description="[Owner Only] Execute SQL")
    async def sql(self, ctx, *, query: str):
        async with self.bot.pool.acquire() as conn:
            try:
                ret = await conn.fetch(query)
            except Exception:
                return await ctx.send(f"```py\n{traceback.format_exc()}```")
            if ret:
                await ctx.send(f"```{ret}```")
            else:
                await ctx.send("No results to fetch.")

    @commands.command(hidden=True, description="[Owner Only] Get an invite to a server")
    async def gimme(self, ctx, *, guildname: str):
        for guild in self.bot.guilds:
            if guild.name == guildname:
                try:
                    return await ctx.send((await guild.invites())[0])
                except IndexError:
                    try:
                        return await ctx.send(
                            await guild.text_channels[0].create_invite()
                        )
                    except discord.Forbidden:
                        return await ctx.send("Can't access invites.")
        await ctx.send("No guild found.")

    @commands.command(
        hidden=True, description="[Owner Only] Invoke a command as someone"
    )
    async def runas(self, ctx, member: discord.Member, *, command: str):
        fake_msg = copy.copy(ctx.message)
        fake_msg._update(ctx.message.channel, dict(content=ctx.prefix + command))
        fake_msg.author = member
        new_ctx = await ctx.bot.get_context(fake_msg)
        try:
            await ctx.bot.invoke(new_ctx)
        except Exception:
            await ctx.send(f"```py\n{traceback.format_exc()}```")

    @commands.command(description="Shard overview.")
    async def shards(self, ctx):
        res = "**Shard overview**\n"
        for s in list(self.bot.shards.keys()):
            res += f"Shard **{s}** ({len([g for g in self.bot.guilds if g.shard_id==s])} Servers). Ping: {round(self.bot.latencies[s][1]*1000, 2)}ms\n"
        await ctx.send(res)


def setup(bot):
    bot.add_cog(Owner(bot))
