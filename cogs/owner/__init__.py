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
import copy
import io
import re
import textwrap
import traceback
import tracemalloc

from contextlib import redirect_stdout
from importlib import reload as importlib_reload

import discord
import import_expression

from discord.ext import commands
from tabulate import tabulate

from classes.converters import MemberConverter
from utils import random, shell
from utils.misc import random_token


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="load", hidden=True)
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
    async def reloadconf(self, ctx):
        try:
            importlib_reload(self.bot.config)
        except Exception as e:
            await ctx.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await ctx.send("**`SUCCESS`**")

    @commands.command(hidden=True)
    async def debug(self, ctx):
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")
            await ctx.send("```" + "\n".join([str(x) for x in top_stats[:10]]) + "```")

    @commands.command(hidden=True)
    async def makeluck(self, ctx):
        """Sets the luck for all gods to a random value and give bonus luck to the top 25 followers."""
        text_collection = ["**This week's luck has been decided:**\n"]
        async with self.bot.pool.acquire() as conn:
            for god in self.bot.config.gods:
                boundaries = self.bot.config.gods[god]["boundaries"]
                luck = random.randint(boundaries[0] * 100, boundaries[1] * 100) / 100
                await conn.execute(
                    'UPDATE profile SET "luck"=round($1, 2) WHERE "god"=$2;', luck, god
                )
                top_followers = [
                    u["user"]
                    for u in await conn.fetch(
                        'SELECT "user" FROM profile WHERE "god"=$1 ORDER BY "favor"'
                        " DESC LIMIT 25;",
                        god,
                    )
                ]
                await conn.execute(
                    'UPDATE profile SET "luck"=CASE WHEN "luck"+round($1, 2)>=2.0 THEN'
                    ' 2.0 ELSE "luck"+round($1, 2) END WHERE "user"=ANY($2);',
                    0.5,
                    top_followers[:5],
                )
                await conn.execute(
                    'UPDATE profile SET "luck"=CASE WHEN "luck"+round($1, 2)>=2.0 THEN'
                    ' 2.0 ELSE "luck"+round($1, 2) END WHERE "user"=ANY($2);',
                    0.4,
                    top_followers[5:10],
                )
                await conn.execute(
                    'UPDATE profile SET "luck"=CASE WHEN "luck"+round($1, 2)>=2.0 THEN'
                    ' 2.0 ELSE "luck"+round($1, 2) END WHERE "user"=ANY($2);',
                    0.3,
                    top_followers[10:15],
                )
                await conn.execute(
                    'UPDATE profile SET "luck"=CASE WHEN "luck"+round($1, 2)>=2.0 THEN'
                    ' 2.0 ELSE "luck"+round($1, 2) END WHERE "user"=ANY($2);',
                    0.2,
                    top_followers[15:20],
                )
                await conn.execute(
                    'UPDATE profile SET "luck"=CASE WHEN "luck"+round($1, 2)>=2.0 THEN'
                    ' 2.0 ELSE "luck"+round($1, 2) END WHERE "user"=ANY($2);',
                    0.1,
                    top_followers[20:25],
                )
                text_collection.append(f"{god} set to {luck}.")
            await conn.execute('UPDATE profile SET "favor"=0 WHERE "god" IS NOT NULL;')
            text_collection.append("Godless set to 1.0")
            await conn.execute('UPDATE profile SET "luck"=1.0 WHERE "god" IS NULL;')
            msg = await ctx.send("\n".join(text_collection))
            try:
                await msg.publish()
            except (discord.Forbidden, discord.HTTPException) as e:
                await ctx.send(f"Could not publish the message for some reason: `{e}`")

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
            "__last__": self._last_result,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()
        token = random_token(self.bot.user.id)

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            import_expression.exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
            if ret is not None:
                ret = str(ret).replace(self.bot.http.token, token)
        except Exception:
            value = stdout.getvalue()
            value = value.replace(self.bot.http.token, token)
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            value = value.replace(self.bot.http.token, token)
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
    async def evall(self, ctx, *, code: str):
        """[Owner only] Evaluates python code on all processes."""
        data = await self.bot.cogs["Sharding"].handler(
            "evaluate", self.bot.shard_count, {"code": code}
        )
        filtered_data = {instance: data.count(instance) for instance in data}
        pretty_data = "".join(
            "```py\n{0}x | {1}".format(count, instance[6:])
            for instance, count in filtered_data.items()
        )
        if len(pretty_data) > 2000:
            pretty_data = pretty_data[:1997] + "..."
        await ctx.send(pretty_data)

    @commands.command(hidden=True)
    async def bash(self, ctx, *, command_to_run: str):
        """[Owner Only] Run shell commands."""
        await shell.run(command_to_run, ctx)

    @commands.command(hidden=True)
    async def sql(self, ctx, *, query: str):
        """[Owner Only] Very basic SQL command."""
        if "select" in query.lower() or "returning" in query.lower():
            type_ = "fetch"
        else:
            type_ = "execute"
        try:
            ret = await (getattr(self.bot.pool, type_))(query)
        except Exception:
            return await ctx.send(f"```py\n{traceback.format_exc()}```")
        if type_ == "fetch" and len(ret) == 0:
            return await ctx.send("No results.")
        elif type_ == "fetch" and len(ret) > 0:
            ret.insert(0, ret[0].keys())
            await ctx.send(
                f"```\n{tabulate(ret, headers='firstrow', tablefmt='psql')}\n```"
            )
        else:
            await ctx.send(f"```{ret}```")

    @commands.command(hidden=True)
    async def runas(self, ctx, member: MemberConverter, *, command: str):
        """[Owner Only] Run a command as if you were the user."""
        fake_msg = copy.copy(ctx.message)
        fake_msg._update(dict(channel=ctx.channel, content=ctx.prefix + command))
        fake_msg.author = member
        new_ctx = await ctx.bot.get_context(fake_msg)
        try:
            await ctx.bot.invoke(new_ctx)
        except Exception:
            await ctx.send(f"```py\n{traceback.format_exc()}```")

    def replace_md(self, s):
        opening = True
        out = []
        for i in s:
            if i == "`":
                if opening is True:
                    opening = False
                    i = "<code>"
                else:
                    opening = True
                    i = "</code>"
            out.append(i)
        reg = re.compile(r'\[(.+)\]\(([^ ]+?)( "(.+)")?\)')
        text = "".join(out)
        return re.sub(reg, r'<a href="\2">\1</a>', text)

    def make_signature(self, cmd):
        if cmd.aliases:
            actual_names = cmd.aliases + [cmd.name]
            aliases = f"[{'|'.join(actual_names)}]"
        else:
            aliases = cmd.name
        return f"${aliases} {cmd.signature}"

    @commands.command(hidden=True)
    async def makehtml(self, ctx):
        """Generates HTML for commands page."""
        with open("assets/html/commands.html", "r") as f:
            base = f.read()
        with open("assets/html/cog.html", "r") as f:
            cog = f.read()
        with open("assets/html/command.html", "r") as f:
            command = f.read()

        html = ""

        for cog_name, cog_ in self.bot.cogs.items():
            if cog_name in ("GameMaster", "Owner", "Custom"):
                continue
            commands = set(c for c in list(cog_.walk_commands()) if not c.hidden)
            if len(commands) > 0:
                html += cog.format(name=cog_name)
                for cmd in commands:
                    html += command.format(
                        name=cmd.qualified_name,
                        usage=self.make_signature(cmd)
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"),
                        checks=f"<b>Checks: {checks}</b>"
                        if (
                            checks := ", ".join(
                                [
                                    (
                                        "cooldown"
                                        if "cooldown" in name
                                        else (
                                            "has_character"
                                            if name == "has_char"
                                            else name
                                        )
                                    )
                                    for c in cmd.checks
                                    if (
                                        name := re.search(
                                            r"<function ([^.]+)\.", repr(c)
                                        ).group(1)
                                    )
                                    != "update_pet"
                                ]
                            )
                        )
                        else "",
                        description=self.replace_md(
                            (cmd.help or "No Description Set")
                            .format(prefix="$")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        ).replace("\n", "<br>"),
                    )

        html = base.format(content=html)
        await ctx.send(
            file=discord.File(filename="commands.html", fp=io.StringIO(html))
        )


def setup(bot):
    bot.add_cog(Owner(bot))
