"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
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
    async def guild(self, ctx):
        """This command contains all guild-related commands."""
        guild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )
        if not guild:
            return await ctx.send("You are not in a guild yet.")
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
            return await ctx.send("No guild found.")

        membercount = await self.bot.pool.fetchval(
            'SELECT count(*) FROM profile WHERE "guild"=$1;', guild["id"]
        )

        embed = discord.Embed(title=guild["name"], description=guild["description"])
        embed.add_field(
            name="Current Member Count",
            value=f"{membercount}/{guild['memberlimit']} Members",
        )
        leader = await rpgtools.lookup(self.bot, guild["leader"])
        embed.add_field(name="Leader", value=f"{leader}")
        embed.add_field(
            name="Guild Bank",
            value=f"**${guild['money']}** / **${guild['banklimit']}**",
        )
        embed.set_thumbnail(url=guild["icon"])
        if guild["badge"]:
            embed.set_image(url=guild["badge"])
        try:
            await ctx.send(embed=embed)
        except discord.errors.HTTPException:
            await ctx.send(
                f"The guild icon seems to be a bad URL. Use `{ctx.prefix}guild icon` to fix this."
            )

    @guild.command()
    async def info(self, ctx, *, name: str):
        """Look up a guild by name."""
        await self.get_guild_info(ctx, name=name)

    @guild.command()
    async def ladder(self, ctx):
        """The best GvG guilds."""
        guilds = await self.bot.pool.fetch(
            "SELECT * FROM guild ORDER BY wins DESC LIMIT 10;"
        )
        result = ""
        for idx, guild in enumerate(guilds):
            leader = await rpgtools.lookup(self.bot, guild["leader"])
            result = f"{result}{idx + 1}. {guild['name']}, a guild by `{leader}` with **{guild['wins']}** GvG Wins\n"
        await ctx.send(
            embed=discord.Embed(
                title=f"The Best GvG Guilds", description=result, colour=0xE7CA01
            )
        )

    @has_guild()
    @guild.command()
    async def members(self, ctx):
        """List of your guild members."""
        members = await self.bot.pool.fetch(
            'SELECT "user", "guildrank" FROM profile WHERE "guild"=$1;',
            ctx.character_data["guild"],
        )
        members_fmt = []
        for m in members:
            u = str(
                await self.bot.get_user_global(m["user"])
                or f"Unknown User (ID {m['user']})"
            )
            members_fmt.append(f"{u} ({m['guildrank']})")
        await ctx.send(
            embed=discord.Embed(
                title="Your guild mates", description="\n".join(members_fmt)
            )
        )

    @has_char()
    @is_guild_leader()
    @guild.command()
    async def badge(self, ctx, number: IntGreaterThan(0)):
        """[Guild owner only] Change the guild badge."""
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                'SELECT badges FROM guild WHERE "leader"=$1;', ctx.author.id
            )
            if not bgs:
                return await ctx.send("Your guild has no badges yet.")
            try:
                bg = bgs[number - 1]
            except IndexError:
                return await ctx.send(
                    f"The badge number {number} is not valid, your guild only has {len(bgs)} available."
                )
            await conn.execute(
                'UPDATE guild SET badge=$1 WHERE "leader"=$2;', bg, ctx.author.id
            )
        await ctx.send("Badge updated!")

    @has_char()
    @has_no_guild()
    @user_cooldown(600)
    @guild.command()
    async def create(self, ctx):
        """Creates a guild."""

        def mycheck(amsg):
            return amsg.author == ctx.author

        await ctx.send("Enter a name for your guild. Maximum length is 20 characters.")
        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled guild creation.")
        name = name.content
        if len(name) > 20:
            return await ctx.send("Guild names musn't exceed 20 characters.")
        await ctx.send(
            "Send a link to the guild's icon. Maximum length is 60 characters."
        )
        try:
            url = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled guild creation.")
        url = url.content
        if len(url) > 60:
            return await ctx.send("URLs mustn't exceed 60 characters.")
        if await user_is_patron(self.bot, ctx.author):
            memberlimit = 100
        else:
            memberlimit = 50

        if not await ctx.confirm(
            "Are you sure? React to create a guild for **$10000**"
        ):
            return
        if not await has_money(self.bot, ctx.author.id, 10000):
            return await ctx.send(
                "A guild creation costs **$10000**, you are too poor."
            )
        async with self.bot.pool.acquire() as conn:
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
            f"Successfully added your guild **{name}** with a member limit of **{memberlimit}**."
        )

    @is_guild_leader()
    @guild.command()
    async def promote(self, ctx, member: MemberWithCharacter):
        """Promote someone to the rank of officer"""
        if member == ctx.author:
            return await ctx.send("Very funny...")
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send("Target is not a member of your guild.")
        if ctx.user_data["guildrank"] == "Officer":
            return await ctx.send("This user is already an officer of your guild.")
        await self.bot.pool.execute(
            'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Officer", member.id
        )
        await ctx.send(f"Done! {member} has been promoted to the rank of `Officer`.")

    @is_guild_leader()
    @guild.command()
    async def demote(self, ctx, member: MemberWithCharacter):
        """Demotes someone from the officer rank"""
        if member == ctx.author:
            return await ctx.send("Very funny...")
        if ctx.character_data["guild"] != ctx.user_data["guild"]:
            return await ctx.send("Target is not a member of your guild.")
        if ctx.user_data["guildrank"] != "Officer":
            return await ctx.send("This user can't be demoted any further.")
        await self.bot.pool.execute(
            'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Member", member.id
        )
        await ctx.send(f"Done! {member} has been demoted to the rank of `Member`.")

    @is_guild_officer()
    @guild.command()
    async def invite(self, ctx, newmember: MemberWithCharacter):
        """[Guild officer only] Invite someone to your guild."""
        if ctx.user_data["guild"]:
            return await ctx.send("That member already has a guild.")
        async with self.bot.pool.acquire() as conn:
            id = await conn.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
            )
            membercount = await conn.fetchval(
                'SELECT COUNT(*) FROM profile WHERE "guild"=$1;', id
            )
            limit, name = await conn.fetchval(
                'SELECT (memberlimit, name) FROM guild WHERE "id"=$1;', id
            )
        if membercount >= limit:
            return await ctx.send("Your guild is already at the maximum member count.")

        if not await ctx.confirm(
            f"{newmember.mention}, {ctx.author.mention} invites you to join **{name}**. React to join the guild.",
            user=newmember,
        ):
            return
        if await has_guild_(self.bot, newmember.id):
            return await ctx.send("That member already has a guild.")
        await self.bot.pool.execute(
            'UPDATE profile SET guild=$1 WHERE "user"=$2;', id, newmember.id
        )
        await ctx.send(f"{newmember.mention} is now a member of **{name}**. Welcome!")

    @has_guild()
    @is_no_guild_leader()
    @guild.command()
    async def leave(self, ctx):
        """Leave your current guild."""
        await self.bot.pool.execute(
            'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "user"=$3;',
            0,
            "Member",
            ctx.author.id,
        )
        await ctx.send(f"You left your guild.")

    @is_guild_officer()
    @guild.command()
    async def kick(self, ctx, member: Union[MemberWithCharacter, int]):
        """[Guild Officer only] Kick someone from your guild."""
        if hasattr(ctx, "user_data"):
            if ctx.user_data["guild"] != ctx.character_data["guild"]:
                return
            member = member.id
        else:
            if (
                await self.bot.pool.fetchval(
                    'SELECT guild FROM profile WHERE "user"=$1;', member
                )
                != ctx.character_data["guild"]
            ):
                return
        async with self.bot.pool.acquire() as conn:
            target_rank = await conn.fetchval(
                'SELECT guildrank FROM profile WHERE "user"=$1;', member
            )
            if target_rank != "Member":
                return await ctx.send("You can only kick members.")
            await conn.execute(
                'UPDATE profile SET "guild"=0, "guildrank"=$1 WHERE "user"=$2;',
                "Member",
                member,
            )
            await ctx.send("The person has been kicked!")

    @is_guild_leader()
    @guild.command()
    async def delete(self, ctx):
        """[Guild Owner only] Deletes the guild."""
        if not await ctx.confirm(
            "Are you sure to delete your guild? React to confirm the deletion."
        ):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute('DELETE FROM guild WHERE "leader"=$1;', ctx.author.id)
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "guild"=$3;',
                0,
                "Member",
                ctx.character_data["guild"],
            )
        await ctx.send("Successfully deleted your guild.")

    @is_guild_leader()
    @guild.command()
    async def icon(self, ctx, url: str):
        """[Guild Leader only] Changes the guild icon."""
        if len(url) > 60:
            return await ctx.send("URLs musn't exceed 60 characters.")
        if not (
            url.startswith("http")
            and (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg"))
        ):
            return await ctx.send(
                "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
            )
        await self.bot.pool.execute(
            'UPDATE guild SET "icon"=$1 WHERE "id"=$2;',
            url,
            ctx.character_data["guild"],
        )
        await ctx.send("Successfully updated the guild icon.")

    @is_guild_leader()
    @guild.command()
    async def description(self, ctx, *, text: str):
        """[Guild Owner only] Changes the guild description."""
        if len(text) > 200:
            return await ctx.send("The text may be up to 200 characters only.")
        await self.bot.pool.execute(
            'UPDATE guild SET "description"=$1 WHERE "leader"=$2;', text, ctx.author.id
        )
        await ctx.send("Updated!")

    @has_guild()
    @guild.command()
    async def richest(self, ctx):
        """Shows the richest players in your guild."""
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
            result = f"{result}{idx + 1}. {profile['name']}, a character by `{charname}` with **${profile['money']}**\n"
        await ctx.send(
            embed=discord.Embed(
                title=f"The Richest Players of {guild['name']}",
                description=result,
                colour=0xE7CA01,
            )
        )

    @has_guild()
    @guild.command(aliases=["high", "top"])
    async def best(self, ctx):
        """Shows the best players of your guild by XP."""
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
            result = f"{result}{idx + 1}. {profile['name']}, a character by `{charname}` with Level **{rpgtools.xptolevel(profile['xp'])}** (**{profile['xp']}** XP)\n"
        await ctx.send(
            embed=discord.Embed(
                title=f"The Best Players of {guild['name']}",
                description=result,
                colour=0xE7CA01,
            )
        )

    @has_guild()
    @guild.command()
    async def invest(self, ctx, amount: IntGreaterThan(0)):
        """Invest some of your money and put it to the guild bank."""
        if ctx.character_data["money"] < amount:
            return await ctx.send("You're too poor.")
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if g["banklimit"] < g["money"] + amount:
                return await ctx.send("The bank would be full.")
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
            f"Done! Now you have `${profile_money}` and the guild has `${guild_money}`."
        )

    @is_guild_officer()
    @guild.command()
    async def pay(self, ctx, amount: IntGreaterThan(0), member: MemberWithCharacter):
        """[Guild Officer only] Pay money from the guild bank to a user."""
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if guild["money"] < amount:
                return await ctx.send("Your guild is too poor.")
            await conn.execute(
                'UPDATE guild SET money=money-$1 WHERE "id"=$2;', amount, guild["id"]
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', amount, member.id
            )
        await ctx.send(
            f"Successfully gave **${amount}** from your guild bank to {member.mention}."
        )

    @is_guild_leader()
    @guild.command()
    async def upgrade(self, ctx):
        """Upgrades your guild bank's capacity."""
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            currentlimit = guild["banklimit"]
            level = int(currentlimit / 250_000)
            if level == 4:
                return await ctx.send("Your guild already reached the maximum upgrade.")
            if int(currentlimit / 2) > guild["money"]:
                return await ctx.send(
                    f"Your guild is too poor, you got **${guild['money']}** but it costs **${int(currentlimit/2)}** to upgrade."
                )
            await conn.execute(
                'UPDATE guild SET banklimit=banklimit+$1 WHERE "id"=$2;',
                250_000,
                guild["id"],
            )
            await conn.execute(
                'UPDATE guild SET money=money-$1 WHERE "id"=$2;',
                int(currentlimit / 2),
                guild["id"],
            )
        await ctx.send(f"Your new guild bank limit is now **${currentlimit+250000}**.")

    @is_guild_officer()
    @guild_cooldown(1800)
    @guild.command()
    async def battle(
        self,
        ctx,
        enemy: MemberWithCharacter,
        amount: IntGreaterThan(-1),
        fightercount: IntGreaterThan(1),
    ):
        """Battle against another guild."""
        if enemy == ctx.author:
            return await ctx.send("Poor kiddo having no friendos.")
        guild1 = ctx.character_data["guild"]
        guild2 = ctx.user_data["guild"]
        if guild1 == 0 or guild2 == 0:
            return await ctx.send("One of you both doesn't have a guild.")
        if (
            ctx.character_data["guildrank"] == "Member"
            or ctx.user_data["guildrank"] == "Member"
        ):
            return await ctx.send("One of you both isn't an officer of their guild.")
        async with self.bot.pool.acquire() as conn:
            guild1 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild1)
            guild2 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild2)
            if guild1["money"] < amount or guild2["money"] < amount:
                return await ctx.send("One of the guilds can't pay the price.")
            size1 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild1["id"]
            )
            size2 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild2["id"]
            )
        if size1 < fightercount or size2 < fightercount:
            return await ctx.send("One of the guilds is too small.")

        if not await ctx.confirm(
            f"{enemy.mention}, {ctx.author.mention} invites you to fight in a guild battle. React to join the battle. You got **1 Minute to accept**.",
            timeout=60,
            user=enemy,
        ):
            return await ctx.send(
                f"{enemy.mention} didn't want to join your battle, {ctx.author.mention}."
            )

        await ctx.send(
            f"{enemy.mention} accepted the challenge by {ctx.author.mention}. Please now nominate members, {ctx.author.mention}. Use `battle nominate @user` to add someone to your team."
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
                await ctx.send("That person isn't in your guild.")
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
                        f"{guild1check} has been added to your team, {ctx.author.mention}."
                    )
                else:
                    await ctx.send("User not found.")
                    continue
            except asyncio.TimeoutError:
                return await ctx.send("Took to long to add members. Fight cancelled.")
        await ctx.send(
            f"Please now nominate members, {enemy.mention}. Use `battle nominate @user` to add someone to your team."
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
                        f"{guild2check} has been added to your team, {enemy.mention}."
                    )
                else:
                    await ctx.send("User not found.")
                    continue
            except asyncio.TimeoutError:
                return await ctx.send("Took to long to add members. Fight cancelled.")

        msg = await ctx.send("Fight started!\nGenerating battles...")
        await asyncio.sleep(3)
        await msg.edit(content="Fight started!\nGenerating battles... Done.")
        wins1 = 0
        wins2 = 0
        for idx, user in enumerate(team1):
            user2 = team2[idx]
            msg = await ctx.send(
                f"Guild Battle Fight **{idx + 1}** of **{len(team1)}**.\n**{user.name}** vs **{user2.name}**!\nBattle running..."
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
                f"Winner of **{user}** vs **{user2}** is **{winner}**! Current points: **{wins1}** to **{wins2}**."
            )
        async with self.bot.pool.acquire() as conn:
            money1 = await conn.fetchval(
                'SELECT money FROM guild WHERE "id"=$1;', guild1["id"]
            )
            money2 = await conn.fetchval(
                'SELECT money FROM guild WHERE "id"=$1;', guild2["id"]
            )
            if money1 < amount or money2 < amount:
                return await ctx.send("Some guild spent the money??? Bad looser!")
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
                await ctx.send(f"{guild1['name']} won the battle! Congratulations!")
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
                await ctx.send(f"{guild2['name']} won the battle! Congratulations!")
            else:
                await ctx.send("It's a tie!")

    @is_guild_officer()
    @guild_cooldown(3600)
    @guild.command()
    async def adventure(self, ctx):
        """Starts a guild adventure."""
        if await self.bot.get_guild_adventure(ctx.character_data["guild"]):
            return await ctx.send(
                f"Your guild is already on an adventure! Use `{ctx.prefix}guild status` to view how long it still lasts."
            )
        guild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )

        msg = await ctx.send(
            f"{ctx.author.mention} seeks a guild adventure for **{guild['name']}**! React to join! Unlimited players can join in the next minute. The minimum of players required is 3."
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
                r, u = await self.bot.wait_for("reaction_add", check=apply, timeout=30)
                user = await self.bot.pool.fetchrow(
                    'SELECT guild, xp FROM profile WHERE "user"=$1;', u.id
                )
                await ctx.send(user)
                if user and user["guild"] == guild["id"]:
                    difficulty = += int(rpgtools.xptolevel(user["xp"])))
                    joined.append(u)
                    await ctx.send(f"Alright, {u.mention}, you have been added.")
                else:
                    await ctx.send("You aren't in their guild.")
            except asyncio.TimeoutError:
                if len(joined) < 3:
                    return await ctx.send(
                        "You didn't get enough other players for the guild adventure."
                    )
                started = True

        time = timedelta(hours=difficulty * 0.5)

        await self.bot.start_guild_adventure(guild["id"], difficulty, time)

        await ctx.send(
            f"""
Guild adventure for **{guild['name']}** started!
Participants:
{', '.join([m.mention for m in joined])}

Difficulty is **{difficulty}**
Time it will take: **{time}**
"""
        )

    @has_guild()
    @guild.command()
    async def status(self, ctx):
        """Views your guild adventure."""
        adventure = await self.bot.get_guild_adventure(ctx.character_data["guild"])

        if not adventure:
            return await ctx.send(
                f"Your guild isn't on an adventure yet. Ask your guild leader to use `{ctx.prefix}guild adventure` to start one"
            )

        if adventure[2]:
            await self.bot.delete_guild_adventure(ctx.character_data["guild"])
            gold = random.randint(adventure[0] * 20, adventure[0] * 50)

            await self.bot.pool.execute(
                'UPDATE guild SET money=money+$1 WHERE "id"=$2;',
                gold,
                ctx.character_data["guild"],
            )
            await ctx.send(
                f"Your guild has completed an adventure of difficulty `{adventure[0]}` and **${gold}** has been added to the bank."
            )
        else:
            await ctx.send(
                f"Your guild is currently in an adventure with difficulty `{adventure[0]}`.\nTime remaining: `{str(adventure[1]).split('.')[0]}`"
            )


def setup(bot):
    bot.add_cog(Guild(bot))
