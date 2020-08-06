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
import string

import discord

from discord.ext import commands

from classes.converters import MemberConverter
from utils import random
from utils.i18n import _, locale_doc


class SnowballFight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("assets/data/hangman.txt", "r") as f:
            self.words = f.readlines()

    @commands.command()
    @locale_doc
    async def snowballfight(self, ctx, enemy: MemberConverter):
        _("""Make a snowball fights against another guild.""")
        if enemy is ctx.author:
            return await ctx.send(_("You may not fight yourself."))

        msg = await ctx.send(
            _(
                "{enemy}, {author} has challenged you for an epic snowball fight! If"
                " you want to accept, react ⚔\n**IMPORTANT: This is very spammy, make"
                " sure you are using a dedicated channel!**"
            ).format(enemy=enemy.mention, author=ctx.author.mention)
        )

        def check(r, u):
            return (
                r.message.id == msg.id and u == enemy and str(r.emoji) == "\U00002744"
            )

        await msg.add_reaction("\U00002744")

        try:
            await self.bot.wait_for("reaction_add", check=check, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(_("Timed out..."))
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
            _(
                "{author}, type `snowballfight nominate @user` to add ten of your"
                " comrades to the fight. You need 10 total!"
            ).format(author=ctx.author.mention)
        )
        while len(team1) < 10:
            try:
                msg = await self.bot.wait_for("message", check=check1, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(_("Timed out..."))
            try:
                u = msg.mentions[0]
            except IndexError:
                continue
            if u in team1 or u in team1:
                await ctx.send(_("Taken!"))
            else:
                team1.append(u)
                await ctx.send(
                    _("{user} has been added to your team, {user2}.").format(
                        user=u.mention, user2=ctx.author.mention
                    )
                )
        await ctx.send(
            _(
                "{enemy}, use `snowballfight nominate @user` to add ten of your"
                " comrades to the fight. You need 10 total!"
            ).format(enemy=enemy.mention)
        )
        while len(team2) < 10:
            try:
                msg = await self.bot.wait_for("message", check=check2, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send(_("Timed out..."))
            try:
                u = msg.mentions[0]
            except IndexError:
                continue
            if u in team2 or u in team1:
                await ctx.send(_("Taken!"))
            else:
                team2.append(u)
                await ctx.send(
                    _("{user} has been added to your team, {user2}.").format(
                        user=u.mention, user2=enemy.mention
                    )
                )
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
                _(
                    """
{author.mention}'s team vs {enemy.mention}'s team
{t1} - {author}
{t2} - {enemy}
Next round starts in 5 seconds!
"""
                ).format(author=ctx.author, enemy=enemy, t1=t1, t2=t2)
            )
            await asyncio.sleep(5)
            game_mode = random.choice(["typeit", "maths", "hangman"])
            if game_mode == "typeit":
                w = random.sample(list(string.ascii_letters), 15)
                w.insert(random.randint(1, 14), "\u200b")
                word = "".join(w)
                real = word.replace("\u200b", "")

                def corr(msg):
                    return (
                        msg.author in team1 or msg.author in team2
                    ) and msg.content == real

                await ctx.send(
                    _(
                        "It's word typing time! In 3 seconds, I will send a word."
                        " Whoever types it fastest gets one point!"
                    )
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
                await ctx.send(
                    _("{author} got it right!").format(author=ctx.author.mention)
                )
            elif game_mode == "maths":
                m = random.randint(1, 10)
                x = random.randint(1, 10)
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
                    _(
                        "It's maths time! In 3 seconds, I'll send a simple maths task"
                        " to solve! Type the answer to get a point!"
                    )
                )
                await asyncio.sleep(3)
                await ctx.send(f"`({m} *\u200b {x}) \u200b/ {c} + \u200b{d}`")
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
                    _(
                        "It's hangman time! In 3 seconds, I'll send a hangman-style"
                        " word and you will have to either send your full word as the"
                        " guess or a letter to check for!"
                    )
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
                        await ctx.send(
                            _("{user} got it right!").format(user=msg.author)
                        )
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


def setup(bot):
    bot.add_cog(SnowballFight(bot))
