"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import datetime
import random
import string

import discord
import ujson
from discord.ext import commands

from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, is_admin, is_guild_leader, is_guild_officer

rewards = {
    1: {"crates": 0, "puzzle": False, "money": 500},
    2: {"crates": 0, "puzzle": True, "money": 0},
    3: {"crates": 0, "puzzle": False, "money": 700},
    4: {"crates": 1, "puzzle": False, "money": 0},
    5: {"crates": 0, "puzzle": False, "money": 750},
    6: {"crates": 0, "puzzle": True, "money": 0},
    7: {"crates": 1, "puzzle": False, "money": 0},
    8: {"crates": 0, "puzzle": False, "money": 850},
    9: {"crates": 0, "puzzle": False, "money": 999},
    10: {"crates": 1, "puzzle": False, "money": 0},
    11: {"crates": 0, "puzzle": False, "money": 1000},
    12: {"crates": 0, "puzzle": False, "money": 1100},
    13: {"crates": 0, "puzzle": True, "money": 0},
    14: {"crates": 1, "puzzle": False, "money": 0},
    15: {"crates": 0, "puzzle": False, "money": 1250},
    16: {"crates": 0, "puzzle": False, "money": 1350},
    17: {"crates": 0, "puzzle": True, "money": 0},
    18: {"crates": 0, "puzzle": False, "money": 1499},
    19: {"crates": 1, "puzzle": False, "money": 0},
    20: {"crates": 0, "puzzle": True, "money": 0},
    21: {"crates": 1, "puzzle": False, "money": 0},
    22: {"crates": 0, "puzzle": False, "money": 1500},
    23: {"crates": 0, "puzzle": True, "money": 0},
    24: {"crates": 1, "puzzle": False, "money": 2000},
}


