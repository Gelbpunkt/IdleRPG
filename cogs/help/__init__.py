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
from datetime import timedelta
from typing import Union

import discord

from asyncpg import UniqueViolationError
from discord.ext import commands

from classes.converters import User
from utils.checks import has_open_help_request, is_supporter
from utils.i18n import _, locale_doc


def chunks(iterable, size):
    """Yield successive n-sized chunks from an iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["commands", "cmds"], brief=_("View the command list"))
    @locale_doc
    async def documentation(self, ctx):
        _("""Sends a link to the official documentation.""")
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a list of"
                " commands**"
            ).format(url=f"{self.bot.BASE_URL}/commands")
        )

    @commands.command(aliases=["faq"], brief=_("View the tutorial"))
    @locale_doc
    async def tutorial(self, ctx):
        _("""Link to the bot tutorial and FAQ.""")
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a tutorial and"
                " FAQ**"
            ).format(url=f"{self.bot.BASE_URL}/tutorial")
        )

    @is_supporter()
    @commands.command(brief=_("Allow someone/-thing to use helpme again"))
    @locale_doc
    async def unbanfromhelpme(self, ctx, thing_to_unban: Union[User, int]):
        _(
            """`<thing_to_unban>` - A discord User, their User ID, or a server ID

            Unbans a previously banned user/server from using the `{prefix}helpme` command.

            Only Support Team Members can use this command."""
        )
        if isinstance(thing_to_unban, discord.User):
            id = thing_to_unban.id
        else:
            id = thing_to_unban
            thing_to_unban = self.bot.get_guild(id)
        await self.bot.pool.execute('DELETE FROM helpme WHERE "id"=$1;', id)
        await ctx.send(
            _("{thing} has been unbanned for the helpme command :ok_hand:").format(
                thing=thing_to_unban.name
            )
        )

    @is_supporter()
    @commands.command(brief=_("Ban someone/-thing from using helpme"))
    @locale_doc
    async def banfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        _(
            """`<thing_to_ban>` - A discord User, their User ID, or a server ID

            Bans a user/server from using the `{prefix}helpme` command.

            Only Support Team Members can use this command."""
        )
        if isinstance(thing_to_ban, discord.User):
            id = thing_to_ban.id
        else:
            id = thing_to_ban
            thing_to_ban = self.bot.get_guild(id)
        try:
            await self.bot.pool.execute('INSERT INTO helpme ("id") VALUES ($1);', id)
        except UniqueViolationError:
            return await ctx.send(_("Error... Maybe they're already banned?"))
        await ctx.send(
            _("{thing} has been banned for the helpme command :ok_hand:").format(
                thing=thing_to_ban.name
            )
        )

    @commands.guild_only()
    @commands.group(
        invoke_without_command=True, brief=_("Ask our Support Team for help")
    )
    @locale_doc
    async def helpme(self, ctx, *, text: str):
        _(
            """`<text>` - The text to describe the question or the issue you are having

            Ask our support team for help, allowing them to join your server and help you personally.
            If they do not join within 48 hours, you may use the helpme command again.

            Make sure the bot has permissions to create instant invites.
            English is preferred."""
        )
        if (cd := await self.bot.redis.execute("TTL", f"helpme:{ctx.guild.id}")) != -2:
            time = timedelta(seconds=cd)
            return await ctx.send(
                _(
                    "You server already has a helpme request open! Please wait until"
                    " the support team gets to you or wait {time} to try again. "
                ).format(time=time)
            )
        blocked = await self.bot.pool.fetchrow(
            'SELECT * FROM helpme WHERE "id"=$1 OR "id"=$2;',
            ctx.guild.id,
            ctx.author.id,
        )
        if blocked:
            return await ctx.send(
                _("You or your server has been blacklisted for some reason.")
            )

        if not await ctx.confirm(
            _(
                "Are you sure? This will notify our support team and allow them to join"
                " the server."
            )
        ):
            return

        try:
            inv = await ctx.channel.create_invite()
        except discord.Forbidden:
            return await ctx.send(_("Error when creating Invite."))
        em = discord.Embed(title="Help Request", colour=0xFF0000)
        em.add_field(name="Requested by", value=f"{ctx.author}")
        em.add_field(name="Requested in server", value=f"{ctx.guild.name}")
        em.add_field(name="Requested in channel", value=f"#{ctx.channel}")
        em.add_field(name="Content", value=text)
        em.add_field(name="Invite", value=inv)
        em.set_footer(text=f"Server ID: {ctx.guild.id}")

        message = await self.bot.http.send_message(
            self.bot.config.helpme_channel, None, embed=em.to_dict()
        )
        await self.bot.redis.execute(
            "SET", f"helpme:{ctx.guild.id}", message["id"], "EX", 172800,  # 48 hours
        )
        await ctx.send(
            _("Support team has been notified and will join as soon as possible!")
        )

    @is_supporter()
    @helpme.command(hidden=True)
    @locale_doc
    async def finish(self, ctx, guild_id: int):
        _("""[Support Team only] Clear a server's helpme cooldown.""")
        await self.bot.redis.execute("DEL", f"helpme:{guild_id}")
        await ctx.send("Clear!", delete_after=5)

    @has_open_help_request()
    @helpme.command(aliases=["correct"])
    @locale_doc
    async def edit(self, ctx, *, new_text: str):
        _("""Edit the text on your open helpme request.""")
        message = await self.bot.http.get_message(
            self.bot.config.helpme_channel, ctx.helpme
        )
        inv = discord.utils.find(
            lambda f: f["name"] == "Invite", message["embeds"][0]["fields"]
        )["value"]
        old_text = discord.utils.find(
            lambda f: f["name"] == "Content", message["embeds"][0]["fields"]
        )["value"]

        em = discord.Embed(title="Help Request", colour=0xFF0000)
        em.add_field(name="Requested by", value=f"{ctx.author}")
        em.add_field(name="Requested in server", value=f"{ctx.guild.name}")
        em.add_field(name="Requested in channel", value=f"#{ctx.channel}")
        em.add_field(name="Content", value=new_text)
        em.add_field(name="Invite", value=inv)
        em.set_footer(text=f"Server ID: {ctx.guild.id}")

        await self.bot.http.edit_message(
            self.bot.config.helpme_channel, ctx.helpme, content=None, embed=em.to_dict()
        )
        await ctx.send(
            _("Successfully changed your helpme text from `{old}` to `{new}`!").format(
                old=old_text, new=new_text
            )
        )

    @has_open_help_request()
    @helpme.command(aliases=["revoke", "remove"])
    @locale_doc
    async def delete(self, ctx):
        _("""Cancel your ongoing helpme request.""")
        if not await ctx.confirm(
            _("Are you sure you want to cancel your helpme request?")
        ):
            return await ctx.send(_("Cancelled cancellation."))
        await self.bot.http.delete_message(self.bot.config.helpme_channel, ctx.helpme)
        await self.bot.redis.execute("DEL", f"helpme:{ctx.guild.id}")
        await ctx.send(_("Your helpme request has been cancelled."))

    @has_open_help_request()
    @helpme.command()
    @locale_doc
    async def view(self, ctx):
        _("""View your server's current helpme request.""")
        message = await self.bot.http.get_message(
            self.bot.config.helpme_channel, ctx.helpme
        )
        embed = discord.Embed().from_dict(message["embeds"][0])

        await ctx.send(
            _("Your help request is visible to our support team like this:"),
            embed=embed,
        )


