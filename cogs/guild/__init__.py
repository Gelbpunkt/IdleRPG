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
import asyncio

from contextlib import suppress
from datetime import timedelta
from typing import Union

import discord

from discord.ext import commands

from classes.converters import (
    ImageFormat,
    ImageUrl,
    IntGreaterThan,
    MemberWithCharacter,
    User,
    UserWithCharacter,
)
from cogs.shard_communication import guild_on_cooldown as guild_cooldown
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils import random
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
from utils.i18n import _, locale_doc
from utils.markdown import escape_markdown


class Guild(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.group(invoke_without_command=True, brief=_("Interact with your guild."))
    @locale_doc
    async def guild(self, ctx):
        _(
            """Interact with your guild. If no subcommand is given, this will show your guild.

            Guilds are groups of players, they have a guild bank where money can be kept safe from thieves and the guild's members can go on adventures to earn extra rewards.
            Players cannot join guilds by themselves, they must be invited by the guild leader or one of its officers."""
        )
        if not ctx.character_data["guild"]:
            return await ctx.send(_("You are not in a guild yet."))
        await self.get_guild_info(ctx, guild_id=ctx.character_data["guild"])

    async def get_guild_info(
        self, ctx: commands.Context, *, guild_id: int = None, name: str = None
    ):
        async with self.bot.pool.acquire() as conn:
            if name:
                guild = await conn.fetchrow(
                    'SELECT * FROM guild WHERE "name"=$1;', name
                )
            elif guild_id:
                guild = await conn.fetchrow(
                    'SELECT * FROM guild WHERE "id"=$1;', guild_id
                )
            if not guild:
                return await ctx.send(_("No guild found."))

            membercount = await conn.fetchval(
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
        url = await ImageUrl(ImageFormat.all_static).convert(
            ctx, guild["icon"], silent=True
        )
        if url:
            embed.set_thumbnail(url=str(url))
        embed.set_footer(text=_("Guild ID: {id}").format(id=guild["id"]))
        if guild["badge"]:
            embed.set_image(url=guild["badge"])
        await ctx.send(embed=embed)

    @guild.command(brief=_("Show a specific guild"))
    @locale_doc
    async def info(self, ctx, *, by: Union[MemberWithCharacter, str]):
        _(
            """`<by>` - The guild's name (format `guild:name`, i.e. `guild:Adrian's Refuge`), its ID (format `id:number`, i.e. `id:5003`), or a person in the guild.

            Show a specific guild's info. You can look up guilds by its name, its ID, or a player in that guild."""
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
            guild_id = await self.bot.cache.get_profile_col(by.id, "guild")
            if not guild_id:
                return await ctx.send(
                    _("**{user}** does not have a guild.").format(user=by.name)
                )
            kwargs.update(guild_id=guild_id)
        await self.get_guild_info(ctx, **kwargs)

    @guild.command(brief=_("Show the best guilds by GvG wins"))
    @locale_doc
    async def ladder(self, ctx):
        _(
            """Shows the top 10 guilds ordered by Guild vs Guild wins.

            To get more GvG wins, the guild leader or its officers can use `{prefix}guild battle`."""
        )
        guilds = await self.bot.pool.fetch(
            "SELECT * FROM guild ORDER BY wins DESC LIMIT 10;"
        )
        result = ""
        for idx, guild in enumerate(guilds):
            leader = await rpgtools.lookup(self.bot, guild["leader"])
            text = _("a guild by {leader} with **{wins}** GvG Wins").format(
                leader=escape_markdown(leader), wins=guild["wins"]
            )
            result = f"{result}{idx + 1}. {guild['name']}, {text}\n"
        await ctx.send(
            embed=discord.Embed(
                title=_("The Best GvG Guilds"), description=result, colour=0xE7CA01
            )
        )

    @has_guild()
    @guild.command(brief=_("Show a list of your guild members."))
    @locale_doc
    async def members(self, ctx):
        _(
            """Show a list of your guild members. If a user's name cannot be found for whatever reason, their user ID is displayed.

            This command can take a minute to load, depending on the amount of members in your guild. Please be patient.

            Only players who are part of a guild can use this command."""
        )
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
            members_fmt.append(f"{escape_markdown(u)} ({m['guildrank']})")
        await self.bot.paginator.Paginator(
            entries=members_fmt, title=_("Your guild mates")
        ).paginate(ctx)

    @has_char()
    @is_guild_leader()
    @guild.command(brief=_("Change your guild's badge"))
    @locale_doc
    async def badge(self, ctx, number: IntGreaterThan(0)):
        _(
            """`<number>` - The number of the guild badge to use, ranging from 1 to the amount of available badges

            Change your guild's badge, it will display in `{prefix}guild info`.

            Only guild leaders can use this command."""
        )
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
                        "The badge number {number} is not valid, your guild only has"
                        " {amount} available."
                    ).format(amount=len(bgs), number=number)
                )
            await conn.execute(
                'UPDATE guild SET badge=$1 WHERE "leader"=$2;', bg, ctx.author.id
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** changed the guild badge."
                )
        await ctx.send(_("Badge updated!"))

    @has_char()
    @has_no_guild()
    @user_cooldown(600)
    @guild.command(brief=_("Create a guild"))
    @locale_doc
    async def create(self, ctx):
        _(
            """Create a guild for $10,000.

            Creating a guild has no level requirements, as long as you have $10,000, you can create a guild.
            To create a guild, you will need the following:
              - A name with 20 characters or less
              - An image URL with 60 characters or less to your guild's icon
              - $10,000

            Having trouble finding a short image URL? Check [this tutorial](https://wiki.idlerpg.xyz/index.php?title=Tutorial:_Short_Image_URLs)

            The bot will ask for these separately. When you enter the guild's name or URL, don't include `{prefix}`.

            Only players who are not already in a guild can use this command.
            (This command has a cooldown of 10 minuets.)"""
        )

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
            urlmsg = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Cancelled guild creation."))
        url = urlmsg.content
        if (urllength := len(url)) == 0:
            if not urlmsg.attachments:
                #  no idea how this would happen but eh
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(_("Cancelled guild creation."))
            file_url = await ImageUrl(ImageFormat.all_static).convert(
                ctx, urlmsg.attachments[0].url
            )
            await ctx.send(
                _("No image URL found in your message, using image attachment...")
            )
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(file_url)
        elif urllength > 60:
            url = await ImageUrl(ImageFormat.all_static).convert(ctx, url)
            await ctx.send(_("Image URL too long, shortening..."))
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(url)
        else:
            icon_url = await ImageUrl(ImageFormat.all_static).convert(ctx, url)
        if await user_is_patron(self.bot, ctx.author):
            memberlimit = 100
        else:
            memberlimit = 50

        if not await ctx.confirm(
            _("Are you sure? React to create a guild for **$10000**")
        ):
            return
        async with self.bot.pool.acquire() as conn:
            if not await has_money(self.bot, ctx.author.id, 10000, conn=conn):
                return await ctx.send(
                    _("A guild creation costs **$10000**, you are too poor.")
                )
            if await conn.fetchrow('SELECT * FROM guild WHERE "name"=$1;', name):
                return await ctx.send(_("The guild name is taken."))
            guild = await conn.fetchrow(
                "INSERT INTO guild (name, memberlimit, leader, icon) VALUES ($1, $2,"
                " $3, $4) RETURNING *;",
                name,
                memberlimit,
                ctx.author.id,
                icon_url,
            )
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2, "money"="money"-$3'
                ' WHERE "user"=$4;',
                guild["id"],
                "Leader",
                10000,
                ctx.author.id,
            )
        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, guild=guild["id"], guildrank="Leader", money=-10000
        )
        await ctx.send(
            _(
                "Successfully added your guild **{name}** with a member limit of"
                " **{memberlimit}**.\n\nTip: You can use `{prefix}guild channel` in a"
                " server where you are the admin to set up the guild logging channel."
            ).format(name=name, memberlimit=memberlimit, prefix=ctx.prefix)
        )

    @is_guild_leader()
    @guild.command(brief=_("Give your guild to someone else"))
    @locale_doc
    async def transfer(self, ctx, member: MemberWithCharacter):
        _(
            """`<member>` - A discord User with a character, must be a member of your guild.

            Transfer your guild to someone else. This person will be the new guild leader, while you will become a regular member.

            If the user you transfer the guild to is a patron, the guild's member limit will be set to 100, otherwise it will be set to 50.

            Only guild leaders can use this command."""
        )
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
            await self.bot.cache.update_profile_cols_abs(
                ctx.author.id, guildrank="Member"
            )
            await self.bot.cache.update_profile_cols_abs(member.id, guildrank="Leader")
            name, channel = await conn.fetchval(
                'UPDATE guild SET "leader"=$1, "banklimit"="upgrade"*250000,'
                ' "memberlimit"=$2 WHERE "id"=$3 RETURNING ("name", "channel");',
                member.id,
                m,
                ctx.character_data["guild"],
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"Ownership changed from **{ctx.author}** to **{member}**"
                )
        await ctx.send(_("{user} now leads {guild}.").format(user=member, guild=name))

    @is_guild_leader()
    @guild.command(brief=_("Promote a guild member to officer."))
    @locale_doc
    async def promote(self, ctx, member: MemberWithCharacter):
        _(
            """`<member>` - A discord User with a character, must be a member of your guild

            Promote a member of your guild to the officer rank. This allows them to use certain guild commands. Officers can:
              - Invite new members
              - Kick members from the guild (cannot kick officers)
              - Take money out of the guild bank
              - Distribute money from the guild bank
              - Start battles with other guilds
              - Start and finish guild adventures

            Officers cannot be kicked from your guild and must be demoted first.
            Only promote members you trust. You can demote officers using `{prefix}guild demote`.

            Only guild leaders can use this command."""
        )
        if member == ctx.author:
            return await ctx.send(_("Very funny..."))
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send(_("Target is not a member of your guild."))
        if ctx.user_data["guildrank"] == "Officer":
            return await ctx.send(_("This user is already an officer of your guild."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guildrank"=$1 WHERE "user"=$2;',
                "Officer",
                member.id,
            )
            await self.bot.cache.update_profile_cols_abs(member.id, guildrank="Officer")
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel,
                    f"**{ctx.author}** promoted **{member}** to the rank of Officer.",
                )
        await ctx.send(
            _("Done! {member} has been promoted to the rank of `Officer`.").format(
                member=member
            )
        )

    @is_guild_leader()
    @guild.command(brief=_("Demote a guild officer to member."))
    @locale_doc
    async def demote(self, ctx, member: UserWithCharacter):
        _(
            """`<member>` - A discord User with a character, must be an officer of your guild

            Demotes an officer of your guild to member rank. The user will lose their guild officer permissions immediately.

            Only guild leaders can use this command."""
        )
        if member == ctx.author:
            return await ctx.send(_("Very funny..."))
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send(_("Target is not a member of your guild."))
        if ctx.user_data["guildrank"] != "Officer":
            return await ctx.send(_("This user can't be demoted any further."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guildrank"=$1 WHERE "user"=$2;',
                "Member",
                member.id,
            )
            await self.bot.cache.update_profile_cols_abs(member.id, guildrank="Member")
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel,
                    f"**{ctx.author}** demoted **{member}** to the rank of Member.",
                )
        await ctx.send(
            _("Done! {member} has been demoted to the rank of `Member`.").format(
                member=member
            )
        )

    @is_guild_officer()
    @guild.command(brief=_("Invite new members to your guild."))
    @locale_doc
    async def invite(self, ctx, newmember: MemberWithCharacter):
        _(
            """`<member>` - A discord user with a character who is not yet in a guild.

            Invites a new member to your guild.
            If your guild is in an alliance which owns a city, the new member will have its bonuses applied immediately.

            Only guild leaders and officers can use this command."""
        )
        if newmember == ctx.me:
            return await ctx.send(
                _("...me? I'm flattered, but I can't accept this invitation...")
            )
        if ctx.user_data["guild"]:
            return await ctx.send(_("That member already has a guild."))
        async with self.bot.pool.acquire() as conn:
            id_ = await self.bot.cache.get_profile_col(
                ctx.author.id, "guild", conn=conn
            )
            membercount = await conn.fetchval(
                'SELECT COUNT(*) FROM profile WHERE "guild"=$1;', id_
            )
            limit, name, channel = await conn.fetchval(
                'SELECT (memberlimit, name, channel) FROM guild WHERE "id"=$1;', id_
            )
        if membercount >= limit:
            return await ctx.send(
                _("Your guild is already at the maximum member count.")
            )

        if not await ctx.confirm(
            _(
                "{newmember}, {author} invites you to join **{name}**. React to join"
                " the guild."
            ).format(newmember=newmember.mention, author=ctx.author.mention, name=name),
            user=newmember,
        ):
            return
        if await has_guild_(self.bot, newmember.id):
            return await ctx.send(_("That member already has a guild."))
        await self.bot.pool.execute(
            'UPDATE profile SET "guild"=$1 WHERE "user"=$2;', id_, newmember.id
        )
        await self.bot.cache.update_profile_cols_abs(newmember.id, guild=id_)
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** invited **{newmember}** to the guild"
                )
        await ctx.send(
            _("{newmember} is now a member of **{name}**. Welcome!").format(
                newmember=newmember.mention, name=name
            )
        )

    @has_guild()
    @is_no_guild_leader()
    @guild.command(brief=_("Leave your guild"))
    @locale_doc
    async def leave(self, ctx):
        _(
            """Leave your current guild

            If your guild was in an alliance which owned a city, you will have its bonuses removed immediately.

            Only players who are in a guild, beside guild leaders, can use this command."""
        )
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "user"=$3;',
                0,
                "Member",
                ctx.author.id,
            )
            await self.bot.cache.update_profile_cols_abs(
                ctx.author.id, guild=0, guildrank="Member"
            )
            channel = await conn.fetchval(
                'SELECT "channel" FROM guild WHERE "id"=$1;',
                ctx.character_data["guild"],
            )

        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** left the guild."
                )
        await ctx.send(_("You left your guild."))

    @is_guild_officer()
    @guild.command(brief=_("Kick a member from your guild."))
    @locale_doc
    async def kick(self, ctx, member: Union[MemberWithCharacter, int]):
        _(
            """`<member>` - A discord User with a character, must be a member of your guild

            Kicks a member from your guild. Officers cannot be kicked.
            If your guild is in an alliance which owns a city, the member will have its bonuses removed immediately.

            If the member shares no server with you, you may use their [User ID](https://support.discordapp.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) as the member parameter.

            Only guild leaders and officers can use this command."""
        )
        if not hasattr(ctx, "user_data"):
            ctx.user_data = await self.bot.cache.get_profile(member)
        else:
            member = member.id

        if ctx.user_data["guild"] != ctx.character_data["guild"]:
            return await ctx.send(_("Not your guild mate."))
        if ctx.user_data["guildrank"] != "Member":
            return await ctx.send(_("You can only kick members."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "guild"=0, "guildrank"=$1 WHERE "user"=$2;',
                "Member",
                member,
            )
            await self.bot.cache.update_profile_cols_abs(
                member, guild=0, guildrank="Member"
            )
            channel = await conn.fetchval(
                'SELECT channel FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** kicked user with ID **{member}**"
                )
        await ctx.send(_("The person has been kicked!"))

    @is_guild_leader()
    @guild.command(brief=_("Delete your guild"))
    @locale_doc
    async def delete(self, ctx):
        _(
            """Delete your guild.

            If you would just like to leave the guild, consider transferring it to someone, then leaving normally.

            If your guild was in an alliance which owned a city, all members will lose its bonuses immediately.

            Only guild leaders can use this command."""
        )
        if not await ctx.confirm(
            _("Are you sure to delete your guild? React to confirm the deletion.")
        ):
            return
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    'UPDATE city SET "owner"=1 WHERE "owner"=$1;',
                    ctx.character_data["guild"],
                )
                channel = await conn.fetchval(
                    'DELETE FROM guild WHERE "leader"=$1 RETURNING "channel";',
                    ctx.author.id,
                )
                users = await conn.fetch(
                    'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "guild"=$3'
                    ' RETURNING "user";',
                    0,
                    "Member",
                    ctx.character_data["guild"],
                )
        for user in users:
            await self.bot.cache.update_profile_cols_abs(
                user["user"], guild=0, guildrank="Member"
            )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"Guild deleted by **{ctx.author}**"
                )
        await ctx.send(_("Successfully deleted your guild."))

    @is_guild_leader()
    @guild.command(brief=_("Change your guild's icon"))
    @locale_doc
    async def icon(self, ctx, url: ImageUrl(ImageFormat.all_static) = ""):
        _(
            """`[url]` - The image URL to use as the icon

            Change your guild's icon. The URL cannot exceed 60 characters.
            ⚠ This can be seen by anyone, do not use NSFW/innapropriate images. GIFs are not supported.

            Having trouble finding short image URLs? Follow [this tutorial](https://wiki.idlerpg.xyz/index.php?title=Tutorial:_Short_Image_URLs) or just attach the image you want to use (png, jpg and gif are supported)!

            Only guild leaders can use this command."""
        )
        if (urllength := len(url)) == 0:
            if not ctx.message.attachments:
                current_icon = await self.bot.pool.fetchval(
                    'SELECT icon FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
                )
                return await ctx.send(
                    _("Your current guild icon is: {url}").format(url=current_icon)
                )
            file_url = await ImageUrl(ImageFormat.all_static).convert(
                ctx, ctx.message.attachments[0].url
            )
            await ctx.send(
                _("No image URL found in your message, using image attachment...")
            )
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(file_url)
        elif urllength > 60:
            await ctx.send(_("Image URL too long, shortening..."))
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(url)
        else:
            icon_url = url
        channel = await self.bot.pool.fetchval(
            'UPDATE guild SET "icon"=$1 WHERE "id"=$2 RETURNING "channel";',
            icon_url,
            ctx.character_data["guild"],
        )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** changed the guild icon"
                )
        await ctx.send(_("Successfully updated the guild icon."))

    @is_guild_leader()
    @guild.command(brief=_("Change your guild description."))
    @locale_doc
    async def description(self, ctx, *, text: str):
        _(
            """`<text>` - The text to use as the description. Cannot exceed 200 characters.

            Change the description of your guild.
            ⚠ This can be seen by everyone, do not use NSFW/inappropriate text.

            Only guild leaders can use this command."""
        )
        if len(text) > 200:
            return await ctx.send(_("The text may be up to 200 characters only."))
        channel = await self.bot.pool.fetchval(
            'UPDATE guild SET "description"=$1 WHERE "leader"=$2 RETURNING "channel";',
            text,
            ctx.author.id,
        )
        if channel:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    channel, f"**{ctx.author}** changed the description"
                )
        await ctx.send(_("Updated!"))

    @commands.has_permissions(administrator=True)
    @is_guild_leader()
    @guild.command(brief=_("Set/update the guild update channel."))
    @locale_doc
    async def channel(self, ctx, channel: discord.TextChannel = None):
        _(
            """`[channel]` - The channel to send guild logs to, defaults to the channel the command is used in

            Set or update the guild update channel. Relevant guild events will be sent here.
            The channel the command is used in will become the guild log channel, `{prefix}guild channel #channel-name` will not work.

            The following will be logged:
              - Guild badge updated
              - Guild transferred
              - Guild promotions
              - Guild demotions
              - New member joins
              - Members leaving the guild
              - Member kicks
              - Guild deletion
              - Guild icon changes
              - Guild description changes
              - Money invests
              - Money payouts
              - Money distributions
              - Guild bank upgrades
              - Guild adventures (start and end)

            Only guild leaders can use this command."""
        )
        channel = channel or ctx.channel
        if not await ctx.confirm(
            _("{channel} will become the channel for all logs. Are you sure?").format(
                channel=channel.mention
            )
        ):
            return
        if not channel.permissions_for(ctx.me).send_messages:
            return await ctx.send(
                _(
                    "I cannot send messages there! This channel cannot be the guild log"
                    " channel."
                )
            )
        await self.bot.pool.execute(
            'UPDATE guild SET "channel"=$1 WHERE "leader"=$2;',
            channel.id,
            ctx.author.id,
        )
        await ctx.send(
            _("**Guild logs will go to {channel} ** ✅").format(channel=channel.mention)
        )

    @has_guild()
    @guild.command(brief=_("Show the richest guild members"))
    @locale_doc
    async def richest(self, ctx):
        _(
            """Displays the top 10 richest guild members of your guild.

            Only players in a guild can use this command."""
        )
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            players = await conn.fetch(
                'SELECT "user", "name", "money" from profile WHERE "guild"=$1 ORDER BY'
                ' "money" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for idx, profile in enumerate(players):
            charname = await rpgtools.lookup(self.bot, profile["user"])
            text = _("a character by {charname} with **${money}**").format(
                charname=escape_markdown(charname), money=profile["money"]
            )
            result = f"{result}{idx + 1}. {escape_markdown(profile['name'])}, {text}\n"
        await ctx.send(
            embed=discord.Embed(
                title=_("The Richest Players of {guild}").format(guild=guild["name"]),
                description=result,
                colour=0xE7CA01,
            )
        )

    @has_guild()
    @guild.command(
        aliases=["high", "top"], brief=_("Show the best guild members by XP")
    )
    @locale_doc
    async def best(self, ctx):
        _(
            """Displays the top 10 best guild members of your guild ordered by XP.

            Only players in a guild can use this command."""
        )
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            players = await conn.fetch(
                'SELECT "user", "name", "xp" FROM profile WHERE "guild"=$1 ORDER BY'
                ' "xp" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for idx, profile in enumerate(players):
            charname = await rpgtools.lookup(self.bot, profile[0])
            text = _(
                "{name}, a character by {charname} with Level **{level}** (**{xp}** XP)"
            ).format(
                charname=escape_markdown(charname),
                name=escape_markdown(profile["name"]),
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
    @guild.command(brief=_("Add money to your guild bank"))
    @locale_doc
    async def invest(self, ctx, amount: IntGreaterThan(0)):
        _(
            """`<amount>` - A whole number greater than 0

            Invest money into your guild bank, keeping it safe from thieves.

            Only guild officers can take money out of the guild bank.

            The money in the guild bank can be used to upgrade the bank or upgrade buildings/build defenses in your alliance, if it owns a city."""
        )
        if ctx.character_data["money"] < amount:
            return await ctx.send(_("You're too poor."))
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if g["banklimit"] < g["money"] + amount:
                return await ctx.send(_("The bank would be full."))
            profile_money = await conn.fetchval(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2 RETURNING'
                " money;",
                amount,
                ctx.author.id,
            )
            await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-amount)
            guild_money = await conn.fetchval(
                'UPDATE guild SET money=money+$1 WHERE "id"=$2 RETURNING money;',
                amount,
                g["id"],
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author,
                to=0,
                subject="guild invest",
                data={"Amount": amount},
                conn=conn,
            )
        if g["channel"]:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    g["channel"], f"**{ctx.author}** invested **${amount}**"
                )
        await ctx.send(
            _(
                "Done! Now you have `${profile_money}` and the guild has"
                " `${guild_money}`."
            ).format(profile_money=profile_money, guild_money=guild_money)
        )

    @is_guild_officer()
    @guild.command(brief=_("Take money out of the guild bank"))
    @locale_doc
    async def pay(self, ctx, amount: IntGreaterThan(0), member: MemberWithCharacter):
        _(
            """`<amount>` - The amount of money to take out of the bank, must be greater than 0 and smaller or equal the amount your guild has
            `<member>` - A discord User with a character.

            Take money out of the guild bank and give it to a user. The user does not have to be a member of your guild.

            Only guild leaders and officers can use this command."""
        )
        if member == ctx.me:
            return await ctx.send(
                _("For me? I'm flattered, but I can't accept this...")
            )
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if guild["money"] < amount:
                return await ctx.send(_("Your guild is too poor."))
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                amount,
                guild["id"],
            )
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                amount,
                member.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=0,
                to=member,
                subject="guild pay",
                data={"Amount": amount},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(member.id, money=amount)
        if guild["channel"]:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    guild["channel"],
                    f"**{ctx.author}** paid **${amount}** to **{member}**",
                )
        await ctx.send(
            _(
                "Successfully gave **${amount}** from your guild bank to {member}."
            ).format(amount=amount, member=member.mention)
        )

    @is_guild_officer()
    @guild.command(
        aliases=["dis", "distrib"], brief=_("Pay out money to multiple members")
    )
    @locale_doc
    async def distribute(
        self, ctx, amount: IntGreaterThan(0), *members: MemberWithCharacter
    ):
        _(
            """`<amount>` - The amount of money to take out all together, must be greater than 0
            `<members...>` - The discord users to give money to, can be multiple, separated by space.

            Distribute some money to multiple members. This will divide by the amount of players before distributing.
            For example, distributing $500 to 5 members will give everyone of them $100.

            Members that are mentioned multiple times will receive multiple payouts.

            In case of a decimal result the bot will round down, i.e. $7 distributed to 3 members will give everyone $2.

            Only guild leaders and officers can use this command."""
        )
        members = list(members)
        if ctx.me in members:
            members.remove(ctx.me)
        if not members:
            return await ctx.send(_("You can't distribute money to nobody."))

        # int() rounds down as to not go over the money limit
        # we need to update the amount after rounding down too to avoid losing money
        for_each = int(amount / len(members))
        amount = for_each * len(members)

        members_dupes = {i: members.count(i) for i in members}
        amounts = {for_each * i: [] for i in members_dupes.values()}
        for member in members_dupes.items():
            amounts[for_each * member[1]].append(member[0].id)
        # a bit ugly, but we get a dict {amount: [list of players]}

        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if guild["money"] < amount:
                return await ctx.send(_("Your guild is too poor."))

            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                amount,
                ctx.character_data["guild"],
            )
            await conn.executemany(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=ANY($2);',
                amounts.items(),
            )

        for member in members:
            await self.bot.cache.update_profile_cols_rel(member.id, money=for_each)

        nice_members = rpgtools.nice_join([str(member) for member in members])
        if guild["channel"]:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    guild["channel"],
                    f"**{ctx.author}** paid **${amount}** (${for_each} each) to"
                    f" **{nice_members}**",
                )
        await ctx.send(
            _(
                "Distributed **${money}** (${small_money} for each) to {members}."
            ).format(money=amount, small_money=for_each, members=nice_members)
        )

    @is_guild_leader()
    @guild.command(brief=_("Upgrade your guild bank"))
    @locale_doc
    async def upgrade(self, ctx):
        _(
            """Upgrade your guild's bank, adding space for $250,000 each time.

            Guilds can be upgraded 9 times which sets them to a maximum of $2,500,000.
            Patrons will be able to upgrade their guild further:
              - Silver donors can double their maximum bank space
              - Gold donors can quintuple (x5) their maximum bank space

            The price to upgrade the guild bank is always half of the maximum.

            Only guild leaders can use this command."""
        )
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            currentlimit = guild["banklimit"]
            newlimit = (guild["upgrade"] + 1) * 250000
            if guild["upgrade"] == 10:
                return await ctx.send(
                    _("Your guild already reached the maximum upgrade.")
                )
            if int(currentlimit / 2) > guild["money"]:
                return await ctx.send(
                    _(
                        "Your guild is too poor, you got **${money}** but it costs"
                        " **${price}** to upgrade."
                    ).format(money=guild["money"], price=int(currentlimit / 2))
                )

            if not await ctx.confirm(
                _(
                    "This will upgrade your guild bank limit to **${newlimit}** for"
                    " **${cost}**. Proceed?"
                ).format(newlimit=newlimit, cost=int(currentlimit / 2))
            ):
                return
            await conn.execute(
                'UPDATE guild SET "banklimit"=$1, "upgrade"="upgrade"+$2,'
                ' "money"="money"-$3 WHERE "id"=$4;',
                newlimit,
                1,
                int(currentlimit / 2),
                guild["id"],
            )
        if guild["channel"]:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    guild["channel"],
                    f"**{ctx.author}** upgraded the guild bank to **${newlimit}**",
                )
        await ctx.send(
            _("Your new guild bank limit is now **${limit}**.").format(limit=newlimit)
        )

    @is_guild_officer()
    @guild_cooldown(1800)
    @guild.command(brief=_("Battle another guild"))
    @locale_doc
    async def battle(
        self,
        ctx,
        enemy: MemberWithCharacter,
        amount: IntGreaterThan(-1),
        fightercount: IntGreaterThan(1),
    ):
        _(
            """`<enemy>` - A guild officer or leader
            `<amount>` - The amount of money to battle for, must be 0 or above
            `<fightercount>` - The amount of fighters to take into the battle

            Fight against another guild, the winning guild will be awarded one GvG win.

            While the battle is preparing, both players, you and the other player, will be asked to nominate guild members for the battle.
            You can do this by writing `battle nominate @person` (not including `{prefix}`) until you hit the fightercount.

            After the preparation is over, battles will be randomly matched between the two guilds.
            These battles function exactly the same as regular battles, see `{prefix}help battle` for more details.

            Each fight will give the guild who the winner is from one point. The guild with the most points in the end will win the guild battle.
            In case of a tie, nobody gets the money or guild win. The money will be taken from the guild bank.

            Only guild leaders and officers can use this command.
            (This command has a guild cooldown of 30 minutes.)"""
        )
        if enemy == ctx.author:
            return await ctx.send(_("Poor kiddo having no friendos."))
        guild1 = ctx.character_data["guild"]
        guild2 = ctx.user_data["guild"]
        if guild1 == 0 or guild2 == 0:
            return await ctx.send(_("One of you both doesn't have a guild."))
        if guild1 == guild2:
            return await ctx.send(
                _("Battling your own guild? :face_with_raised_eyebrow:")
            )
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
                'SELECT count("user") FROM profile WHERE "guild"=$1;', guild1["id"]
            )
            size2 = await conn.fetchval(
                'SELECT count("user") FROM profile WHERE "guild"=$1;', guild2["id"]
            )
        if size1 < fightercount or size2 < fightercount:
            return await ctx.send(_("One of the guilds is too small."))

        if not await ctx.confirm(
            f"{enemy.mention}, {ctx.author.mention} invites you to fight in a guild"
            " battle. React to join the battle. You got **1 Minute to accept**.",
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
                "{enemy} accepted the challenge by {author}. Please now nominate"
                " members, {author}. Use `battle nominate @user` to add someone to your"
                " team."
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
            guild = await self.bot.cache.get_profile_col(member.id, "guild")
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
                res = await self.bot.wait_for("message", timeout=90, check=simple1)
                try:
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
                except AttributeError:
                    await ctx.send(_("Error when adding this user, please try again"))
                continue
            except asyncio.TimeoutError:
                await self.bot.reset_guild_cooldown(ctx)
                return await ctx.send(
                    _("Took to long to add members. Fight cancelled.")
                )
        await ctx.send(
            _(
                "Please now nominate members, {enemy}. Use `battle nominate @user` to"
                " add someone to your team."
            ).format(enemy=enemy.mention)
        )
        while len(team2) != fightercount:
            try:
                res = await self.bot.wait_for("message", timeout=90, check=simple2)
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

        await self.bot.public_log(
            f"Guild **{guild1['name']}** challenges Guild **{guild2['name']}** to a"
            f" battle for a prize of **${amount}**.\n **{fightercount}** players"
            " entered."
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
                    "Guild Battle Fight **{num}** of **{total}**.\n**{user}** vs"
                    " **{user2}**!\nBattle running..."
                ).format(num=idx + 1, total=len(team1), user=user, user2=user2)
            )
            val1 = sum(await self.bot.get_damage_armor_for(user)) + random.randint(1, 7)
            val2 = sum(await self.bot.get_damage_armor_for(user2)) + random.randint(
                1, 7
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
                    "Winner of **{user}** vs **{user2}** is **{winner}**! Current"
                    " points: **{wins1}** to **{wins2}**."
                ).format(
                    user=user, user2=user2, winner=winner, wins1=wins1, wins2=wins2
                )
            )
        async with self.bot.pool.acquire() as conn:
            money1, bank1 = await conn.fetchval(
                'SELECT ("money", "banklimit") FROM guild WHERE "id"=$1;', guild1["id"]
            )
            money2, bank2 = await conn.fetchval(
                'SELECT ("money", "banklimit") FROM guild WHERE "id"=$1;', guild2["id"]
            )
            if money1 < amount or money2 < amount:
                return await ctx.send(_("Some guild spent the money??? Bad looser!"))
            if wins1 > wins2:
                if money1 + amount <= bank1:
                    await conn.execute(
                        'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2;',
                        amount,
                        guild1["id"],
                    )
                else:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                        amount,
                        ctx.author.id,
                    )
                    await self.bot.cache.update_profile_cols_rel(
                        ctx.author.id, money=amount
                    )
                await conn.execute(
                    'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                    amount,
                    guild2["id"],
                )
                await conn.execute(
                    'UPDATE guild SET "wins"="wins"+1 WHERE "id"=$1;', guild1["id"]
                )
                await ctx.send(
                    _("{guild} won the battle! Congratulations!").format(
                        guild=guild1["name"]
                    )
                )
                await self.bot.public_log(
                    f"**{guild1['name']}** won against **{guild2['name']}**."
                )
            elif wins2 > wins1:
                if money2 + amount <= bank2:
                    await conn.execute(
                        'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2;',
                        amount,
                        guild2["id"],
                    )
                else:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                        amount,
                        enemy.id,
                    )
                    await self.bot.cache.update_profile_cols_rel(
                        ctx.author.id, money=amount
                    )
                await conn.execute(
                    'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                    amount,
                    guild1["id"],
                )
                await conn.execute(
                    'UPDATE guild SET "wins"="wins"+1 WHERE "id"=$1;', guild2["id"]
                )
                await ctx.send(
                    _("{guild} won the battle! Congratulations!").format(
                        guild=guild2["name"]
                    )
                )
                await self.bot.public_log(
                    f"**{guild2['name']}** won against **{guild1['name']}**."
                )
            else:
                await ctx.send(_("It's a tie!"))
                await self.bot.public_log(
                    f"**{guild1['name']}** and **{guild2['name']}** tied."
                )

    @is_guild_officer()
    @guild_cooldown(3600)
    @guild.command(brief=_("Start a guild adventure"))
    @locale_doc
    async def adventure(self, ctx):
        _(
            """Start a guild adventure. Guild adventures can happen alongside regular adventures.

            On guild adventures, you can gain additional gold for your guild bank.
            When using this command, the bot will send a link used to join the adventure. Each member of the guild can join, at least 3 are required.
            Ten minutes after the link was sent, the users who joined will be gathered.

            The guild adventure's difficulty will depend solely on the users' levels, their equipped items and race/class bonuses are not considered.
            The adventure's lentgh depends on the difficulty, +1 difficulty means +30 minutes time.

            Only guild leaders and officers can use this command.
            (This command has a guild cooldown of 1 hour.)"""
        )
        if await self.bot.get_guild_adventure(ctx.character_data["guild"]):
            await self.bot.reset_guild_cooldown(ctx)
            return await ctx.send(
                _(
                    "Your guild is already on an adventure! Use `{prefix}guild status`"
                    " to view how long it still lasts."
                ).format(prefix=ctx.prefix)
            )
        guild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )

        id_ = await self.bot.start_joins()

        await ctx.send(
            _(
                "{author} seeks a guild adventure for **{guild}**! Follow the link to"
                " join! Unlimited players can join in the next 10 minutes. The minimum"
                " of players required is 3.\nPlease go to"
                " https://join.idlerpg.xyz/{id_} to join the guild adventure."
            ).format(author=ctx.author.mention, guild=guild["name"], id_=id_)
        )

        difficulty = int(rpgtools.xptolevel(ctx.character_data["xp"]))

        await asyncio.sleep(60 * 10)

        a_joined = await self.bot.get_joins(id_)
        joined = []

        async with self.bot.pool.acquire() as conn:
            for u in a_joined:
                user = await self.bot.cache.get_profile(u.id, conn=conn)
                if user and user["guild"] == guild["id"]:
                    difficulty += int(rpgtools.xptolevel(user["xp"]))
                    joined.append(u)

        if len(joined) < 3:
            await self.bot.reset_guild_cooldown(ctx)
            return await ctx.send(
                _("You didn't get enough other players for the guild adventure.")
            )

        time = timedelta(hours=difficulty * 0.5)

        await self.bot.start_guild_adventure(guild["id"], difficulty, time)

        if guild["channel"]:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self.bot.http.send_message(
                    guild["channel"],
                    f"Guild adventure with difficulty **{difficulty}**, lasting **{time}**,"
                    " started",
                )
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
                participants=", ".join([str(u) for u in joined]),
                difficulty=difficulty,
                time=time,
            )
        )

    @has_guild()
    @guild.command(brief=_("View your guild adventure's status"))
    @locale_doc
    async def status(self, ctx):
        _(
            """Check your guild adventure's status

            This will either display the time left or the reward. The reward can range from 20 times the difficulty up to 50 times the difficulty.
            Only guild leaders and officers can finish adventures, the status can be seen by every guild member."""
        )
        adventure = await self.bot.get_guild_adventure(ctx.character_data["guild"])

        if not adventure:
            return await ctx.send(
                _(
                    "Your guild isn't on an adventure yet. Ask your guild officer to"
                    " use `{prefix}guild adventure` to start one"
                ).format(prefix=ctx.prefix)
            )

        if adventure[2]:
            if ctx.character_data["guildrank"] in ["Leader", "Officer"]:
                await self.bot.delete_guild_adventure(ctx.character_data["guild"])
                gold = random.randint(adventure[0] * 20, adventure[0] * 50)

                channel = await self.bot.pool.fetchval(
                    'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2 RETURNING'
                    ' "channel";',
                    gold,
                    ctx.character_data["guild"],
                )
                if channel:
                    with suppress(discord.Forbidden, discord.HTTPException):
                        await self.bot.http.send_message(
                            channel,
                            f"**{ctx.author}** ended the guild adventure, reward was"
                            f" **${gold}**",
                        )
                await ctx.send(
                    _(
                        "Your guild has completed an adventure of difficulty"
                        " `{difficulty}` and **${gold}** has been added to the bank."
                    ).format(difficulty=adventure[0], gold=gold)
                )
            else:
                await ctx.send(
                    _(
                        "Your guild has completed an adventure of difficulty"
                        " `{difficulty}`, ask a guild officer to check their status."
                    ).format(difficulty=adventure[0])
                )
        else:
            await ctx.send(
                _(
                    "Your guild is currently in an adventure with difficulty"
                    " `{difficulty}`.\nTime remaining: `{remain}`"
                ).format(
                    difficulty=adventure[0], remain=str(adventure[1]).split(".")[0]
                )
            )

    @has_guild()
    @guild.command(
        aliases=["cooldowns", "t", "cds"], brief=_("Lists guild-specific cooldowns")
    )
    @locale_doc
    async def timers(self, ctx):
        _(
            """Lists guild-specific cooldowns, meaning all guild members have these cooldowns and cannot use the commands."""
        )
        cooldowns = await self.bot.redis.execute(
            "KEYS", f"guildcd:{ctx.character_data['guild']}:*"
        )
        adv = await self.bot.get_guild_adventure(ctx.character_data["guild"])
        if not cooldowns and (not adv or adv[2]):
            return await ctx.send(
                _("You don't have any active cooldown at the moment.")
            )
        timers = _("Commands on cooldown:")
        for key in cooldowns:
            key = key.decode()
            cooldown = await self.bot.redis.execute("TTL", key)
            cmd = key.replace(f"guildcd:{ctx.character_data['guild']}:", "")
            text = _("{cmd} is on cooldown and will be available after {time}").format(
                cmd=cmd, time=timedelta(seconds=int(cooldown))
            )
            timers = f"{timers}\n{text}"
        if adv and not adv[2]:
            text = _("Guild adventure is running and will be done after {time}").format(
                time=adv[1]
            )
            timers = f"{timers}\n{text}"
        await ctx.send(f"```{timers}```")

    '''
    @has_guild()
    @guild.command(brief=_("Show your progress in the ongoing event.")
    @locale_doc
    async def event(self, ctx):
        _(
            """Shows how many Pumpkins your guild currently has. Prizes can be claimed by the guild leader using `{prefix}guild claim <ID>`.
            Your guild can gain more pumpkins from guild adventures."""
        )
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
    @guild.command(brief=_("Claim an event reward"))
    @locale_doc
    async def claim(self, ctx, reward_id: IntFromTo(1, 10)):
        _(
            """`<reward_id>` - The reward's ID to claim, must be a number from 1 to 10.

            Claim an reward for your guild. These rewards can be money added to the guild bank, additional guild member slots or special guild badges.
            Rewards can be claimed multiple times. To see the full list of rewards, use `{prefix}guild event`.

            Only guild leaders can use this command."""
        )
        reward = [
            {"price": 1000, "reward": "money", "data": 5000},
            {"price": 5000, "reward": "money", "data": 27500},
            {"price": 10000, "reward": "money", "data": 60000},
            {"price": 25000, "reward": "money", "data": 175000},
            {
                "price": 37500,
                "reward": "badge",
                "data": "https://idlerpg.xyz/halloween_2019_1.png",
            },
            {
                "price": 50000,
                "reward": "badge",
                "data": "https://idlerpg.xyz/halloween_2019_2.png",
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
