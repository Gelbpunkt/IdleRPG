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
import math

from datetime import timedelta
from typing import Union

import discord

from asyncpg import UniqueViolationError
from discord.ext import commands, menus

from classes.converters import User
from utils.checks import has_open_help_request, is_supporter
from utils.i18n import _, locale_doc


def chunks(iterable, size):
    """Yield successive n-sized chunks from an iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


class CogMenu(menus.Menu):
    def __init__(self, *args, **kwargs):
        self.title = kwargs.pop("title")
        self.description = kwargs.pop("description")
        self.bot = kwargs.pop("bot")
        self.color = kwargs.pop("color")
        self.footer = kwargs.pop("footer")
        self.per_page = kwargs.pop("per_page", 5)
        self.page = 1
        super().__init__(*args, timeout=60.0, delete_message_after=True, **kwargs)

    @property
    def pages(self):
        return math.ceil(len(self.description) / self.per_page)

    def embed(self, desc):
        e = discord.Embed(
            title=self.title, color=self.color, description="\n".join(desc)
        )
        e.set_author(
            name=self.bot.user,
            icon_url=self.bot.user.avatar.url,
        )
        e.set_footer(
            text=f"{self.footer} | Page {self.page}/{self.pages}",
            icon_url=self.bot.user.avatar.url,
        )
        return e

    def should_add_reactions(self):
        return len(self.description) > self.per_page

    async def send_initial_message(self, ctx, channel):
        e = self.embed(self.description[0 : self.per_page])
        return await channel.send(embed=e)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f")
    async def on_previous_page(self, payload):
        if self.page != 1:
            self.page -= 1
            start = (self.page - 1) * self.per_page
            end = self.page * self.per_page
            items = self.description[start:end]
            e = self.embed(items)
            await self.message.edit(embed=e)

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f")
    async def on_stop(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f")
    async def on_next_page(self, payload):
        if len(self.description) >= (self.page * self.per_page):
            self.page += 1
            start = (self.page - 1) * self.per_page
            end = self.page * self.per_page
            items = self.description[start:end]
            e = self.embed(items)
            await self.message.edit(embed=e)


class SubcommandMenu(menus.Menu):
    def __init__(self, *args, **kwargs):
        self.cmds = kwargs.pop("cmds")
        self.title = kwargs.pop("title")
        self.description = kwargs.pop("description")
        self.bot = kwargs.pop("bot")
        self.color = kwargs.pop("color")
        self.per_page = kwargs.pop("per_page", 5)
        self.page = 1
        self.group_emoji = "💠"
        self.command_emoji = "🔷"
        super().__init__(*args, timeout=60.0, delete_message_after=True, **kwargs)

    @property
    def pages(self):
        return math.ceil(len(self.cmds) / self.per_page)

    def embed(self, cmds):
        e = discord.Embed(
            title=self.title, color=self.color, description=self.description
        )
        e.set_author(
            name=self.bot.user,
            icon_url=self.bot.user.avatar.url,
        )
        e.add_field(
            name=_("Subcommands"),
            value="\n".join(
                [
                    f"{self.group_emoji if isinstance(c, commands.Group) else self.command_emoji}"
                    f" `{self.ctx.prefix}{c.qualified_name}` - {_(c.brief)}"
                    for c in cmds
                ]
            ),
        )
        if self.should_add_reactions():
            e.set_footer(
                icon_url=self.bot.user.avatar.url,
                text=_(
                    "Click on the reactions to see more subcommands. | Page"
                    " {start}/{end}"
                ).format(start=self.page, end=self.pages),
            )
        return e

    def should_add_reactions(self):
        return len(self.cmds) > self.per_page

    async def send_initial_message(self, ctx, channel):
        e = self.embed(self.cmds[0 : self.per_page])
        return await channel.send(embed=e)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f")
    async def on_previous_page(self, payload):
        if self.page != 1:
            self.page -= 1
            start = (self.page - 1) * self.per_page
            end = self.page * self.per_page
            items = self.cmds[start:end]
            e = self.embed(items)
            await self.message.edit(embed=e)

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f")
    async def on_stop(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f")
    async def on_next_page(self, payload):
        if len(self.cmds) >= (self.page * self.per_page):
            self.page += 1
            start = (self.page - 1) * self.per_page
            end = self.page * self.per_page
            items = self.cmds[start:end]
            e = self.embed(items)
            await self.message.edit(embed=e)


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
        id = thing_to_ban.id if isinstance(thing_to_ban, discord.User) else thing_to_ban
        try:
            await self.bot.pool.execute('INSERT INTO helpme ("id") VALUES ($1);', id)
        except UniqueViolationError:
            return await ctx.send(_("Error... Maybe they're already banned?"))
        await ctx.send(_("They have been banned for the helpme command :ok_hand:"))

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
        if (
            cd := await self.bot.redis.execute_command("TTL", f"helpme:{ctx.guild.id}")
        ) != -2:
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
            self.bot.config.game.helpme_channel, None, embed=em.to_dict()
        )
        await self.bot.redis.execute_command(
            "SET",
            f"helpme:{ctx.guild.id}",
            message["id"],
            "EX",
            172800,  # 48 hours
        )
        await ctx.send(
            _("Support team has been notified and will join as soon as possible!")
        )

    @is_supporter()
    @helpme.command(hidden=True, brief=_("Finish the helpme request"))
    @locale_doc
    async def finish(self, ctx, guild_id: int):
        _(
            """`<guild_id>` - The server ID of the requesting server

            Clear a server's helpme cooldown. If this is not done, they will be on cooldown for 48 hours."""
        )
        await self.bot.redis.execute_command("DEL", f"helpme:{guild_id}")
        await ctx.send("Clear!", delete_after=5)

    @has_open_help_request()
    @helpme.command(aliases=["correct"], brief=_("Change your helpme text"))
    @locale_doc
    async def edit(self, ctx, *, new_text: str):
        _(
            """`<new_text>` - The new text to use in your helpme request

            Edit the text on your open helpme request. Our Support Team will see the new text right away.

            You can only use this command if your server has an open helpme request."""
        )
        message = await self.bot.http.get_message(
            self.bot.config.game.helpme_channel, ctx.helpme
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
            self.bot.config.game.helpme_channel,
            ctx.helpme,
            content=None,
            embed=em.to_dict(),
        )
        await ctx.send(
            _("Successfully changed your helpme text from `{old}` to `{new}`!").format(
                old=old_text, new=new_text
            )
        )

    @has_open_help_request()
    @helpme.command(
        aliases=["revoke", "remove"], brief=_("Cancel your open helpme request")
    )
    @locale_doc
    async def delete(self, ctx):
        _(
            """Cancel your ongoing helpme request. Our Support Team will not join your server.

            You can only use this command if your server has an open helpme request."""
        )
        if not await ctx.confirm(
            _("Are you sure you want to cancel your helpme request?")
        ):
            return await ctx.send(_("Cancelled cancellation."))
        await self.bot.http.delete_message(
            self.bot.config.game.helpme_channel, ctx.helpme
        )
        await self.bot.redis.execute_command("DEL", f"helpme:{ctx.guild.id}")
        await self.bot.http.send_message(
            self.bot.config.game.helpme_channel,
            f"Helpme request for server {ctx.guild} ({ctx.guild.id}) was cancelled by"
            f" {ctx.author}",
        )
        await ctx.send(_("Your helpme request has been cancelled."))

    @has_open_help_request()
    @helpme.command(brief=_("View your current helpme request"))
    @locale_doc
    async def view(self, ctx):
        _(
            """View how your server's current helpme request looks like to our Support Team.

            You can only use this command if your server has an open helpme request."""
        )
        message = await self.bot.http.get_message(
            self.bot.config.game.helpme_channel, ctx.helpme
        )
        embed = discord.Embed().from_dict(message["embeds"][0])

        await ctx.send(
            _("Your help request is visible to our support team like this:"),
            embed=embed,
        )


