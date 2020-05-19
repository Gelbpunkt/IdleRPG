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

from typing import Union

import discord

from asyncpg import UniqueViolationError
from discord.ext import commands

from classes.converters import User
from utils.checks import is_supporter
from utils.i18n import _, locale_doc


def chunks(iterable, size):
    """Yield successive n-sized chunks from an iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def make_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            fmt = f"[{command.name}|{'|'.join(command.aliases)}]"
            if parent:
                fmt = f"{parent} {fmt}"
        else:
            fmt = command.name if not parent else f"{parent} {command.name}"
        fmt = f"{fmt} {command.signature}"
        return fmt

    def make_pages(self):
        all_commands = {}
        for cog, instance in self.bot.cogs.items():
            if cog in ["GameMaster", "Owner"]:
                continue
            commands = list(chunks(list(instance.get_commands()), 10))
            if len(commands) == 1:
                all_commands[cog] = commands[0]
            else:
                for i, j in enumerate(commands):
                    all_commands[f"{cog} ({i + 1}/{len(commands)})"] = j

        pages = []
        maxpages = len(all_commands)

        embed = discord.Embed(
            title=_("IdleRPG Help"),
            colour=self.bot.config.primary_colour,
            url=self.bot.BASE_URL,
            description=_(
                "**Welcome to the IdleRPG help. Use the arrows to move.\nFor more help,"
                " join the support server at https://support.idlerpg.xyz.**\nCheck out"
                " our partners using the partners command!"
            ),
        )
        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(
            text=_("IdleRPG Version {version}").format(version=self.bot.version),
            icon_url=self.bot.user.avatar_url,
        )
        pages.append(embed)
        for i, (cog, commands) in enumerate(all_commands.items()):
            embed = discord.Embed(
                title=_("IdleRPG Help"),
                colour=self.bot.config.primary_colour,
                url=self.bot.BASE_URL,
                description=_("**{category} Commands**").format(category=cog),
            )
            embed.set_footer(
                text=_("IdleRPG Version {version} | Page {page} of {maxpages}").format(
                    version=self.bot.version, page=i + 1, maxpages=maxpages
                ),
                icon_url=self.bot.user.avatar_url,
            )
            for command in commands:
                if hasattr(command.callback, "__doc__"):
                    desc = _(command.callback.__doc__)
                else:
                    desc = _("No Description set")
                embed.add_field(
                    name=self.make_signature(command), value=desc, inline=False
                )
            pages.append(embed)
        return pages

    @commands.command(aliases=["commands", "cmds"])
    @locale_doc
    async def documentation(self, ctx):
        _("""Sends a link to the official documentation.""")
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a list of"
                " commands**"
            ).format(url=f"{self.bot.BASE_URL}/commands")
        )

    @commands.command(aliases=["faq"])
    @locale_doc
    async def tutorial(self, ctx):
        """Link to the bot tutorial."""
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a tutorial and"
                " FAQ**"
            ).format(url=f"{self.bot.BASE_URL}/tutorial")
        )

    @is_supporter()
    @commands.command()
    @locale_doc
    async def unbanfromhelpme(self, ctx, thing_to_unban: Union[User, int]):
        _("""Unban an entitiy from using $helpme.""")
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
    @commands.command()
    @locale_doc
    async def banfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        _("""Ban a user from using $helpme.""")
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
    @commands.command()
    @locale_doc
    async def helpme(self, ctx, *, text: str):
        _("""Allows a support team member to join your server for individual help.""")
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

        await self.bot.http.send_message(
            453_551_307_249_418_254, None, embed=em.to_dict()
        )
        await ctx.send(
            _("Support team has been notified and will join as soon as possible!")
        )

    # @commands.command()
    # @locale_doc
    # async def help(
    #     self, ctx, *, command: commands.clean_content(escape_markdown=True) = None
    # ):
    #     _("""Shows help about the bot.""")
    #     if command:
    #         command = self.bot.get_command(command.lower())
    #         if not command:
    #             return await ctx.send(_("Sorry, that command does not exist."))
    #         sig = self.make_signature(command)
    #         subcommands = getattr(command, "commands", None)
    #         if subcommands:
    #             clean_subcommands = "\n".join(
    #                 [
    #                     f"    {c.name.ljust(15, ' ')}"
    #                     f" {_(getattr(c.callback, '__doc__'))}"
    #                     for c in subcommands
    #                 ]
    #             )
    #             fmt = (
    #                 f"```\n{ctx.prefix}{sig}\n\n{_(getattr(command.callback, '__doc__'))}\n\nCommands:\n{clean_subcommands}\n```"
    #             )
    #         else:
    #             fmt = (
    #                 f"```\n{ctx.prefix}{sig}\n\n{_(getattr(command.callback, '__doc__'))}\n```"
    #             )

    #         return await ctx.send(fmt)

    #     await self.bot.paginator.Paginator(extras=self.make_pages()).paginate(ctx)


class IdleHelp(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify_checks = False
        self.gm_exts = {"GameMaster"}
        self.owner_exts = {"GameMaster", "Owner"}
        self.color = 0xcb735c
        # self.icon = "https://media.discordapp.net/attachments/460568954968997890/711736595652280361/idlehelp.png"

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

        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    def embedbase(self, *args, **kwargs):
        e = discord.Embed(color=self.color, **kwargs)
        e.set_author(name=self.context.bot.user, icon_url=self.context.bot.user.avatar_url_as(static_format="png"))
        # e.set_thumbnail(url=self.icon)

        return e

    async def send_bot_help(self, mapping):
        e = self.embedbase(title=_("IdleRPG Help {}").format(self.context.bot.version), url="https://idlerpg.travitia.xyz/")
        e.set_image(url="https://media.discordapp.net/attachments/460568954968997890/711740723715637288/idle_banner.png")
        e.description = _("**Welcome to the IdleRPG help.**\n") +
                        _("Are you stuck? Ask for help in the support server!\n") +
                        "- https://support.idlerpg.xyz/\n" + 
                        _("Would you like to invite me to your server?\n") +
                        "- https://invite.idlerpg.xyz/\n" +
                        _("*See `help [command|extension]` for more info*")

        allowed = []
        for cog in mapping.keys():
            if cog is None:
                continue
            if self.context.author.id not in self.context.bot.config.game_masters and cog.qualified_name in self.gm_exts:
                continue
            if self.context.author.id not in self.context.bot.owner_ids and cog.qualified_name in self.owner_exts:
                continue
            if cog.qualified_name not in self.gm_exts and len([c for c in cog.get_commands() if not c.hidden]) == 0:
                continue
            allowed.append(cog.qualified_name)
        cogs = [sorted(allowed)[x:x+3] for x in range(0, len(allowed), 3)]
        length_list = [len(element) for row in cogs for element in row]
        column_width = max(length_list)
        rows = []
        for row in cogs:
            rows.append("".join(element.ljust(column_width + 2) for element in row))
        e.add_field(name=_("Extensions"), value="```{}```".format("\n".join(rows)))

        await self.context.send(embed=e)

    async def send_cog_help(self, cog):
        if self.context.author.id not in self.context.bot.config.game_master and cog.qualified_name in self.gm_exts:
            return await self.context.send(_("You do not have access to these commands!"))
        if self.context.author.id not in self.context.bot.owner_ids and cog.qualified_name in self.owner_exts:
            return await self.context.send(_("You do not have access to these commands!"))

        e = self.embedbase(title=f"[{cog.qualified_name.upper()}] {len(set(cog.walk_commands()))} commands")
        e.description = "\n".join([f"{'👥' if isinstance(c, commands.Group) else '👤'} `{self.clean_prefix}{c.qualified_name} {c.signature}` - {c.brief}" for c in cog.get_commands])
        e.set_footer(icon_url=self.context.bot.avatar_url_as(static_format="png"), text=_("See 'help <command>' for more detailed info"))
        await self.context.send(embed=e)

    async def send_command_help(self, command):
        if command.cog:
            if self.context.author.id not in self.context.bot.config.game_master and command.cog.qualified_name in self.gm_exts:
                return await self.context.send(_("You do not have access to this command!"))
            if self.context.author.id not in self.context.bot.owner_ids and command.cog.qualified_name in self.owner_exts:
                return await self.context.send(_("You do not have access to this command!"))

        e = self.embedbase(title=f"[{command.cog.qualified_name.upper()}] {command.qualified_name} {command.signature}", description=command.help)
        await self.context.send(embed=e)

    async def send_group_help(self, group):
        if group.cog:
            if self.context.author.id not in self.context.bot.config.game_master and group.cog.qualified_name in self.gm_exts:
                return await self.context.send(_("You do not have access to this command!"))
            if self.context.author.id not in self.context.bot.owner_ids and group.cog.qualified_name in self.owner_exts:
                return await self.context.send(_("You do not have access to this command!"))

        e = self.embedbase(title=f"[{group.cog.qualified_name.upper()}] {group.qualified_name} {group.signature}", description=group.help)
        e.add_field(name="Subcommands", value="\n".join([f"`{c.qualified_name}` - {c.brief}"] for c in group.commands))
        await self.context.send(embed=e)


def setup(bot):
    bot.add_cog(Help(bot))
    bot.help_command = IdleHelp()