class IdleHelp(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify_checks = False
        self.gm_exts = {"GameMaster"}
        self.owner_exts = {"GameMaster", "Owner"}
        self.color = 0xCB735C

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        cog = bot.get_cog(command.title())
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(
                self.command_not_found, self.remove_mentions(keys[0])
            )
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(
                    self.subcommand_not_found, cmd, self.remove_mentions(key)
                )
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(
                        self.subcommand_not_found, cmd, self.remove_mentions(key)
                    )
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    def embedbase(self, *args, **kwargs):
        e = discord.Embed(color=self.color, **kwargs)
        e.set_author(
            name=self.context.bot.user,
            icon_url=self.context.bot.user.avatar_url_as(static_format="png"),
        )

        return e

    async def send_bot_help(self, mapping):
        e = self.embedbase(
            title=_("IdleRPG Help {version}").format(version=self.context.bot.version),
            url="https://idlerpg.travitia.xyz/",
        )
        e.set_image(
            url="https://media.discordapp.net/attachments/460568954968997890/711740723715637288/idle_banner.png"
        )
        e.description = _(
            "**Welcome to the IdleRPG help.**\n"
            "Are you stuck? Ask for help in the support server!\n"
            "- https://support.idlerpg.xyz/\n"
            "Would you like to invite me to your server?\n"
            "- https://invite.idlerpg.xyz/\n"
            "*See `help [command|extension]` for more info*"
        )

        allowed = []
        for cog in sorted(mapping.keys(), key=lambda x: x.qualified_name if x else ""):
            if cog is None:
                continue
            if (
                self.context.author.id not in self.context.bot.config.game_masters
                and cog.qualified_name in self.gm_exts
            ):
                continue
            if (
                self.context.author.id not in self.context.bot.owner_ids
                and cog.qualified_name in self.owner_exts
            ):
                continue
            if (
                cog.qualified_name not in self.gm_exts
                and len([c for c in cog.get_commands() if not c.hidden]) == 0
            ):
                continue
            allowed.append(cog.qualified_name)
        cogs = [allowed[x : x + 3] for x in range(0, len(allowed), 3)]
        length_list = [len(element) for row in cogs for element in row]
        column_width = max(length_list)
        rows = []
        for row in cogs:
            rows.append("".join(element.ljust(column_width + 2) for element in row))
        e.add_field(name=_("Extensions"), value="```{}```".format("\n".join(rows)))

        await self.context.send(embed=e)

    async def send_cog_help(self, cog):
        if (
            self.context.author.id not in self.context.bot.config.game_masters
            and cog.qualified_name in self.gm_exts
        ):
            return await self.context.send(
                _("You do not have access to these commands!")
            )
        if (
            self.context.author.id not in self.context.bot.owner_ids
            and cog.qualified_name in self.owner_exts
        ):
            return await self.context.send(
                _("You do not have access to these commands!")
            )

        e = self.embedbase(
            title=(
                f"[{cog.qualified_name.upper()}] {len(set(cog.walk_commands()))}"
                " commands"
            )
        )
        e.description = "\n".join(
            [
                f"{'👥' if isinstance(c, commands.Group) else '👤'}"
                f" `{self.clean_prefix}{c.qualified_name} {c.signature}` - {_(c.brief)}"
                for c in cog.get_commands()
            ]
        )
        e.set_footer(
            icon_url=self.context.bot.user.avatar_url_as(static_format="png"),
            text=_("See '{prefix}help <command>' for more detailed info").format(
                prefix=self.context.prefix
            ),
        )
        await self.context.send(embed=e)

    async def send_command_help(self, command):
        if command.cog:
            if (
                self.context.author.id not in self.context.bot.config.game_masters
                and command.cog.qualified_name in self.gm_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )
            if (
                self.context.author.id not in self.context.bot.owner_ids
                and command.cog.qualified_name in self.owner_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )

        e = self.embedbase(
            title=(
                f"[{command.cog.qualified_name.upper()}] {command.qualified_name}"
                f" {command.signature}"
            ),
            description=_(command.help).format(prefix=self.context.prefix),
        )
        if command.aliases:
            e.add_field(
                name=_("Aliases"), value="`{}`".format("`, `".join(command.aliases))
            )
        await self.context.send(embed=e)

    async def send_group_help(self, group):
        if group.cog:
            if (
                self.context.author.id not in self.context.bot.config.game_masters
                and group.cog.qualified_name in self.gm_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )
            if (
                self.context.author.id not in self.context.bot.owner_ids
                and group.cog.qualified_name in self.owner_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )

        e = self.embedbase(
            title=(
                f"[{group.cog.qualified_name.upper()}] {group.qualified_name}"
                f" {group.signature}"
            ),
            description=group.help,
        )
        e.add_field(
            name="Subcommands",
            value="\n".join(
                [f"`{c.qualified_name}` - {_(c.brief)}" for c in group.commands]
            ),
        )
        if group.aliases:
            e.add_field(
                name=_("Aliases"), value="`{}`".format("`, `".join(group.aliases))
            )
        await self.context.send(embed=e)


def setup(bot):
    bot.add_cog(Help(bot))
    bot.help_command = IdleHelp()
