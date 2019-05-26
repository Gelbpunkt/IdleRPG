"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
from typing import Union

import discord
from asyncpg import UniqueViolationError
from discord.ext import commands

from classes.converters import User
from utils.checks import is_supporter


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.queue.put_nowait(self.make_pages())

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

    async def make_pages(self):
        await self.bot.wait_until_ready()  # prevent buggy start behaviour
        all_commands = {}
        for cog, instance in self.bot.cogs.items():
            if cog in ["Admin", "Owner"]:
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
                "**Welcome to the IdleRPG help. Use the arrows to move.\nFor more help, join the support server at https://discord.gg/axBKXBv.**\nCheck out our partners using the partners command!"
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
                desc = (
                    command.description
                    or getattr(command.callback, "__doc__")
                    or _("No Description set")
                )
                embed.add_field(
                    name=self.make_signature(command), value=desc, inline=False
                )
            pages.append(embed)
        self.pages = pages

    @commands.command()
    async def documentation(self, ctx):
        _("""Sends a link to the official documentation.""")
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a list of commands**"
            ).format(url=f"{self.bot.BASE_URL}/commands")
        )

    @commands.command(aliases=["faq"])
    async def tutorial(self, ctx):
        """Link to the bot tutorial."""
        await ctx.send(
            _(
                "<:blackcheck:441826948919066625> **Check {url} for a tutorial and FAQ**"
            ).format(url=f"{self.bot.BASE_URL}/tutorial")
        )

    @is_supporter()
    @commands.command()
    async def unbanfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        _("""Unban an entitiy from using $helpme.""")
        if isinstance(thing_to_ban, discord.User):
            id = thing_to_ban.id
        else:
            id = thing_to_ban
            thing_to_ban = self.bot.get_guild(id)
        await self.bot.pool.execute('DELETE FROM helpme WHERE "id"=$1;', id)
        await ctx.send(
            _("{thing} has been unbanned for the helpme command :ok_hand:").format(
                thing=thing_to_ban.name
            )
        )

    @is_supporter()
    @commands.command()
    async def banfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        _("""Band a user from using $helpme.""")
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
                "Are you sure? This will notify our support team and allow them to join the server."
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

    @commands.command()
    async def help(
        self, ctx, *, command: commands.clean_content(escape_markdown=True) = None
    ):
        _("""Shows help about the bot.""")
        if command:
            command = self.bot.get_command(command.lower())
            if not command:
                return await ctx.send(_("Sorry, that command does not exist."))
            sig = self.make_signature(command)
            subcommands = getattr(command, "commands", None)
            if subcommands:
                clean_subcommands = "\n".join(
                    [
                        f"    {c.name.ljust(15, ' ')} {c.description or getattr(c.callback, '__doc__')}"
                        for c in subcommands
                    ]
                )
                fmt = f"```\n{ctx.prefix}{sig}\n\n{command.description or getattr(command.callback, '__doc__')}\n\nCommands:\n{clean_subcommands}\n```"
            else:
                fmt = f"```\n{ctx.prefix}{sig}\n\n{command.description or getattr(command.callback, '__doc__')}\n```"

            return await ctx.send(fmt)

        await self.bot.paginator.Paginator(extras=self.pages).paginate(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