class Christmas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("assets/data/hangman.txt", "r") as f:
            self.words = f.readlines()

    @commands.group(invoke_without_command=True)
    async def calendar(self, ctx):
        _("""Look at your Winter Calendar""")
        today = datetime.datetime.now().day
        if today > 25 or today < 1:
            return await ctx.send(_("No calendar to show!"))
        await ctx.send(file=discord.File(f"assets/calendar/Day {today - 1}.png"))

    @has_char()
    @user_cooldown(86401)  # truly make sure they use it once a day
    @calendar.command(name="open")
    async def _open(self, ctx):
        _("""Open the Winter Calendar once every day.""")
        today = datetime.datetime.now().date()
        christmas_too_late = datetime.date(2018, 12, 25)
        first_dec = datetime.date(2018, 12, 1)
        if today >= christmas_too_late or today < first_dec:
            return await ctx.send(_("It's not calendar time yet..."))
        reward = rewards[today.day]
        reward_text = _("**You opened day {today}!**").format(today=today.day)
        async with self.bot.pool.acquire() as conn:
            if reward["puzzle"]:
                await conn.execute(
                    'UPDATE profile SET puzzles=puzzles+1 WHERE "user"=$1;',
                    ctx.author.id,
                )
                reward_text = f"{reward_text}\n- {_('A mysterious puzzle piece')}"
            if reward["crates"]:
                await conn.execute(
                    'UPDATE profile SET crates=crates+$1 WHERE "user"=$2;',
                    reward["crates"],
                    ctx.author.id,
                )
                reward_text = f"{reward_text}\n- {reward['crates']} {_('crates')}"
            if reward["money"]:
                await conn.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    reward["money"],
                    ctx.author.id,
                )
                reward_text = f"{reward_text}\n- ${reward['money']}"
            if today.day == 24:
                await conn.execute(
                    'UPDATE profile SET backgrounds=array_append(backgrounds, $1) WHERE "user"=$2;',
                    "https://i.imgur.com/HuF0VbN.png",
                    ctx.author.id,
                )
                reward_text = f"{reward_text}\n- {_('A special surprise - check out `{prefix}eventbackground` for a new Wintersday background!').format(prefix=ctx.prefix)}"
        await ctx.send(reward_text)

    @has_char()
    @commands.command()
    async def combine(self, ctx):
        _("""Combine the mysterious puzzle pieces.""")
        async with self.bot.pool.acquire() as conn:
            if (
                await conn.fetchval(
                    'SELECT puzzles FROM profile WHERE "user"=$1;', ctx.author.id
                )
                != 6
            ):
                return await ctx.send(
                    _("The mysterious puzzles don't fit together... Maybe some are missing?")
                )
            bg = random.choice(
                [
                    "https://i.imgur.com/PVYzp58.png",
                    "https://i.imgur.com/yjBS7Y9.png",
                    "https://i.imgur.com/gxMUpPm.png",
                    "https://i.imgur.com/DjzhuRe.png",
                    "https://i.imgur.com/l1ceMpq.png",
                    "https://i.imgur.com/OH9rAON.png",
                ]
            )
            await conn.execute(
                'UPDATE profile SET backgrounds=array_append(backgrounds, $1) WHERE "user"=$2;',
                bg,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET puzzles=0 WHERE "user"=$1;', ctx.author.id
            )
        await ctx.send(
            _("You combined the puzzles! In your head a voice whispers: *Well done. Now use `{prefix}eventbackground 1` to set your new background that you just acquired...*").format(prefix=ctx.prefix)
        )

    @is_guild_officer()
    @commands.command()
    async def snowballfight(self, ctx, enemy: discord.Member):
        _("""Make a snowball fights against another guild.""")
        if enemy is ctx.author:
            return await ctx.send(_("You may not fight yourself."))
        async with self.bot.pool.acquire() as conn:
            guild1, rank1 = await conn.fetchval(
                'SELECT (guild, guildrank) FROM profile WHERE "user"=$1;', ctx.author.id
            )
            guild2, rank2 = await conn.fetchval(
                'SELECT (guild, guildrank) FROM profile WHERE "user"=$1;', enemy.id
            )
            if rank2 == "Member":
                return await ctx.send(_("The enemy must be an officer or higher."))
            guild1 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild1)
            guild2 = await conn.fetchrow('SELECT * FROM guild WHERE "id"=$1;', guild2)
            guild1_members = [
                r["user"]
                for r in await conn.fetch(
                    'SELECT "user" FROM profile WHERE "guild"=$1;', guild1["id"]
                )
            ]
            guild2_members = [
                r["user"]
                for r in await conn.fetch(
                    'SELECT "user" FROM profile WHERE "guild"=$1;', guild2["id"]
                )
            ]

        msg = await ctx.send(
            _("{enemy}, {author} has challenged you for an epic snowball fight! If you want to accept, react \U00002744\n**IMPORTANT: This is very spammy, make sure you are using a dedicated channel!**").format(enemy=enemy.mention, author=ctx.author.mention)
        )

        def check(r, u):
            return r.message.id == msg.id and u == enemy and str(r.emoji) == "\U00002744"

        await msg.add_reaction("\U00002744")

        try:
            await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(_("Timed out..."))
        conv = commands.UserConverter()
        team1 = [ctx.author]
        team2 = [enemy]

        def check1(msg):
            return (
                msg.content.startswith("snowballfight nominate")
                and msg.author == ctx.author
            )

        def check2(msg):
            return (
                msg.content.startswith("snowballfight nominate") and msg.author == enemy
            )

        await ctx.send(
            _("{author}, type `snowballfight nominate @user` to add one of your guild members to the fight!").format(author=ctx.author.mention)
        )
        while len(team1) == 1:
            try:
                msg = await self.bot.wait_for("message", check=check1, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send(_("Timed out..."))
            try:
                u = await conv.convert(ctx, msg.content.split()[-1])
            except commands.BadArgument:
                continue
            if u.id not in guild1_members:
                await ctx.send(_("Not one of your guild members..."))
            elif u in team1:
                await ctx.send(_("That's you!"))
            else:
                team1.append(u)
        await ctx.send(
            _("{enemy}, use `snowballfight nominate @user` to add one of your guild members to the fight!").format(enemy=enemy.mention)
        )
        while len(team2) == 1:
            try:
                msg = await self.bot.wait_for("message", check=check2, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send(_("Timed out..."))
            try:
                u = await conv.convert(ctx, msg.content.split()[-1])
            except commands.BadArgument:
                continue
            if u.id not in guild2_members:
                await ctx.send(_("Not one of your guild members..."))
            elif u in team2:
                await ctx.send(_("That's you!"))
            else:
                team2.append(u)
        points1 = 1
        points2 = 1
        while points1 < 10 and points2 < 10:
            t1 = (
                ":black_large_square:" * (points1 - 1)
                + ":snowflake:"
                + ":black_large_square:" * (10 - points1)
            )
            t2 = (
                ":black_large_square:" * (points2 - 1)
                + ":snowflake:"
                + ":black_large_square:" * (10 - points2)
            )
            await ctx.send(
                _("""
{author.mention}'s team vs {enemy.mention}'s team
{t1} - {author}
{t2} - {enemy}
Next round starts in 5 seconds!
""").format(author=ctx.author, enemy=enemy, t1=t1, t2=t2)
            )
            await asyncio.sleep(5)
            game_mode = random.choice(["typeit", "maths", "hangman"])
            if game_mode == "typeit":
                w = random.sample(string.ascii_letters, 15)
                w.insert(random.randint(1, 14), "\u200b")
                word = "".join(w)
                real = word.replace("\u200b", "")

                def corr(msg):
                    return (
                        msg.author in team1 or msg.author in team2
                    ) and msg.content == real

                await ctx.send(
                    _("It's word typing time! In 3 seconds, I will send a word. Whoever types it fastest gets one point!")
                )
                await asyncio.sleep(3)
                await ctx.send(f"`{word}`")
                try:
                    msg = await self.bot.wait_for("message", check=corr, timeout=45)
                except asyncio.TimeoutError:
                    return await ctx.send(
                        _("Noone managed to get it right, I'll cancel the fight!")
                    )
                if msg.author in team1:
                    points1 += 1
                else:
                    points2 += 1
                await ctx.send(_("{author} got it right!").format(author=ctx.author.mention))
            elif game_mode == "maths":
                m = random.randint(1, 20)
                x = random.randint(1, 30)
                c = random.choice([2, 4, 5])
                d = random.randint(1, 100)
                res = (m * x) / c + d
                if int(res) == res:
                    res = str(int(res))
                else:
                    res = str(res)

                def corr(msg):
                    return (
                        msg.author in team1 or msg.author in team2
                    ) and msg.content == res

                await ctx.send(
                    _("It's maths time! In 3 seconds, I'll send a simple maths task to solve! Type the answer to get a point!")
                )
                await asyncio.sleep(3)
                await ctx.send(f"`({m} * {x}) / {c} + {d}`")
                try:
                    msg = await self.bot.wait_for("message", check=corr, timeout=45)
                except asyncio.TimeoutError:
                    return await ctx.send(
                        _("Noone managed to get it right, I'll cancel the fight!")
                    )
                if msg.author in team1:
                    points1 += 1
                else:
                    points2 += 1
                await ctx.send(_("{user} got it right!").format(user=msg.author))
            elif game_mode == "hangman":
                word = random.choice(self.words).strip()

                def corr(msg):
                    return (msg.author in team1 or msg.author in team2) and (
                        msg.content == word or len(msg.content) == 1
                    )

                disp = "_ " * len(word)
                guessed = []
                await ctx.send(
                    _("It's hangman time! In 3 seconds, I'll send a hangman-style word and you will have to either send your full word as the guess or a letter to check for!")
                )
                await asyncio.sleep(3)
                q = await ctx.send(f"`{disp}`")
                while True:
                    try:
                        msg = await self.bot.wait_for("message", check=corr, timeout=20)
                    except asyncio.TimeoutError:
                        return await ctx.send(
                            _("Noone participated, I'll cancel the fight!")
                        )
                    if msg.content == word:
                        if msg.author in team1:
                            points1 += 1
                        else:
                            points2 += 1
                        await ctx.send(_("{user} got it right!").format(user=msg.author))
                        break
                    else:
                        try:
                            await msg.delete()
                        except discord.Forbidden:
                            pass

                        if msg.content in guessed:
                            continue
                        if msg.content not in word:
                            continue
                        guessed.append(msg.content)
                        disp = " ".join([i if (i in guessed) else "_" for i in word])
                        await q.edit(content=f"`{disp}`")
        if points1 > points2:
            await ctx.send(_("Team 1 ({user}) won!").format(user=ctx.author.mention))
        else:
            await ctx.send(_("Team 2 ({user}) won!").format(user=enemy.mention))

    @is_guild_leader()
    @commands.command()
    async def signup(self, ctx):
        _("""Sign up for the snowball tournament.""")
        if datetime.datetime.now().day >= 6:
            return await ctx.send(_("Too late, my friend."))
        g = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "leader"=$1;', ctx.author.id
        )
        d = [g["id"], g["name"]]
        with open("tournament.json", "r+") as f:
            c = ujson.load(f)
            f.seek(0)
            if d in c["Participants"]:
                return await ctx.send("You're already signed up!")
            if len(c["Participants"]) > 64:
                return await ctx.send("Tournament is full!")
            c["Participants"].append(d)
            ujson.dump(c, f)
            f.truncate()
        await ctx.send(f"{g['name']} has been signed up.")

    @is_admin()
    @commands.command()
    async def makematches(self, ctx):
        """Makes the snowball tournament matches"""
        with open("tournament.json", "r+") as f:
            c = ujson.load(f)
            f.seek(0)
            d = c["Participants"]
            e = list(chunks(d, 2))
            c["Matches"] = e
            c["Participants"] = []
            ujson.dump(c, f)
            f.truncate()
        await ctx.send("Matches generated!")

    @is_admin()
    @commands.command()
    async def result(self, ctx, guild1name, guild2name, winnername):
        """Save a result of a match if it is in the tournament"""
        with open("tournament.json", "r+") as f:
            c = ujson.load(f)
            f.seek(0)
            for r in c["Matches"]:
                if (r[0][1] == guild1name or r[0][1] == guild2name) and (
                    r[1][1] == guild1name or r[1][1] == guild2name
                ):
                    the_r = r
                    c["Matches"].remove(the_r)
            try:
                if the_r[0][1] == winnername:
                    id = the_r[0][0]
                else:
                    id = the_r[1][0]
            except IndexError:
                return await ctx.send("Those guilds are not in a match!")
            c["Participants"].append([id, winnername])
            ujson.dump(c, f)
            f.truncate()
        await ctx.send(
            f"The winner of {guild1name} vs {guild2name} is now {winnername}!"
        )

    @is_admin()
    @commands.command()
    async def forceround(self, ctx):
        """Enforces a new snowball round."""
        with open("tournament.json", "r+") as f:
            c = ujson.load(f)
            f.seek(0)
            for r in c["Matches"]:
                c["Participants"].append(random.choice(r))
            c["Matches"] = list(chunks(c["Participants"], 2))
            ujson.dump(c, f)
            f.truncate()
        await ctx.send("Round forced!")

    @commands.command()
    async def matches(self, ctx):
        """Shows tournament matches."""
        with open("tournament.json", "r") as f:
            c = ujson.load(f)
        await ctx.send(
            f"**Participants who already are in the next round**:\n{', '.join([i[1] for i in c['Participants']])}"
        )
        paginator = commands.Paginator()
        try:
            for i in [f"{i[0][1]} vs {i[1][1]}" for i in c["Matches"]]:
                paginator.add_line(i)
        except IndexError:
            return await ctx.send(
                "No more matches to be done. Either it is over or it's time for a new round!"
            )
        await ctx.send(f"**Matches to be done**:")
        for i in paginator.pages:
            await ctx.send(i)


def setup(bot):
    bot.add_cog(Christmas(bot))
