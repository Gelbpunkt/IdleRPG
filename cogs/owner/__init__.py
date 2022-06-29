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
import copy
import io
import re
import textwrap
import traceback

from contextlib import redirect_stdout

import discord

from discord.ext import commands

from classes.badges import Badge, BadgeConverter
from classes.bot import Bot
from classes.context import Context
from classes.converters import UserWithCharacter
from utils import shell
from utils.misc import random_token


class Owner(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    def cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip("` \n")

    @commands.command(hidden=True, name="eval")
    async def _eval(self, ctx: Context, *, body: str) -> None:
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
            exec(to_compile, env)
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
    async def evall(self, ctx: Context, *, code: str) -> None:
        """[Owner only] Evaluates python code on all processes."""
        data = await self.bot.cogs["Sharding"].handler(
            "evaluate", self.bot.shard_count, {"code": code}
        )
        filtered_data = {instance: data.count(instance) for instance in data}
        pretty_data = "".join(
            f"```py\n{count}x | {instance[6:]}"
            for instance, count in filtered_data.items()
        )
        if len(pretty_data) > 2000:
            pretty_data = pretty_data[:1997] + "..."
        await ctx.send(pretty_data)

    @commands.command(hidden=True)
    async def bash(self, ctx: Context, *, command_to_run: str) -> None:
        """[Owner Only] Run shell commands."""
        await shell.run(command_to_run, ctx)

    @commands.command(hidden=True)
    async def runas(
        self, ctx: Context, member: discord.Member, *, command: str
    ) -> None:
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
        text = re.sub(reg, r'<a href="\2">\1</a>', text)
        reg = re.compile(r"~~(.+)~~")
        text = re.sub(reg, r"<s>\1</s>", text)
        reg = re.compile(r"__(.+)__")
        text = re.sub(reg, r"<u>\1</u>", text)
        reg = re.compile(r"\*\*(.+)\*\*")
        text = re.sub(reg, r"<b>\1</b>", text)
        reg = re.compile(r"\*(.+)\*")
        text = re.sub(reg, r"<i>\1</i>", text)
        return text

    def make_signature(self, cmd):
        if cmd.aliases:
            prelude = cmd.qualified_name.replace(cmd.name, "").strip()
            if prelude:
                prelude = f"{prelude} "
            actual_names = cmd.aliases + [cmd.name]
            aliases = f"{prelude}[{'|'.join(actual_names)}]"
        else:
            aliases = cmd.qualified_name
        return f"${aliases} {cmd.signature}"

    @commands.command(hidden=True)
    async def makehtml(self, ctx: Context) -> None:
        """Generates HTML for commands page."""
        with open("assets/html/commands.html") as f:
            base = f.read()
        with open("assets/html/cog.html") as f:
            cog = f.read()
        with open("assets/html/command.html") as f:
            command = f.read()

        html = ""

        for cog_name, cog_ in self.bot.cogs.items():
            if cog_name in ("GameMaster", "Owner", "Custom"):
                continue
            commands = {c for c in list(cog_.walk_commands()) if not c.hidden}
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

    @commands.group(hidden=True, invoke_without_command=True)
    async def badges(self, ctx: Context, user: UserWithCharacter) -> None:
        badges = Badge.from_db(ctx.user_data["badges"])

        if badges:
            await ctx.send(badges.to_pretty())
        else:
            await ctx.send("User has no badges")

    @badges.command(hidden=True, name="add")
    async def badges_add(
        self, ctx: Context, user: UserWithCharacter, badge: BadgeConverter
    ) -> None:
        badges = Badge.from_db(ctx.user_data["badges"])
        badges |= badge

        await self.bot.pool.execute(
            'UPDATE profile SET "badges"=$1 WHERE "user"=$2;', badges.to_db(), user.id
        )

        await ctx.send("Done")

    @badges.command(hidden=True, name="rem", aliases=["remove", "delete", "del"])
    async def badges_rem(
        self, ctx: Context, user: UserWithCharacter, badge: BadgeConverter
    ) -> None:
        badges = Badge.from_db(ctx.user_data["badges"])
        badges ^= badge

        await self.bot.pool.execute(
            'UPDATE profile SET "badges"=$1 WHERE "user"=$2;', badges.to_db(), user.id
        )

        await ctx.send("Done")


def setup(bot):
    bot.add_cog(Owner(bot))
