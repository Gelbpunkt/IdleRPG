"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import asyncio
from utils import misc as rpgtools
import random
import secrets

from cogs.shard_communication import user_on_cooldown as user_cooldown
from discord.ext import commands
from utils.checks import has_char, has_money, is_patron, user_is_patron


async def genstats(bot, userid, damage, armor):
    async with bot.pool.acquire() as conn:
        uclass = await conn.fetchval(
            'SELECT class FROM profile WHERE "user"=$1;', userid
        )
    evolves1 = ["Mage", "Wizard", "Pyromancer", "Elementalist", "Dark Caster"]
    evolves3 = ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"]
    evolves4 = ["Novice", "Proficient", "Artisan", "Master", "Paragon"]
    if uclass in evolves1:
        return (damage + evolves1.index(uclass) + 1, armor)
    elif uclass in evolves3:
        return (damage, armor + evolves3.index(uclass) + 1)
    elif uclass in evolves4:
        return (damage + evolves4.index(uclass) + 1, armor + evolves4.index(uclass) + 1)
    else:
        return (damage, armor)


async def thiefgrade(bot, userid):
    async with bot.pool.acquire() as conn:
        uclass = await conn.fetchval(
            'SELECT class FROM profile WHERE "user"=$1;', userid
        )
    return ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"].index(uclass) + 1


async def petlevel(bot, userid):
    async with bot.pool.acquire() as conn:
        uclass = await conn.fetchval(
            'SELECT class FROM profile WHERE "user"=$1;', userid
        )
    return ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"].index(uclass) + 1


def is_thief():
    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            ret = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if not ret:
            return False
        else:
            return ret in ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"]

    return commands.check(predicate)


def is_ranger():
    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            ret = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if not ret:
            return False
        return ret in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]

    return commands.check(predicate)


