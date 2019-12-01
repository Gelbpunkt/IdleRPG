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
import random

from datetime import timedelta
from typing import Union

import discord

from discord.ext import commands

from classes.converters import IntGreaterThan, MemberWithCharacter, User
from cogs.shard_communication import guild_on_cooldown as guild_cooldown
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import (
    has_char,
    has_guild,
    has_guild_,
    has_money,
    has_no_guild,
    is_guild_leader,
    is_guild_officer,
    is_no_guild_leader,
    user_is_patron,
)


class Guild(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.group(invoke_without_command=True)
    @locale_doc
    async def guild(self, ctx):
        _("""This command contains all guild-related commands.""")
        guild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )
        if not guild:
            return await ctx.send(_("You are not in a guild yet."))
        await self.get_guild_info(ctx, guild_id=guild[0])

    async def get_guild_info(
        self, ctx: commands.Context, *, guild_id: int = None, name: str = None
    ):
        if name:
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "name"=$1;', name
            )
        elif guild_id:
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', guild_id
            )
        if not guild:
            return await ctx.send(_("No guild found."))

        membercount = await self.bot.pool.fetchval(
            'SELECT count(*) FROM profile WHERE "guild"=$1;', guild["id"]
        )
        text = _("Members")
        embed = discord.Embed(title=guild["name"], description=guild["description"])
        embed.add_field(
            name=_("Current Member Count"),
            value=f"{membercount}/{guild['memberlimit']} {text}",
        )
        leader = await rpgtools.lookup(self.bot, guild["leader"])
        embed.add_field(name=_("Leader"), value=leader)
        embed.add_field(
            name="Guild Bank",
            value=f"**${guild['money']}** / **${guild['banklimit']}**",
        )
        embed.set_thumbnail(url=guild["icon"])
        embed.set_footer(text=_("Guild ID: {id}").format(id=guild["id"]))
        if guild["badge"]:
            embed.set_image(url=guild["badge"])
        try:
            await ctx.send(embed=embed)
        except discord.errors.HTTPException:
            await ctx.send(
                _(
                    "The guild icon seems to be a bad URL. Use `{prefix}guild icon` to fix this."
                ).format(prefix=ctx.prefix)
            )

    @guild.command()
    @locale_doc
    async def info(self, ctx, *, by: Union[MemberWithCharacter, str]):
        _(
            """\
Look up a guild by its name or by a player.
To look up a guild by its name, use guild:name.
To look up a guild by its ID, use id:number."""
        )
        kwargs = {}
        if isinstance(by, str):
            if by.lower().startswith("guild:"):
                kwargs.update(name=by[6:])
            elif by.lower().startswith("id:"):
                kwargs.update(guild_id=int(by[3:]))
            else:
                kwargs.update(name=by)
        else:
            async with self.bot.pool.acquire() as conn:
                guild_id = await conn.fetchval(
                    'SELECT guild FROM profile WHERE "user"=$1;', by.id
                )
                if guild_id == 0:
                    return await ctx.send(
                        _("**{user}** does not have a guild.").format(user=by.name)
                    )
                kwargs.update(guild_id=guild_id)
        await self.get_guild_info(ctx, **kwargs)

    @guild.command()
    @locale_doc
    async def ladder(self, ctx):
        _("""The best GvG guilds.""")
        guilds = await self.bot.pool.fetch(
            "SELECT * FROM guild ORDER BY wins DESC LIMIT 10;"
        )
        result = ""
        for idx, guild in enumerate(guilds):
            leader = await rpgtools.lookup(self.bot, guild["leader"])
            text = _("a guild by `{leader}` with **{wins}** GvG Wins").format(
                leader=leader, wins=guild["wins"]
            )
            result = f"{result}{idx + 1}. {guild['name']}, {text}\n"
        await ctx.send(
            embed=discord.Embed(
                title=_("The Best GvG Guilds"), description=result, colour=0xE7CA01
            )
        )

    @has_guild()
    @guild.command()
    @locale_doc
    async def members(self, ctx):
        _("""Shows you a list of your guild members.""")
        members = await self.bot.pool.fetch(
            'SELECT "user", "guildrank" FROM profile WHERE "guild"=$1;',
            ctx.character_data["guild"],
        )
        members_fmt = []
        for m in members:
            u = str(
                await self.bot.get_user_global(m["user"])
                or _("Unknown User (ID {id})").format(id=m["user"])
            )
            members_fmt.append(f"{u} ({m['guildrank']})")
        await self.bot.paginator.Paginator(
            entries=members_fmt, title=_("Your guild mates")
        ).paginate(ctx)

    @has_char()
    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def badge(self, ctx, number: IntGreaterThan(0)):
        _("""[Guild owner only] Change the guild badge.""")
        async with self.bot.pool.acquire() as conn:
            bgs, channel = await conn.fetchval(
                'SELECT (badges, channel) FROM guild WHERE "leader"=$1;', ctx.author.id
            )
            if not bgs:
                return await ctx.send(_("Your guild has no badges yet."))
            try:
                bg = bgs[number - 1]
            except IndexError:
                return await ctx.send(
                    _(
                        "The badge number {number} is not valid, your guild only has {amount} available."
                    ).format(amount=len(bgs), number=number)
                )
            await conn.execute(
                'UPDATE guild SET badge=$1 WHERE "leader"=$2;', bg, ctx.author.id
            )
        await ctx.send(_("Badge updated!"))
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** changed the guild badge."
        )

    @has_char()
    @has_no_guild()
    @user_cooldown(600)
    @guild.command()
    @locale_doc
    async def create(self, ctx):
        _("""Creates a guild.""")

        def mycheck(amsg):
            return amsg.author == ctx.author

        await ctx.send(
            _("Enter a name for your guild. Maximum length is 20 characters.")
        )
        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Cancelled guild creation."))
        name = name.content
        if len(name) > 20:
            return await ctx.send(_("Guild names musn't exceed 20 characters."))
        await ctx.send(
            _("Send a link to the guild's icon. Maximum length is 60 characters.")
        )
        try:
            url = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Cancelled guild creation."))
        url = url.content
        if len(url) > 60:
            return await ctx.send(_("URLs mustn't exceed 60 characters."))
        if await user_is_patron(self.bot, ctx.author):
            memberlimit = 100
        else:
            memberlimit = 50

        if not await ctx.confirm(
            _("Are you sure? React to create a guild for **$10000**")
        ):
            return
        if not await has_money(self.bot, ctx.author.id, 10000):
            return await ctx.send(
                _("A guild creation costs **$10000**, you are too poor.")
            )
        async with self.bot.pool.acquire() as conn:
            if await conn.fetchrow('SELECT * FROM guild WHERE "name"=$1;', name):
                return await ctx.send(_("The guild name is taken."))
            guild = await conn.fetchrow(
                "INSERT INTO guild (name, memberlimit, leader, icon) VALUES ($1, $2, $3, $4) RETURNING *;",
                name,
                memberlimit,
                ctx.author.id,
                url,
            )
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2, "money"="money"-$3 WHERE "user"=$4;',
                guild["id"],
                "Leader",
                10000,
                ctx.author.id,
            )
        await ctx.send(
            _(
                "Successfully added your guild **{name}** with a member limit of **{memberlimit}**."
            ).format(name=name, memberlimit=memberlimit)
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def transfer(self, ctx, member: MemberWithCharacter):
        _("""Transfer guild ownership to someone else.""")
        if (
            member == ctx.author
            or ctx.character_data["guild"] != ctx.user_data["guild"]
        ):
            return await ctx.send(_("Not a member of your guild."))
        if not await ctx.confirm(
            _("Are you sure to transfer guild ownership to {user}?").format(
                user=member.mention
            )
        ):
            return
        m = 100 if await user_is_patron(self.bot, member) else 50
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guildrank"=$1 WHERE "user"=$2;',
                "Member",
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "guildrank"=$1 WHERE "user"=$2;',
                "Leader",
                member.id,
            )
            name, channel = await conn.fetchval(
                'UPDATE guild SET "leader"=$1, "banklimit"="upgrade"*250000, "memberlimit"=$2 WHERE "id"=$3 RETURNING ("name", "channel");',
                member.id,
                m,
                ctx.character_data["guild"],
            )

        await ctx.send(_("{user} now leads {guild}.").format(user=member, guild=name))
        await self.bot.http.send_message(
            channel, f"Ownership changed from **{ctx.author}** to **{member}**"
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def promote(self, ctx, member: MemberWithCharacter):
        _("""Promote someone to the rank of officer""")
        if member == ctx.author:
            return await ctx.send(_("Very funny..."))
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send(_("Target is not a member of your guild."))
        if ctx.user_data["guildrank"] == "Officer":
            return await ctx.send(_("This user is already an officer of your guild."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Officer", member.id
            )
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )
        await ctx.send(
            _("Done! {member} has been promoted to the rank of `Officer`.").format(
                member=member
            )
        )
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** promoted **{member}** to the rank of Officer."
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def demote(self, ctx, member: MemberWithCharacter):
        _("""Demotes someone from the officer rank""")
        if member == ctx.author:
            return await ctx.send(_("Very funny..."))
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send(_("Target is not a member of your guild."))
        if ctx.user_data["guildrank"] != "Officer":
            return await ctx.send(_("This user can't be demoted any further."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Member", member.id
            )
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )
        await ctx.send(
            _("Done! {member} has been demoted to the rank of `Member`.").format(
                member=member
            )
        )
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** demoted **{member}** to the rank of Member."
        )

    @is_guild_officer()
    @guild.command()
    @locale_doc
    async def invite(self, ctx, newmember: MemberWithCharacter):
        _("""[Guild officer only] Invite someone to your guild.""")
        if ctx.user_data["guild"]:
            return await ctx.send(_("That member already has a guild."))
        async with self.bot.pool.acquire() as conn:
            id = await conn.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
            )
            membercount = await conn.fetchval(
                'SELECT COUNT(*) FROM profile WHERE "guild"=$1;', id
            )
            limit, name, channel = await conn.fetchval(
                'SELECT (memberlimit, name, channel) FROM guild WHERE "id"=$1;', id
            )
        if membercount >= limit:
            return await ctx.send(
                _("Your guild is already at the maximum member count.")
            )

        if not await ctx.confirm(
            _(
                "{newmember}, {author} invites you to join **{name}**. React to join the guild."
            ).format(newmember=newmember.mention, author=ctx.author.mention, name=name),
            user=newmember,
        ):
            return
        if await has_guild_(self.bot, newmember.id):
            return await ctx.send(_("That member already has a guild."))
        await self.bot.pool.execute(
            'UPDATE profile SET guild=$1 WHERE "user"=$2;', id, newmember.id
        )
        await ctx.send(
            _("{newmember} is now a member of **{name}**. Welcome!").format(
                newmember=newmember.mention, name=name
            )
        )
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** invited **{newmember}** to the guild"
        )

    @has_guild()
    @is_no_guild_leader()
    @guild.command()
    @locale_doc
    async def leave(self, ctx):
        _("""Leave your current guild.""")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "user"=$3;',
                0,
                "Member",
                ctx.author.id,
            )
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )

        await ctx.send(_("You left your guild."))
        await self.bot.http.send_message(channel, f"**{ctx.author}** left the guild.")

    @is_guild_officer()
    @guild.command()
    @locale_doc
    async def kick(self, ctx, member: Union[MemberWithCharacter, int]):
        _("""[Guild Officer only] Kick someone from your guild.""")
        if hasattr(ctx, "user_data"):
            if ctx.user_data["guild"] != ctx.character_data["guild"]:
                return await ctx.send(_("Not your guild mate."))
            member = member.id
        else:
            if (
                await self.bot.pool.fetchval(
                    'SELECT guild FROM profile WHERE "user"=$1;', member
                )
                != ctx.character_data["guild"]
            ):
                return await ctx.send(_("Not your guild mate."))
        async with self.bot.pool.acquire() as conn:
            target_rank = await conn.fetchval(
                'SELECT guildrank FROM profile WHERE "user"=$1;', member
            )
            if target_rank != "Member":
                return await ctx.send(_("You can only kick members."))
            await conn.execute(
                'UPDATE profile SET "guild"=0, "guildrank"=$1 WHERE "user"=$2;',
                "Member",
                member,
            )
            channel = await conn.fetchval(
                'SELECT channel FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
        await ctx.send(_("The person has been kicked!"))
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** kicked user with ID **{member}**"
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def delete(self, ctx):
        _("""[Guild Owner only] Deletes the guild.""")
        if not await ctx.confirm(
            _("Are you sure to delete your guild? React to confirm the deletion.")
        ):
            return
        async with self.bot.pool.acquire() as conn:
            channel = await conn.fetchval(
                'DELETE FROM guild WHERE "leader"=$1 RETURNING "channel";',
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "guild"=$3;',
                0,
                "Member",
                ctx.character_data["guild"],
            )
        await ctx.send(_("Successfully deleted your guild."))
        await self.bot.http.send_message(channel, f"Guild deleted by **{ctx.author}**")

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def icon(self, ctx, url: str):
        _("""[Guild Leader only] Changes the guild icon.""")
        if len(url) > 60:
            return await ctx.send(_("URLs musn't exceed 60 characters."))
        if not (
            url.startswith("http")
            and (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg"))
        ):
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
            )
        channel = await self.bot.pool.fetchval(
            'UPDATE guild SET "icon"=$1 WHERE "id"=$2 RETURNING "channel";',
            url,
            ctx.character_data["guild"],
        )
        await ctx.send(_("Successfully updated the guild icon."))
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** changed the guild icon"
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def description(self, ctx, *, text: str):
        _("""[Guild Owner only] Changes the guild description.""")
        if len(text) > 200:
            return await ctx.send(_("The text may be up to 200 characters only."))
        channel = await self.bot.pool.fetchval(
            'UPDATE guild SET "description"=$1 WHERE "leader"=$2 RETURNING "channel";',
            text,
            ctx.author.id,
        )
        await ctx.send(_("Updated!"))
        await self.bot.http.send_message(
            channel, f"**{ctx.author}** changed the description"
        )

    @commands.has_permissions(administrator=True)
    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def channel(self, ctx):
        _(
            """[Guild Owner only] Change the logging channel for the guild. You also need to be server admin."""
        )
        if not await ctx.confirm(
            _("This will become the channel for all logs. Are you sure?")
        ):
            return
        await self.bot.pool.execute(
            'UPDATE guild SET "channel"=$1 WHERE "leader"=$2;',
            ctx.channel.id,
            ctx.author.id,
        )
        await ctx.send("**Guild logs will go here** ✅")

    @has_guild()
    @guild.command()
    @locale_doc
    async def richest(self, ctx):
        _("""Shows the richest players in your guild.""")
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            players = await conn.fetch(
                'SELECT "user", "name", "money" from profile WHERE "guild"=$1 ORDER BY "money" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for idx, profile in enumerate(players):
            charname = await rpgtools.lookup(self.bot, profile["user"])
            text = _("a character by `{charname}` with **${money}**").format(
                charname=charname, money=profile["money"]
            )
            result = f"{result}{idx + 1}. {profile['name']}, {text}\n"
        await ctx.send(
            embed=discord.Embed(
                title=_("The Richest Players of {guild}").format(guild=guild["name"]),
                description=result,
                colour=0xE7CA01,
            )
        )

    @has_guild()
    @guild.command(aliases=["high", "top"])
    @locale_doc
    async def best(self, ctx):
        _("""Shows the best players of your guild by XP.""")
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            players = await conn.fetch(
                'SELECT "user", "name", "xp" FROM profile WHERE "guild"=$1 ORDER BY "xp" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for idx, profile in enumerate(players):
            charname = await rpgtools.lookup(self.bot, profile[0])
            text = _(
                "{name}, a character by `{charname}` with Level **{level}** (**{xp}** XP)"
            ).format(
                charname=charname,
                name=profile["name"],
                level=rpgtools.xptolevel(profile["xp"]),
                xp=profile["xp"],
            )
            result = f"{result}{idx + 1}. {text}\n"
        await ctx.send(
            embed=discord.Embed(
                title=_("The Best Players of {name}").format(name=guild["name"]),
                description=result,
                colour=0xE7CA01,
            )
        )

    @has_guild()
    @guild.command()
    @locale_doc
    async def invest(self, ctx, amount: IntGreaterThan(0)):
        _("""Invest some of your money and put it to the guild bank.""")
        if ctx.character_data["money"] < amount:
            return await ctx.send(_("You're too poor."))
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if g["banklimit"] < g["money"] + amount:
                return await ctx.send(_("The bank would be full."))
            profile_money = await conn.fetchval(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2 RETURNING money;',
                amount,
                ctx.author.id,
            )
            guild_money = await conn.fetchval(
                'UPDATE guild SET money=money+$1 WHERE "id"=$2 RETURNING money;',
                amount,
                g["id"],
            )
        await ctx.send(
            _(
                "Done! Now you have `${profile_money}` and the guild has `${guild_money}`."
            ).format(profile_money=profile_money, guild_money=guild_money)
        )
        await self.bot.log_transaction(
            ctx, from_=ctx.author, to=0, subject="guild invest", data=amount
        )
        await self.bot.http.send_message(
            g["channel"], f"**{ctx.author}** invested **${amount}**"
        )

    @is_guild_officer()
    @guild.command()
    @locale_doc
    async def pay(self, ctx, amount: IntGreaterThan(0), member: MemberWithCharacter):
        _("""[Guild Officer only] Pay money from the guild bank to a user.""")
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if guild["money"] < amount:
                return await ctx.send(_("Your guild is too poor."))
            await conn.execute(
                'UPDATE guild SET money=money-$1 WHERE "id"=$2;', amount, guild["id"]
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', amount, member.id
            )
        await ctx.send(
            _(
                "Successfully gave **${amount}** from your guild bank to {member}."
            ).format(amount=amount, member=member.mention)
        )
        await self.bot.log_transaction(
            ctx, from_=0, to=member, subject="guild pay", data=amount
        )
        await self.bot.http.send_message(
            guild["channel"], f"**{ctx.author}** paid **${amount}** to **{member}**"
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def upgrade(self, ctx):
        _("""Upgrades your guild bank's capacity.""")
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            currentlimit = guild["banklimit"]
            newlimit = (guild["upgrade"] + 1) * 250000
            if guild["upgrade"] == 4:
                return await ctx.send(
                    _("Your guild already reached the maximum upgrade.")
                )
            if int(currentlimit / 2) > guild["money"]:
                return await ctx.send(
                    _(
                        "Your guild is too poor, you got **${money}** but it costs **${price}** to upgrade."
                    ).format(money=guild["money"], price=int(currentlimit / 2))
                )

            if not await ctx.confirm(
                _(
                    "This will upgrade your guild bank limit to **${newlimit}** for **${cost}**. Proceed?"
                ).format(newlimit=newlimit, cost=int(currentlimit / 2))
            ):
                return
            await conn.execute(
                'UPDATE guild SET "banklimit"=$1, "upgrade"="upgrade"+$2, "money"="money"-$3 WHERE "id"=$4;',
                newlimit,
                1,
                int(currentlimit / 2),
                guild["id"],
            )
        await ctx.send(
            _("Your new guild bank limit is now **${limit}**.").format(limit=newlimit)
        )
        await self.bot.http.send_message(
            guild["channel"],
            f"**{ctx.author}** upgraded the guild bank to **${newlimit}**",
        )

    @is_guild_officer()
    @guild_cooldown(1800)
    @guild.command()
    @locale_doc
    async def battle(
        self,
        ctx,
        enemy: MemberWithCharacter,
        amount: IntGreaterThan(-1),
        fightercount: IntGreaterThan(1),
    ):
        _("""Battle against another guild.""")
        if enemy == ctx.author:
            return await ctx.send(_("Poor kiddo having no friendos."))
        guild1 = ctx.character_data["guild"]
        guild2 = ctx.user_data["guild"]
        if guild1 == 0 or guild2 == 0:
            return await ctx.send(_("One of you both doesn't have a guild."))
        if (
            ctx.character_data["guildrank"] == "Member"
            or ctx.user_data["guildrank"] == "Member"
        ):
            return await ctx.send(_("One of you both isn't an officer of their guild."))
        async with self.bot.pool.acquire() as conn:
            guild1 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild1)
            guild2 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild2)
            if guild1["money"] < amount or guild2["money"] < amount:
                return await ctx.send(_("One of the guilds can't pay the price."))
            size1 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild1["id"]
            )
            size2 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild2["id"]
            )
        if size1 < fightercount or size2 < fightercount:
            return await ctx.send(_("One of the guilds is too small."))

        if not await ctx.confirm(
            f"{enemy.mention}, {ctx.author.mention} invites you to fight in a guild battle. React to join the battle. You got **1 Minute to accept**.",
            timeout=60,
            user=enemy,
        ):
            return await ctx.send(
                _("{enemy} didn't want to join your battle, {author}.").format(
                    enemy=enemy.mention, author=ctx.author.mention
                )
            )

        await ctx.send(
            _(
                "{enemy} accepted the challenge by {author}. Please now nominate members, {author}. Use `battle nominate @user` to add someone to your team."
            ).format(enemy=enemy.mention, author=ctx.author.mention)
        )
        team1 = []
        team2 = []
        converter = User()

        async def guildcheck(already, guildid, user):
            try:
                member = await converter.convert(ctx, user)
            except commands.errors.BadArgument:
                return False
            guild = await self.bot.pool.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1;', member.id
            )
            if guild != guildid:
                await ctx.send(_("That person isn't in your guild."))
                return False
            if member in already:
                return False
            return member

        def simple1(msg):
            return msg.author == ctx.author and msg.content.startswith(
                "battle nominate"
            )

        def simple2(msg):
            return msg.author == enemy and msg.content.startswith("battle nominate")

        while len(team1) != fightercount:
            try:
                res = await self.bot.wait_for("message", timeout=30, check=simple1)
                guild1check = await guildcheck(
                    team1, guild1["id"], res.content.split()[-1]
                )
                if guild1check:
                    team1.append(guild1check)
                    await ctx.send(
                        _("{user} has been added to your team, {author}.").format(
                            user=guild1check, author=ctx.author.mention
                        )
                    )
                else:
                    await ctx.send(_("User not found."))
                    continue
            except asyncio.TimeoutError:
                await self.bot.reset_guild_cooldown(ctx)
                return await ctx.send(
                    _("Took to long to add members. Fight cancelled.")
                )
        await ctx.send(
            _(
                "Please now nominate members, {enemy}. Use `battle nominate @user` to add someone to your team."
            ).format(enemy=enemy.mention)
        )
        while len(team2) != fightercount:
            try:
                res = await self.bot.wait_for("message", timeout=30, check=simple2)
                guild2check = await guildcheck(
                    team2, guild2["id"], res.content.split()[-1]
                )
                if guild2check:
                    team2.append(guild2check)
                    await ctx.send(
                        _("{user} has been added to your team, {enemy}.").format(
                            user=guild2check, enemy=enemy.mention
                        )
                    )
                else:
                    await ctx.send(_("User not found."))
                    continue
            except asyncio.TimeoutError:
                await self.bot.reset_guild_cooldown(ctx)
                return await ctx.send(
                    _("Took to long to add members. Fight cancelled.")
                )

        msg = await ctx.send(_("Fight started!\nGenerating battles..."))
        await asyncio.sleep(3)
        await msg.edit(content=_("Fight started!\nGenerating battles... Done."))
        wins1 = 0
        wins2 = 0
        for idx, user in enumerate(team1):
            user2 = team2[idx]
            msg = await ctx.send(
                _(
                    "Guild Battle Fight **{num}** of **{total}**.\n**{user}** vs **{user2}**!\nBattle running..."
                ).format(num=idx + 1, total=len(team1), user=user, user2=user2)
            )
            sw1, sh1 = await self.bot.get_equipped_items_for(user)
            val1 = (
                (sw1["damage"] if sw1 else 0)
                + (sh1["armor"] if sh1 else 0)
                + random.randint(1, 7)
            )
            sw2, sh2 = await self.bot.get_equipped_items_for(user2)
            val2 = (
                (sw2["damage"] if sw2 else 0)
                + (sh2["armor"] if sh2 else 0)
                + random.randint(1, 7)
            )
            if val1 > val2:
                winner = user
                wins1 += 1
            elif val2 > val1:
                winner = user2
                wins2 += 1
            else:
                winner = random.choice([user, user2])
                if winner == user:
                    wins1 += 1
                else:
                    wins2 += 1
            await asyncio.sleep(5)
            await ctx.send(
                _(
                    "Winner of **{user}** vs **{user2}** is **{winner}**! Current points: **{wins1}** to **{wins2}**."
                ).format(
                    user=user, user2=user2, winner=winner, wins1=wins1, wins2=wins2
                )
            )
        async with self.bot.pool.acquire() as conn:
            money1 = await conn.fetchval(
                'SELECT money FROM guild WHERE "id"=$1;', guild1["id"]
            )
            money2 = await conn.fetchval(
                'SELECT money FROM guild WHERE "id"=$1;', guild2["id"]
            )
            if money1 < amount or money2 < amount:
                return await ctx.send(_("Some guild spent the money??? Bad looser!"))
            if wins1 > wins2:
                await conn.execute(
                    'UPDATE guild SET money=money+$1 WHERE "id"=$2;',
                    amount,
                    guild1["id"],
                )
                await conn.execute(
                    'UPDATE guild SET money=money-$1 WHERE "id"=$2;',
                    amount,
                    guild2["id"],
                )
                await conn.execute(
                    'UPDATE guild SET wins=wins+1 WHERE "id"=$1;', guild1["id"]
                )
                await ctx.send(
                    _("{guild} won the battle! Congratulations!").format(
                        guild=guild1["name"]
                    )
                )
            elif wins2 > wins1:
                await conn.execute(
                    'UPDATE guild SET money=money+$1 WHERE "id"=$2;',
                    amount,
                    guild2["id"],
                )
                await conn.execute(
                    'UPDATE guild SET money=money-$1 WHERE "id"=$2;',
                    amount,
                    guild1["id"],
                )
                await conn.execute(
                    'UPDATE guild SET wins=wins+1 WHERE "id"=$1;', guild2["id"]
                )
                await ctx.send(
                    _("{guild} won the battle! Congratulations!").format(
                        guild=guild2["name"]
                    )
                )
            else:
                await ctx.send(_("It's a tie!"))

    @is_guild_officer()
    @guild_cooldown(3600)
    @guild.command()
    @locale_doc
    async def adventure(self, ctx):
        _("""Starts a guild adventure.""")
        if await self.bot.get_guild_adventure(ctx.character_data["guild"]):
            await self.bot.reset_guild_cooldown(ctx)
            return await ctx.send(
                _(
                    "Your guild is already on an adventure! Use `{prefix}guild status` to view how long it still lasts."
                ).format(prefix=ctx.prefix)
            )
        guild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )

        msg = await ctx.send(
            _(
                "{author} seeks a guild adventure for **{guild}**! React to join! Unlimited players can join in the next minute. The minimum of players required is 3."
            ).format(author=ctx.author.mention, guild=guild["name"])
        )

        await msg.add_reaction("\U00002694")

        joined = [ctx.author]
        difficulty = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        started = False

        def apply(r, u):
            return (
                r.message.id == msg.id
                and str(r.emoji) == "\U00002694"
                and u not in joined
                and not u.bot
            )

        while not started:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=apply, timeout=300)
                user = await self.bot.pool.fetchrow(
                    'SELECT guild, xp FROM profile WHERE "user"=$1;', u.id
                )
                if user and user["guild"] == guild["id"]:
                    difficulty += int(rpgtools.xptolevel(user["xp"]))
                    joined.append(u)
                    await ctx.send(
                        _("Alright, {user}, you have been added.").format(
                            user=u.mention
                        )
                    )
                else:
                    await ctx.send(_("You aren't in their guild."))
            except asyncio.TimeoutError:
                if len(joined) < 3:
                    await self.bot.reset_guild_cooldown(ctx)
                    return await ctx.send(
                        _(
                            "You didn't get enough other players for the guild adventure."
                        )
                    )
                started = True

        time = timedelta(hours=difficulty * 0.5)

        await self.bot.start_guild_adventure(guild["id"], difficulty, time)

        await ctx.send(
            _(
                """
Guild adventure for **{guild}** started!
Participants:
{participants}

Difficulty is **{difficulty}**
Time it will take: **{time}**
"""
            ).format(
                guild=guild["name"],
                participants=", ".join([m.mention for m in joined]),
                difficulty=difficulty,
                time=time,
            )
        )
        await self.bot.http.send_message(
            guild["channel"],
            f"Guild adventure with difficulty **{difficulty}**, lasting **{time}**, started",
        )

    @has_guild()
    @guild.command()
    @locale_doc
    async def status(self, ctx):
        _("""Views your guild adventure.""")
        adventure = await self.bot.get_guild_adventure(ctx.character_data["guild"])

        if not adventure:
            return await ctx.send(
                _(
                    "Your guild isn't on an adventure yet. Ask your guild leader to use `{prefix}guild adventure` to start one"
                ).format(prefix=ctx.prefix)
            )

        if adventure[2]:
            await self.bot.delete_guild_adventure(ctx.character_data["guild"])
            gold = random.randint(adventure[0] * 20, adventure[0] * 50)

            channel = await self.bot.pool.fetchval(
                'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2 RETURNING "channel";',
                gold,
                ctx.character_data["guild"],
            )
            await ctx.send(
                _(
                    "Your guild has completed an adventure of difficulty `{difficulty}` and **${gold}** has been added to the bank."
                ).format(difficulty=adventure[0], gold=gold)
            )
            await self.bot.http.send_message(
                channel,
                f"**{ctx.author}** ended the guild adventure, reward was **${gold}**",
            )
        else:
            await ctx.send(
                _(
                    "Your guild is currently in an adventure with difficulty `{difficulty}`.\nTime remaining: `{remain}`"
                ).format(
                    difficulty=adventure[0], remain=str(adventure[1]).split(".")[0]
                )
            )

    '''
    @has_guild()
    @guild.command()
    @locale_doc
    async def event(self, ctx):
        _("""View your guild's progress in the ongoing event.""")
        pumpkins = await self.bot.pool.fetchval(
            'SELECT pumpkins FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )
        val = int(pumpkins / 50000 * 10)
        percent = round(pumpkins / 50000 * 100, 2)
        if val > 10:
            val = 10
        progress = f"{'▣' * val}{'▢' * (10 - val)}"
        await ctx.send(
            _(
                """\
**Halloween 2019 🎃 👻**

*Progress for best reward*
{bar} {percent}% {pumpkins}/50,000 🎃

*Prices for claiming*
`(ID for {prefix}guild claim) Amount 🎃: Reward`
**(1)** 1000 🎃: **$5000** Guild Bank Fill
**(2)** 5000 🎃: **$27500** Guild Bank Fill
**(3)** 10000 🎃: **$60000** Guild Bank Fill
**(4)** 25000 🎃: **$175000** Guild Bank Fill

**(5)** 37500 🎃: Halloween 2019 Guild Badge #1
**(6)** 50000 🎃: Halloween 2019 Guild Badge #2

**(7)** 10000 🎃: 2 additional guild member slots
**(8)** 20000 🎃: 5 additional guild member slots
**(9)** 35000 🎃: 8 additional guild member slots
**(10)** 50000 🎃: 15 additional guild member slots
*Please note that these will be **gone** if the leader uses `{prefix}updateguild`, so choose carefully*"""
            ).format(
                bar=progress, percent=percent, pumpkins=pumpkins, prefix=ctx.prefix
            )
        )

    @is_guild_leader()
    @guild.command()
    @locale_doc
    async def claim(self, ctx, reward_id: IntFromTo(1, 10)):
        _("""[Guild Leader only] Claim event rewards.""")
        reward = [
            {"price": 1000, "reward": "money", "data": 5000},
            {"price": 5000, "reward": "money", "data": 27500},
            {"price": 10000, "reward": "money", "data": 60000},
            {"price": 25000, "reward": "money", "data": 175000},
            {
                "price": 37500,
                "reward": "badge",
                "data": "https://idlerpg.travitia.xyz/halloween_2019_1.png",
            },
            {
                "price": 50000,
                "reward": "badge",
                "data": "https://idlerpg.travitia.xyz/halloween_2019_2.png",
            },
            {"price": 10000, "reward": "members", "data": 2},
            {"price": 20000, "reward": "members", "data": 5},
            {"price": 35000, "reward": "members", "data": 8},
            {"price": 50000, "reward": "members", "data": 15},
        ][reward_id - 1]
        async with self.bot.pool.acquire() as conn:
            if (
                await conn.fetchval(
                    'SELECT pumpkins FROM guild WHERE "id"=$1;',
                    ctx.character_data["guild"],
                )
                < reward["price"]
            ):
                return await ctx.send(
                    _("You have insufficient pumpkins for this reward.")
                )
            await conn.execute(
                'UPDATE guild SET "pumpkins"="pumpkins"-$1 WHERE "id"=$2;',
                reward["price"],
                ctx.character_data["guild"],
            )
            if reward["reward"] == "money":
                await conn.execute(
                    'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2;',
                    reward["data"],
                    ctx.character_data["guild"],
                )
            elif reward["reward"] == "badge":
                await conn.execute(
                    'UPDATE guild SET "badges"=array_append("badges", $1) WHERE "id"=$2;',
                    reward["data"],
                    ctx.character_data["guild"],
                )
            elif reward["reward"] == "members":
                await conn.execute(
                    'UPDATE guild SET "memberlimit"="memberlimit"+$1 WHERE "id"=$2;',
                    reward["data"],
                    ctx.character_data["guild"],
                )
        await ctx.send(
            _("Reward successfully claimed for **{amount}** 🎃!").format(
                amount=reward["price"]
            )
        )
        '''


def setup(bot):
    bot.add_cog(Guild(bot))