class IdleHelp(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        kwargs["command_attrs"] = {
            "brief": _("Views the help on a topic."),
            "help": _(
                """Views the help on a topic.

            The topic may either be a command name or a module name.
            Command names are always preferred, so for example, `{prefix}help adventure`
            will show the help on the command, not the module.

            To view the help on a module explicitely, use `{prefix}help module [name]`"""
            ),
        }

        super().__init__(*args, **kwargs)
        self.verify_checks = False
        self.color = None
        self.gm_exts = {"GameMaster"}
        self.owner_exts = {"Owner"}
        self.group_emoji = "💠"
        self.command_emoji = "🔷"

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        PREFER_COG = False
        if command.lower().startswith(("module ", "module:")):
            command = command[7:]
            PREFER_COG = True

        if PREFER_COG:
            if command.lower() == "gamemaster":
                command = "GameMaster"
            else:
                command = command.title()
            cog = bot.get_cog(command)
            if cog is not None:
                return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            cog = bot.get_cog(command.title())
            if cog is not None:
                return await self.send_cog_help(cog)

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

    async def send_bot_help(self, mapping):
        e = discord.Embed(
            title=_(
                "IdleRPG Help {version}",
            ).format(version=self.context.bot.version),
            color=self.context.bot.config.game.primary_colour,
            url="https://idlerpg.xyz/",
        )
        e.set_author(
            name=self.context.bot.user,
            icon_url=self.context.bot.user.avatar.url,
        )
        e.set_image(
            url="https://media.discordapp.net/attachments/460568954968997890/711740723715637288/idle_banner.png"
        )
        e.description = _(
            "**Welcome to the IdleRPG help.**\nCheck out our tutorial!\n-"
            " https://idlerpg.xyz/tutorial/\nAre you stuck? Ask for help in the support"
            " server!\n- https://support.idlerpg.xyz/\nDo you need personal help?\n-"
            " Contact our support team using `{prefix}helpme`.\nWould you like to"
            " invite me to your server?\n- https://invite.idlerpg.xyz/\n*See"
            " `{prefix}help [command]` and `{prefix}help module [module]` for more"
            " info*"
        ).format(prefix=self.context.prefix)

        allowed = []
        for cog in sorted(mapping.keys(), key=lambda x: x.qualified_name if x else ""):
            if cog is None:
                continue
            if (
                self.context.author.id not in self.context.bot.config.game.game_masters
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
        e.add_field(name=_("Modules"), value="```{}```".format("\n".join(rows)))

        await self.context.send(embed=e)

    async def send_cog_help(self, cog):
        if (cog.qualified_name in self.gm_exts) and (
            self.context.author.id not in self.context.bot.config.game.game_masters
        ):
            if self.context.author.id in self.context.bot.owner_ids:
                pass  # owners don't have restrictions
            else:
                return await self.context.send(
                    _("You do not have access to these commands!")
                )
        if (cog.qualified_name in self.owner_exts) and (
            self.context.author.id not in self.context.bot.owner_ids
        ):
            return await self.context.send(
                _("You do not have access to these commands!")
            )

        menu = CogMenu(
            title=(
                f"[{cog.qualified_name.upper()}] {len(set(cog.walk_commands()))}"
                " commands"
            ),
            bot=self.context.bot,
            color=self.context.bot.config.game.primary_colour,
            description=[
                f"{self.group_emoji if isinstance(c, commands.Group) else self.command_emoji}"
                f" `{self.context.clean_prefix}{c.qualified_name} {c.signature}` - {_(c.brief)}"
                for c in cog.get_commands()
            ],
            footer=_("See '{prefix}help <command>' for more detailed info").format(
                prefix=self.context.prefix
            ),
        )

        await menu.start(self.context)

    async def send_command_help(self, command):
        if command.cog:
            if (command.cog.qualified_name in self.gm_exts) and (
                self.context.author.id not in self.context.bot.config.game.game_masters
            ):
                if self.context.author.id in self.context.bot.owner_ids:
                    pass  # owners don't have restrictions
                else:
                    return await self.context.send(
                        _("You do not have access to this command!")
                    )
            if (command.cog.qualified_name in self.owner_exts) and (
                self.context.author.id not in self.context.bot.owner_ids
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )

        e = discord.Embed(
            title=(
                f"[{command.cog.qualified_name.upper()}] {command.qualified_name}"
                f" {command.signature}"
            ),
            colour=self.context.bot.config.game.primary_colour,
            description=_(command.help).format(prefix=self.context.prefix),
        )
        e.set_author(
            name=self.context.bot.user,
            icon_url=self.context.bot.user.avatar.url,
        )

        if command.aliases:
            e.add_field(
                name=_("Aliases"), value="`{}`".format("`, `".join(command.aliases))
            )
        await self.context.send(embed=e)

    async def send_group_help(self, group):
        if group.cog:
            if (
                self.context.author.id not in self.context.bot.config.game.game_masters
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

        menu = SubcommandMenu(
            title=(
                f"[{group.cog.qualified_name.upper()}] {group.qualified_name}"
                f" {group.signature}"
            ),
            bot=self.context.bot,
            color=self.context.bot.config.game.primary_colour,
            description=_(group.help).format(prefix=self.context.prefix),
            cmds=list(group.commands),
        )
        await menu.start(self.context)


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))
    bot.help_command = IdleHelp()
    bot.help_command.cog = bot.get_cog("Help")