class Classes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def genstats(self, userid, damage, armor):
        uclass = await self.bot.pool.fetchval(
            'SELECT class FROM profile WHERE "user"=$1;', userid
        )
        evolves1 = ["Wizard", "Pyromancer", "Elementalist", "Dark Caster"]
        evolves2 = ["Rogue", "Chunin", "Renegade", "Assassin"]
        evolves3 = ["Swordsman", "Knight", "Warlord", "Berserker"]
        evolves4 = ["Novice", "Proficient", "Artisan", "Master", "Paragon"]
        if uclass in evolves1:
            return (damage + evolves1.index(uclass) + 2, armor)
        elif uclass in evolves3:
            return (damage, armor + evolves2.index(uclass) + 2)
        elif uclass in evolves4:
            return (
                damage + evolves4.index(uclass) + 1,
                armor + evolves4.index(uclass) + 1,
            )
        elif uclass in evolves2:
            return (damage, armor)

    async def get_level(self, userid):
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchval('SELECT xp FROM profile WHERE "user"=$1;', userid)
        if not ret:
            return ret
        else:
            return rpgtools.xptolevel(ret)

    @has_char()
    @user_cooldown(86400)
    @commands.command(name="class", description="Change your class.")
    async def _class(self, ctx, profession: str):
        profession = profession.title()
        if profession not in ["Warrior", "Thief", "Mage", "Paragon", "Ranger"]:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(
                "Please align as a `Warrior`, `Mage`, `Thief`, `Ranger` or `Paragon` (Patreon Only)."
            )
        if profession == "Paragon" and not user_is_patron(self.bot, ctx.author):
            await self.bot.reset_cooldown(ctx)
            return await ctx.send("You have to be a donator to choose this class.")
        if profession == "Paragon":
            profession = "Novice"
        if profession == "Ranger":
            profession = "Caretaker"
        async with self.bot.pool.acquire() as conn:
            curclass = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if curclass == "No Class":
                await conn.execute(
                    'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                    profession,
                    ctx.author.id,
                )
                await ctx.send(f"Your new class is now `{profession}`.")
            else:
                if not await has_money(self.bot, ctx.author.id, 5000):
                    return await ctx.send(
                        f"You're too poor for a class change, it costs **$5000**."
                    )

                def check(m):
                    return m.content.lower() == "confirm" and m.author == ctx.author

                await ctx.send(
                    "Are you sure? Type `confirm` to change your class for **$5000**"
                )
                try:
                    await self.bot.wait_for("message", check=check, timeout=30)
                except asyncio.TimeoutError:
                    return await ctx.send("Class change cancelled.")
                await conn.execute(
                    'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                    profession,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    5000,
                    ctx.author.id,
                )
                await ctx.send(
                    f"Your new class is now `{profession}`. **$5000** was taken off your balance."
                )

    @has_char()
    @commands.command(description="Views your current class and benefits.")
    async def myclass(self, ctx):
        async with self.bot.pool.acquire() as conn:
            userclass = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if userclass == "No Class":
                await ctx.send("You haven't got a class yet.")
            else:
                try:
                    await ctx.send(
                        file=discord.File(
                            f"classes/{userclass.lower().replace(' ', '_')}.png"
                        )
                    )
                except FileNotFoundError:
                    await ctx.send(
                        f"The image for your class **{userclass}** hasn't been added yet."
                    )

    @has_char()
    @commands.command(description="Evolve to the next level of your class.")
    async def evolve(self, ctx):
        level = int(await self.get_level(ctx.author.id))
        evolves = {
            "Mage": ["Wizard", "Pyromancer", "Elementalist", "Dark Caster"],
            "Thief": ["Rogue", "Chunin", "Renegade", "Assassin"],
            "Warrior": ["Swordsman", "Knight", "Warlord", "Berserker"],
            "Paragon": ["Proficient", "Artisan", "Master", "Paragon"],
            "Ranger": ["Trainer", "Bowman", "Hunter", "Ranger"],
        }
        if level < 5:
            return await ctx.send("Your level isn't high enough to evolve.")
        if level >= 5:
            newindex = 0
        if level >= 10:
            newindex = 1
        if level >= 15:
            newindex = 2
        if level >= 20:
            newindex = 3
        async with self.bot.pool.acquire() as conn:
            curclass = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if curclass in ["Mage", "Wizard", "Pyromancer", "Elementalist", "Dark Caster"]:
            newclass = evolves["Mage"][newindex]
        elif curclass in ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"]:
            newclass = evolves["Thief"][newindex]
        elif curclass in ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"]:
            newclass = evolves["Warrior"][newindex]
        elif curclass in ["Novice", "Proficient", "Artisan", "Master", "Paragon"]:
            newclass = evolves["Paragon"][newindex]
        elif curclass in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
            newclass = evolves["Ranger"][newindex]
        else:
            return await ctx.send("You don't have a class yet.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                newclass,
                ctx.author.id,
            )
        await ctx.send(f"You are now a `{newclass}`.")

    @commands.command(description="Evolving tree.")
    async def tree(self, ctx):
        await ctx.send(
            """```
Level 0   |  Level 5    |  Level 10     | Level 15        |  Level 20
----------------------------------------------------------------------
Warriors ->  Swordsmen ->  Knights     -> Warlords       ->  Berserker
Thieves  ->  Rogues    ->  Chunin      -> Renegades      ->  Assassins
Mage     ->  Wizards   ->  Pyromancers -> Elementalists  ->  Dark Caster
Novice   ->  Proficient->  Artisan     -> Master         ->  Paragon
Caretaker->  Trainer   ->  Bowman      -> Hunter         ->  Ranger
```"""
        )

    @is_thief()
    @user_cooldown(3600)
    @commands.command(description="[Thief Only] Steal money!")
    async def steal(self, ctx):
        grade = await thiefgrade(self.bot, ctx.author.id)
        if secrets.randbelow(100) in range(1, grade * 8 + 1):
            async with self.bot.pool.acquire() as conn:
                usr = await conn.fetchrow(
                    'SELECT "user", "money" FROM profile WHERE "money">=0 ORDER BY RANDOM() LIMIT 1;'
                )
                stolen = int(usr["money"] * 0.1)
                await conn.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    stolen,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    stolen,
                    usr["user"],
                )
                user = await self.bot.get_user_global(usr["user"])
                await ctx.send(f"You stole **${stolen}** from **{user}**.")
        else:
            await ctx.send("Your attempt to steal money wasn't successful.")

    @is_ranger()
    @commands.command(description="[Ranger Only] View your pet!")
    async def pet(self, ctx):
        petlvl = await petlevel(self.bot, ctx.author.id)
        em = discord.Embed(title=f"{ctx.author.display_name}'s pet")
        em.add_field(name="Level", value=petlvl, inline=False)
        em.set_thumbnail(url=ctx.author.avatar_url)
        url = [
            "https://cdn.discordapp.com/attachments/456433263330852874/458568221189210122/fox.JPG",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568217770721280/bird_2.jpg",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568230110363649/hedgehog_2.JPG",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568231918108673/wolf_2.jpg",
            "https://cdn.discordapp.com/attachments/456433263330852874/458577751226581024/dragon_2.jpg",
        ][petlvl - 1]
        em.set_image(url=url)
        await ctx.send(embed=em)

    @is_ranger()
    @user_cooldown(86400)
    @commands.command(description="[Ranger Only] Let your pet get a weapon for you!")
    async def hunt(self, ctx):
        petlvl = await petlevel(self.bot, ctx.author.id)
        async with self.bot.pool.acquire() as conn:
            maximumstat = random.randint(1, petlvl * 6)
            shieldorsword = random.choice(["Sword", "Shield"])
            names = ["Broken", "Old", "Tattered", "Forgotten"]
            itemvalue = random.randint(1, 250)
            if shieldorsword == "Sword":
                itemname = random.choice(names) + random.choice(
                    [" Sword", " Blade", " Stich"]
                )
                item = await conn.fetchrow(
                    'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                    ctx.author.id,
                    itemname,
                    itemvalue,
                    "Sword",
                    maximumstat,
                    0.00,
                )
            elif shieldorsword == "Shield":
                itemname = random.choice(names) + random.choice(
                    [" Shield", " Defender", " Aegis"]
                )
                item = await conn.fetchrow(
                    'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                    ctx.author.id,
                    itemname,
                    itemvalue,
                    "Shield",
                    0.00,
                    maximumstat,
                )
            await conn.execute(
                'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                item[0],
                False,
            )
            embed = discord.Embed(
                title="You gained an item!",
                description="Your pet found an item!",
                color=0xFF0000,
            )
            embed.set_thumbnail(url=ctx.author.avatar_url)
            embed.add_field(name="ID", value=item[0], inline=False)
            embed.add_field(name="Name", value=itemname, inline=False)
            embed.add_field(name="Type", value=shieldorsword, inline=False)
            if shieldorsword == "Shield":
                embed.add_field(name="Armor", value=f"{maximumstat}.00", inline=True)
            else:
                embed.add_field(name="Damage", value=f"{maximumstat}.00", inline=True)
            embed.add_field(name="Value", value=f"${itemvalue}", inline=False)
            embed.set_footer(text=f"Your pet needs to recover, wait a day to retry")
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Classes(bot))
