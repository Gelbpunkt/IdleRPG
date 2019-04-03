"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import asyncio

from discord.ext import commands
from typing import Union
from asyncpg import UniqueViolationError
from classes.converters import User


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def is_supporter():
    async def predicate(ctx):
        u = ctx.bot.get_guild(ctx.bot.config.support_server_id).get_member(
            ctx.author.id
        )
        if not u:
            return False
        return "Support Team" in [r.name for r in u.roles]

    return commands.check(predicate)


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
            title="IdleRPG Help",
            colour=self.bot.config.primary_colour,
            url=self.bot.BASE_URL,
            description="**Welcome to the IdleRPG help. Use the arrows to move.\nFor more help, join the support server at https://discord.gg/axBKXBv.**\nCheck out our partners using the partners command!",
        )
        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(
            text=f"IdleRPG Version {self.bot.version}",
            icon_url=self.bot.user.avatar_url,
        )
        pages.append(embed)
        for i, (cog, commands) in enumerate(all_commands.items()):
            embed = discord.Embed(
                title="IdleRPG Help",
                colour=self.bot.config.primary_colour,
                url=self.bot.BASE_URL,
                description=f"**{cog} Commands**",
            )
            embed.set_footer(
                text=f"IdleRPG Version {self.bot.version} | Page {i + 1} of {maxpages}",
                icon_url=self.bot.user.avatar_url,
            )
            for command in commands:
                desc = (
                    command.description
                    or getattr(command.callback, "__doc__")
                    or "No Description set"
                )
                embed.add_field(
                    name=self.make_signature(command), value=desc, inline=False
                )
            pages.append(embed)
        self.pages = pages

    @commands.command(
        description="Sends a link to the official documentation.", aliases=["docs"]
    )
    async def documentation(self, ctx):
        await ctx.send(
            f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL} for a list of commands**"
        )

    @commands.command(description="Tutorial link.")
    async def tutorial(self, ctx):
        await ctx.send(
            f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL}/tutorial for a tutorial**"
        )

    @commands.command(description="Link to the FAQ.")
    async def faq(self, ctx):
        await ctx.send(
            f"<:blackcheck:441826948919066625> **Check {self.bot.BASE_URL}/tutorial for the official FAQ**"
        )

    @is_supporter()
    @commands.command(
        description="Unblock a guild or user from using the helpme command"
    )
    async def unbanfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        if isinstance(thing_to_ban, discord.User):
            id = thing_to_ban.id
        else:
            id = thing_to_ban
            thing_to_ban = self.bot.get_guild(id)
        await self.bot.pool.execute('DELETE FROM helpme WHERE "id"=$1;', id)
        await ctx.send(
            f"{thing_to_ban.name} has been unbanned for the helpme command :ok_hand:"
        )

    @is_supporter()
    @commands.command(description="Block a guild or user from using the helpme command")
    async def banfromhelpme(self, ctx, thing_to_ban: Union[User, int]):
        if isinstance(thing_to_ban, discord.User):
            id = thing_to_ban.id
        else:
            id = thing_to_ban
            thing_to_ban = self.bot.get_guild(id)
        try:
            await self.bot.pool.execute('INSERT INTO helpme ("id") VALUES ($1);', id)
        except UniqueViolationError:
            return await ctx.send("Error... Maybe they're already banned?")
        await ctx.send(
            f"{thing_to_ban.name} has been banned for the helpme command :ok_hand:"
        )

    @commands.command(
        description="Need help? This command allows a support member to join and help you!"
    )
    async def helpme(self, ctx, *, text: str):
        blocked = await self.bot.pool.fetchrow(
            'SELECT * FROM helpme WHERE "id"=$1 OR "id"=$2;',
            ctx.guild.id,
            ctx.author.id,
        )
        if blocked:
            return await ctx.send(
                "You or your server has been blacklisted for some reason."
            )

        def check(msg):
            return msg.author == ctx.author and msg.content.lower() == "yes, i do"

        await ctx.send(
            "Are you sure? This will notify our support team and allow them to join the server. If you are sure, type `Yes, I do`."
        )
        try:
            await self.bot.wait_for("message", check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelling your help request.")
        try:
            inv = await ctx.channel.create_invite()
        except discord.Forbidden:
            return await ctx.send("Error when creating Invite.")
        c = self.bot.get_channel(453_551_307_249_418_254)
        em = discord.Embed(title="Help Request", colour=0xFF0000)
        em.add_field(name="Requested by", value=f"{ctx.author}")
        em.add_field(name="Requested in server", value=f"{ctx.guild.name}")
        em.add_field(name="Requested in channel", value=f"#{ctx.channel}")
        em.add_field(name="Content", value=text)
        em.add_field(name="Invite", value=inv)

        await c.send(embed=em)
        await ctx.send(
            "Support team has been notified and will join as soon as possible!"
        )

    @commands.command(description="Get some help.")
    async def help(
        self, ctx, *, command: commands.clean_content(escape_markdown=True) = None
    ):
        if command:
            command = self.bot.get_command(command.lower())
            if not command:
                return await ctx.send("Sorry, that command does not exist.")
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

        maxpage = len(self.pages) - 1
        currentpage = 0
        browsing = True
        msg = await ctx.send(embed=self.pages[currentpage])

        await msg.add_reaction("\U000023ee")
        await msg.add_reaction("\U000025c0")
        await msg.add_reaction("\U000025b6")
        await msg.add_reaction("\U000023ed")
        await msg.add_reaction("\U0001f522")

        def reactioncheck(reaction, user):
            return (
                str(reaction.emoji)
                in [
                    "\U000025c0",
                    "\U000025b6",
                    "\U000023ee",
                    "\U000023ed",
                    "\U0001f522",
                ]
                and reaction.message.id == msg.id
                and user.id == ctx.author.id
            )

        def msgcheck(amsg):
            return amsg.channel == ctx.channel and not amsg.author.bot

        while browsing:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=reactioncheck
                )
                if reaction.emoji == "\U000025c0":
                    if currentpage == 0:
                        pass
                    else:
                        currentpage -= 1
                        await msg.edit(embed=self.pages[currentpage])
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                elif reaction.emoji == "\U000025b6":
                    if currentpage == maxpage:
                        pass
                    else:
                        currentpage += 1
                        await msg.edit(embed=self.pages[currentpage])
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                elif reaction.emoji == "\U000023ed":
                    currentpage = maxpage
                    await msg.edit(embed=self.pages[currentpage])
                    try:
                        await msg.remove_reaction(reaction.emoji, user)
                    except discord.Forbidden:
                        pass
                elif reaction.emoji == "\U000023ee":
                    currentpage = 0
                    await msg.edit(embed=self.pages[currentpage])
                    try:
                        await msg.remove_reaction(reaction.emoji, user)
                    except discord.Forbidden:
                        pass
                elif reaction.emoji == "\U0001f522":
                    question = await ctx.send(
                        f"Enter a page number from `1` to `{maxpage + 1}`"
                    )
                    num = await self.bot.wait_for("message", timeout=10, check=msgcheck)
                    if num is not None:
                        try:
                            num2 = int(num.content)
                            if num2 >= 1 and num2 <= maxpage + 1:
                                currentpage = num2 - 1
                                await msg.edit(embed=self.pages[currentpage])
                                try:
                                    await num.delete()
                                except discord.Forbidden:
                                    pass
                            else:
                                await ctx.send(
                                    f"Must be between `1` and `{maxpage + 1}`.",
                                    delete_after=2,
                                )
                                try:
                                    await num.delete()
                                except discord.Forbidden:
                                    pass
                        except ValueError:
                            await ctx.send(
                                "That is not a valid number!", delete_after=2
                            )
                    await question.delete()
                    try:
                        await msg.remove_reaction(reaction.emoji, user)
                    except discord.Forbidden:
                        pass
            except asyncio.TimeoutError:
                browsing = False
                try:
                    await msg.clear_reactions()
                except discord.Forbidden:
                    pass
                finally:
                    break


def setup(bot):
    bot.add_cog(Help(bot))
