import discord
import asyncio
import random

from typing import Union
from discord.ext import commands
from utils import misc as rpgtools
from utils.checks import (
    has_char,
    has_money,
    is_guild_officer,
    is_guild_leader,
    has_guild,
    has_no_guild,
    user_is_patron,
    is_member_of_author_guild,
    user_has_char,
    has_guild_,
    is_no_guild_leader,
)
from utils.tools import todelta
from cogs.shard_communication import user_on_cooldown as user_cooldown


class Guild:
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.group(
        invoke_without_command=True,
        description="A command containing various other ones. Try the help on this command.",
    )
    async def guild(self, ctx):
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT g.* FROM profile p JOIN guild g ON (p.guild=g.id) WHERE "user"=$1;',
                ctx.author.id,
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
        else:
            guild = False  # Technically impossible to happen but better to handle
        if not guild:
            return await ctx.send("No guild found.")
        membercount = await self.bot.pool.fetch(
            'SELECT * FROM profile WHERE "guild"=$1;', guild[0]
        )

        embed = discord.Embed(title=guild[1], description="Information about a guild.")
        embed.add_field(
            name="Current Member Count", value=f"{len(membercount)}/{guild[2]} Members"
        )
        leader = await rpgtools.lookup(self.bot, guild[3])
        embed.add_field(name="Leader", value=f"{leader}")
        embed.add_field(name="Guild Bank", value=f"**${guild[5]}** / **${guild[7]}**")
        embed.set_thumbnail(url=guild[4])
        if guild["badge"]:
            embed.set_image(url=guild["badge"])
        try:
            await ctx.send(embed=embed)
        except discord.errors.HTTPException:
            await ctx.send(
                f"The guild icon seems to be a bad URL. Use `{ctx.prefix}guild icon` to fix this."
            )

    @guild.command(description="Views a guild.", hidden=True)
    async def info(self, ctx, *, name: str):
        await self.get_guild_info(ctx, name=name)

    @guild.command(description="Guild GvG Ladder")
    async def ladder(self, ctx):
        ret = await self.bot.pool.fetch(
            "SELECT * FROM guild ORDER BY wins DESC LIMIT 10;"
        )
        result = ""
        for guild in ret:
            number = ret.index(guild) + 1
            leader = await rpgtools.lookup(self.bot, guild[3])
            result += f"{number}. {guild[1]}, a guild by `{leader}` with **{guild[6]}** GvG Wins and **${guild[5]}**\n"
        result = discord.Embed(
            title=f"The Best GvG Guilds", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @has_guild()
    @guild.command(description="A member list of your guild.")
    async def members(self, ctx):
        members = await self.bot.pool.fetch(
            'SELECT "user", "guildrank" FROM profile WHERE "guild"=(SELECT guild FROM profile WHERE "user"=$1);',
            ctx.author.id,
        )
        members = [
            f"{self.bot.get_user(m['user']) or 'Unknown User (ID '+str(m['user'])+')'} ({m['guildrank']})"
            for m in members
        ]
        embed = discord.Embed(title="Your guild mates", description="\n".join(members))
        await ctx.send(embed=embed)

    @has_char()
    @is_guild_leader()
    @guild.command(description="Change your guild badge.")
    async def badge(self, ctx, number: int):
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                'SELECT badges FROM guild WHERE "leader"=$1;', ctx.author.id
            )
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
    @guild.command(description="Creates a guild.")
    async def create(self, ctx):
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
        if user_is_patron(self.bot, ctx.author):
            memberlimit = 100
        else:
            memberlimit = 50

        def check(m):
            return m.content.lower() == "confirm" and m.author == ctx.author

        await ctx.send("Are you sure? Type `confirm` to create a guild for **$10000**")
        try:
            await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Guild creation cancelled.")
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
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "user"=$3;',
                guild["id"],
                "Leader",
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                10000,
                ctx.author.id,
            )
        await ctx.send(
            f"Successfully added your guild **{name}** with a member limit of **{memberlimit}**."
        )

    @is_guild_leader()
    @guild.command()
    async def promote(self, ctx, member: discord.Member):
        """Promote someone to the rank of officer"""
        if member == ctx.author:
            return await ctx.send("Very funny...")
        if not await is_member_of_author_guild(ctx, member.id):
            return await ctx.send("Target is not a member of your guild.")
        async with self.bot.pool.acquire() as conn:
            rank = await conn.fetchval(
                'SELECT guildrank FROM profile WHERE "user"=$1;', member.id
            )
            if rank == "Officer":
                return await ctx.send("This user is already an officer of your guild.")
            await conn.execute(
                'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Officer", member.id
            )
        await ctx.send(f"Done! {member} has been promoted to the rank of `Officer`.")

    @is_guild_leader()
    @guild.command()
    async def demote(self, ctx, member: discord.Member):
        """Demotes someone from the officer rank"""
        if member == ctx.author:
            return await ctx.send("Very funny...")
        if not await is_member_of_author_guild(ctx, member.id):
            return await ctx.send("Target is not a member of your guild.")
        async with self.bot.pool.acquire() as conn:
            if (
                await conn.fetchval(
                    'SELECT guildrank FROM profile WHERE "user"=$1;', member.id
                )
                != "Officer"
            ):
                return await ctx.send("This user can't be demoted any further.")
            await conn.execute(
                'UPDATE profile SET guildrank=$1 WHERE "user"=$2;', "Member", member.id
            )
        await ctx.send(f"Done! {member} has been demoted to the rank of `Member`.")

    @is_guild_officer()
    @guild.command(description="Invite someone to your guild.")
    async def invite(self, ctx, newmember: discord.Member):
        if not await user_has_char(self.bot, newmember.id):
            return await ctx.send("That member has not got a character.")
        if await has_guild_(self.bot, newmember.id):
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

        def mycheck(amsg):
            return amsg.author == newmember and amsg.content.lower() == "invite accept"

        await ctx.send(
            f"{newmember.mention}, {ctx.author.mention} invites you to join **{name}**. Type `invite accept` to join the guild."
        )
        try:
            await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send(
                f"{newmember.mention} didn't want to join your guild, {ctx.author.mention}."
            )
        if await has_guild_(self.bot, newmember.id):
            return await ctx.send("That member already has a guild.")
        await self.bot.pool.execute(
            'UPDATE profile SET guild=$1 WHERE "user"=$2;', id, newmember.id
        )
        await ctx.send(f"{newmember.mention} is now a member of **{name}**. Welcome!")

    @has_guild()
    @is_no_guild_leader()
    @guild.command(description="Leave your current guild.")
    async def leave(self, ctx):
        guild = await self.bot.pool.fetchval(
            'SELECT name FROM guild WHERE "id"=(SELECT guild FROM profile WHERE "user"=$1)',
            ctx.author.id,
        )
        await self.bot.pool.execute(
            'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "user"=$3;',
            0,
            "Member",
            ctx.author.id,
        )
        await ctx.send(f"You left **{guild}**.")

    @is_guild_officer()
    @guild.command(description="Kick someone out of your guild.")
    async def kick(self, ctx, member: Union[discord.User, int]):
        if isinstance(member, discord.User):
            username = str(member)
            member = member.id
        else:
            username = str(await self.bot.get_user_info(member))
        if not await is_member_of_author_guild(ctx, member):
            return await ctx.send("Target is not a member of your guild.")
        async with self.bot.pool.acquire() as conn:
            rank = await conn.fetchval(
                'SELECT guildrank FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if rank not in ["Officer", "Leader"]:
                return await ctx.send(
                    "You have to be a guild officer or leader to do this action!"
                )
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
            await ctx.send(f"**{username or 'Unknown user'}** has been kicked!")

    @is_guild_leader()
    @guild.command(description="Deletes your guild.")
    async def delete(self, ctx):
        def mycheck(amsg):
            return (
                amsg.author == ctx.author
                and amsg.content.lower() == "guild deletion confirm"
            )

        await ctx.send(
            "Are you sure to delete your guild? Type `guild deletion confirm` to confirm the deletion."
        )
        try:
            await self.bot.wait_for("message", timeout=15, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled guild deletion.")
        async with self.bot.pool.acquire() as conn:
            guild_id = await conn.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1', ctx.author.id
            )
            await conn.execute('DELETE FROM guild WHERE "leader"=$1;', ctx.author.id)
            await conn.execute(
                'UPDATE profile SET "guild"=$1, "guildrank"=$2 WHERE "guild"=$3;',
                0,
                "Member",
                guild_id,
            )
        await ctx.send("Successfully deleted your guild.")

    @is_guild_leader()
    @guild.command(description="Changes your guild icon.")
    async def icon(self, ctx, url: str):
        if len(url) > 60:
            return await ctx.send("URLs musn't exceed 60 characters.")
        if url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            url = url
        else:
            return await ctx.send(
                "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
            )
        await self.bot.pool.execute(
            'UPDATE guild SET "icon"=$1 WHERE "id"=(SELECT guild FROM profile WHERE "user"=$2);',
            url,
            ctx.author.id,
        )
        await ctx.send("Successfully updated the guild icon.")

    @has_guild()
    @guild.command(description="Shows the richest players in your guild. Maximum 10.")
    async def richest(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT g.* FROM guild g JOIN profile p ON (g.id=p.guild) WHERE p."user"=$1;',
                ctx.author.id,
            )
            ret = await conn.fetch(
                'SELECT "user", "name", "money" from profile WHERE "guild"=$1 ORDER BY "money" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            charname = await rpgtools.lookup(self.bot, profile[0])
            result = f"{result}{number}. {profile[1]}, a character by `{charname}` with **${profile[2]}**\n"
        result = discord.Embed(
            title=f"The Richest Players of {guild['name']}",
            description=result,
            colour=0xE7CA01,
        )
        await ctx.send(embed=result)

    @has_guild()
    @guild.command(
        description="Shows the best players by XP in your guild. Maximum 10.",
        aliases=["high", "top"],
    )
    async def best(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                "SELECT g.* FROM guild g JOIN profile p ON (p.guild=g.id) WHERE p.user=$1;",
                ctx.author.id,
            )
            ret = await conn.fetch(
                'SELECT "user", "name", "xp" from profile WHERE "guild"=$1 ORDER BY "xp" DESC LIMIT 10;',
                guild["id"],
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            charname = await rpgtools.lookup(self.bot, profile[0])
            result = f"{result}{number}. {profile[1]}, a character by `{charname}` with Level **{rpgtools.xptolevel(profile[2])}** (**{profile[2]}** XP)\n"
        result = discord.Embed(
            title=f"The Best Players of {guild['name']}",
            description=result,
            colour=0xE7CA01,
        )
        await ctx.send(embed=result)

    @has_guild()
    @guild.command(description="Pay money to your guild's bank.")
    async def invest(self, ctx, amount: int):
        if amount < 0:
            return await ctx.send("Negative money cannot be invested.")
        if not await has_money(self.bot, ctx.author.id, amount):
            return await ctx.send("You don't have enough money to do that!")
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchrow(
                'SELECT g.* FROM guild g JOIN profile p ON (g.id=p.guild) WHERE p."user"=$1;',
                ctx.author.id,
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
    @guild.command(description="Pay money to a guild member.")
    async def pay(self, ctx, amount: int, member: discord.Member):
        if amount < 0:
            return await ctx.send("Don't scam!")
        if not await user_has_char(self.bot, member.id):
            return await ctx.send("That user doesn't have a character.")
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT g.* FROM guild g JOIN profile p ON (g.id=p.guild) WHERE p."user"=$1;',
                ctx.author.id,
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
    @guild.command(description="Upgrade your guild bank.")
    async def upgrade(self, ctx):
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM guild WHERE "id"=(SELECT guild FROM profile WHERE "user"=$1);',
                ctx.author.id,
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

    @has_char()
    @guild.command(description="Battle against another guild.")
    async def battle(self, ctx, enemy: discord.Member, amount: int, fightercount: int):
        if amount < 0:
            return await ctx.send("Don't scam!")
        if enemy is ctx.author:
            return await ctx.send("Poor kiddo having no friendos.")
        async with self.bot.pool.acquire() as conn:
            guild1, rank1 = await conn.fetchval(
                'SELECT (guild, guildrank) FROM profile WHERE "user"=$1;', ctx.author.id
            )
            guild2, rank2 = await conn.fetchval(
                'SELECT (guild, guildrank) FROM profile WHERE "user"=$1;', enemy.id
            )

            if guild1 == 0 or guild2 == 0:
                return await ctx.send("One of you both doesn't have a guild.")
            guild1 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild1)
            guild2 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild2)
            if rank1 == "Member" or rank2 == "Member":
                return await ctx.send(
                    "One of you both isn't an officer of their guild."
                )
            if guild1[5] < amount or guild2[5] < amount:
                return await ctx.send("One of the guilds can't pay the price.")
            size1 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild1[0]
            )
            size2 = await conn.fetchval(
                'SELECT count(user) FROM profile WHERE "guild"=$1;', guild2[0]
            )
            if size1 < fightercount or size2 < fightercount:
                return await ctx.send("One of the guilds is too small.")

        def msgcheck(amsg):
            return (
                amsg.author == enemy and amsg.content.lower() == "guild battle accept"
            )

        await ctx.send(
            f"{enemy.mention}, {ctx.author.mention} invites you to fight in a guild battle. Type `guild battle accept` to join the battle. You got **1 Minute to accept**."
        )
        try:
            res = await self.bot.wait_for("message", timeout=60, check=msgcheck)
        except asyncio.TimeoutError:
            return await ctx.send(
                f"{enemy.mention} didn't want to join your battle, {ctx.author.mention}."
            )
        await ctx.send(
            f"{enemy.mention} accepted the challenge by {ctx.author.mention}. Please now nominate members, {ctx.author.mention}. Use `battle nominate @user` to add someone to your team."
        )
        team1 = []
        team2 = []
        converter = commands.UserConverter()

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
        for user in team1:
            user2 = team2[team1.index(user)]
            msg = await ctx.send(
                f"Guild Battle Fight **{team1.index(user)+1}** of **{len(team1)}**.\n**{user.name}** vs **{user2.name}**!\nBattle running..."
            )
            async with self.bot.pool.acquire() as conn:
                sw1 = (
                    await conn.fetchval(
                        "SELECT ai.damage FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                        user.id,
                    )
                    or 0
                )
                sh1 = (
                    await conn.fetchval(
                        "SELECT ai.armor FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                        user.id,
                    )
                    or 0
                )
                sw2 = (
                    await conn.fetchval(
                        "SELECT ai.damage FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                        user2.id,
                    )
                    or 0
                )
                sh2 = (
                    await conn.fetchval(
                        "SELECT ai.armor FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                        user2.id,
                    )
                    or 0
                )
            val1 = sw1 + sh1 + random.randint(1, 7)
            val2 = sw2 + sh2 + random.randint(1, 7)
            if val1 > val2:
                winner = user
                wins1 += 1
            elif val2 > val1:
                winner = user2
                wins2 += 1
            else:
                winner = random.choice(user, user2)
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
    @user_cooldown(3600)
    @guild.command(description="Starts a guild adventure.")
    async def adventure(self, ctx):
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchrow(
                'SELECT * FROM profile p JOIN guild g ON (p.guild=g.id) WHERE p."user"=$1;',
                ctx.author.id,
            )
            check = await conn.fetchrow(
                'SELECT * FROM guildadventure WHERE "guildid"=$1;', guild["id"]
            )
            if check:
                return await ctx.send(
                    f"Your guild is already on an adventure! Use `{ctx.prefix}guild status` to view how long it still lasts."
                )

        await ctx.send(
            f"{ctx.author.mention} seeks a guild adventure for **{guild['name']}**! Write `guild adventure join` to join them! Unlimited players can join in the next 30 seconds. The minimum of players required is 3."
        )

        joined = [ctx.author]
        difficulty = int(rpgtools.xptolevel(guild[3]))
        started = False

        async def is_in_guild(userid, difficulty):
            user = await self.bot.pool.fetchrow(
                'SELECT guild, xp FROM profile WHERE "user"=$1;', userid
            )
            if user[0] == guild["id"]:
                difficulty += int(rpgtools.xptolevel(user[1]))
                return difficulty
            return False

        def apply(msg):
            return (
                msg.content.lower() == "guild adventure join"
                and msg.channel == ctx.channel
                and not msg.author.bot
                and msg.author not in joined
            )

        while not started:
            try:
                msg = await self.bot.wait_for("message", check=apply, timeout=30)
                test = await is_in_guild(msg.author.id, difficulty)
                if test:
                    difficulty = test
                    joined.append(msg.author)
                    await ctx.send(
                        f"Alright, {msg.author.mention}, you have been added."
                    )
                else:
                    await ctx.send("You aren't in their guild.")
            except asyncio.TimeoutError:
                if len(joined) < 3:
                    return await ctx.send(
                        "You didn't get enough other players for the guild adventure."
                    )
                started = True

        time = str(difficulty * 0.5) + "h"

        await ctx.send(
            f"""
Guild adventure for **{guild['name']}** started!
Participants:
{', '.join([m.mention for m in joined])}

Difficulty is **{difficulty}**
Time it will take: **{time}**
"""
        )

        async with self.bot.pool.acquire() as conn:
            enddate = await conn.fetchval(
                "SELECT clock_timestamp() + $1::interval;", todelta(time)
            )
            await conn.execute(
                'INSERT INTO guildadventure ("guildid", "end", "difficulty") VALUES ($1, $2, $3);',
                guild["id"],
                enddate,
                difficulty,
            )

    @has_char()
    @guild.command(description="Views your guild adventure status.")
    async def status(self, ctx):
        async with self.bot.pool.acquire() as conn:
            guild = await conn.fetchval(
                'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if guild == 0:
                return await ctx.send("You didn't join a guild yet.")
            adventure = await conn.fetchrow(
                'SELECT * FROM guildadventure WHERE "guildid"=$1;', guild
            )

            if not adventure:
                return await ctx.send(
                    f"Your guild isn't on an adventure yet. Ask your guild leader to use `{ctx.prefix}guild adventure` to start one"
                )

            finished = await conn.fetchrow(
                'SELECT * FROM guildadventure WHERE "guildid"=$1 AND "end" < clock_timestamp();',
                guild,
            )

            if finished:
                gold = random.randint(adventure[2] * 20, adventure[2] * 50)
                await conn.execute(
                    'DELETE FROM guildadventure WHERE "guildid"=$1;', guild
                )
                await conn.execute(
                    'UPDATE guild SET money=money+$1 WHERE "id"=$2;', gold, guild
                )
                await ctx.send(
                    f"Your guild has completed an adventure of difficulty `{adventure[2]}` and **${gold}** has been added to the bank."
                )
            else:
                remain = await conn.fetchval(
                    "SELECT $1-clock_timestamp();", adventure[1]
                )
                await ctx.send(
                    f"Your guild is currently in an adventure with difficulty `{adventure[2]}`.\nTime remaining: `{str(remain).split('.')[0]}`"
                )


def setup(bot):
    bot.add_cog(Guild(bot))
