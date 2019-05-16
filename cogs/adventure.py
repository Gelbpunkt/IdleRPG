"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import functools
import random

import discord
from discord.ext import commands

from classes.converters import IntFromTo
from cogs.classes import genstats
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char, has_no_adventure
from utils.tools import todelta


class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(aliases=["missions", "dungeons"])
    async def adventures(self, ctx):
        """A list of all adventures with success rates, name and time it takes."""
        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        all_dungeons = await self.bot.pool.fetch(
            'SELECT difficulty FROM dungeon ORDER BY "id";'
        )  # TODO: This table can be hardcoded
        level = rpgtools.xptolevel(ctx.character_data["xp"])
        damage = sword["damage"] if sword else 0
        defense = shield["armor"] if shield else 0

        msg = await ctx.send("Loading images...")

        chances = []
        for row in all_dungeons:
            success = rpgtools.calcchance(
                damage, defense, row["difficulty"], int(level), returnsuccess=False
            )
            chances.append((success[0] - success[2], success[1] + success[2]))
        thing = functools.partial(rpgtools.makeadventures, chances)
        images = await self.bot.loop.run_in_executor(None, thing)

        await msg.delete()

        files = [
            discord.File(img, filename=f"Adventure{idx + 1}.png")
            for idx, img in enumerate(images)
        ]
        pages = [
            discord.Embed().set_image(url=f"attachment://Adventure{idx + 1}.png")
            for idx in range(len(images))
        ]

        await self.bot.paginator.AdventurePaginator(embeds=pages, files=files).paginate(
            ctx
        )

    @has_no_adventure()
    @commands.command(aliases=["mission", "a", "dungeon"])
    async def adventure(self, ctx, dungeonnumber: IntFromTo(1, 20)):
        """Sends your character on an adventure."""
        async with self.bot.pool.acquire() as conn:
            boostertest = await conn.fetchval(
                'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2;',
                ctx.author.id,
                1,
            )
            boostertest2 = await conn.fetchval(
                'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2 AND clock_timestamp() < "end";',
                ctx.author.id,
                1,
            )
            if not boostertest and not boostertest2:
                end = await conn.fetchval(
                    "SELECT clock_timestamp() + $1::interval;",
                    todelta(times[dungeonnumber]),
                )
            elif boostertest and not boostertest2:
                await conn.execute(
                    'DELETE FROM boosters WHERE "user"=$1 AND "type"=$2;',
                    ctx.author.id,
                    1,
                )
                end = await conn.fetchval(
                    "SELECT clock_timestamp() + $1::interval;",
                    todelta(times[dungeonnumber]),
                )
            elif boostertest and boostertest2:
                end = await conn.fetchval(
                    "SELECT clock_timestamp() + $1::interval;",
                    todelta(booster_times[dungeonnumber]),
                )
            await conn.execute(
                'INSERT INTO mission ("name", "end", "dungeon") VALUES ($1, $2, $3);',
                ctx.author.id,
                end,
                dungeonnumber,
            )
            await ctx.send(
                f"Successfully sent your character out on an adventure. Use `{ctx.prefix}status` to see the current status of the mission."
            )

    @has_no_adventure()
    @user_cooldown(3600)
    @commands.command()
    async def activeadventure(self, ctx):
        """Go out on an active, action based adventure."""
        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        SWORD = sword["damage"] if sword else 0
        SHIELD = shield["armor"] if shield else 0
        # class test
        SWORD, SHIELD = await genstats(
            self.bot, ctx.author.id, float(SWORD), float(SHIELD)
        )
        HP = 100
        PROGRESS = 0  # percent

        def is_valid_move(msg):
            return (
                msg.content.lower() in ["attack", "defend", "recover"]
                and msg.author == ctx.author
            )

        ENEMY_HP = 100

        while PROGRESS < 100 and HP > 0:
            await ctx.send(
                f"""
**{ctx.author.display_name}'s Adventure**
```
Progress: {PROGRESS}%
HP......: {HP}

Enemy
HP......: {ENEMY_HP}

Use attack, defend or recover
```
""",
                delete_after=10,
            )
            try:
                res = await self.bot.wait_for(
                    "message", timeout=30, check=is_valid_move
                )
            except asyncio.TimeoutError:
                return await ctx.send("Adventure stopped because you refused to move.")
            move = res.content.lower()
            enemymove = random.choice(["attack", "defend", "recover"])
            if move == "recover":
                HP += 20
                await ctx.send("You healed yourself for 20 HP.", delete_after=10)
            if enemymove == "recover":
                ENEMY_HP += 20
                await ctx.send(f"The enemy healed himself for 20 HP.", delete_after=10)
            if move == "attack" and enemymove == "defend":
                await ctx.send("Your attack was blocked!", delete_after=10)
            if move == "defend" and enemymove == "attack":
                await ctx.send("Enemy attack was blocked!", delete_after=10)
            if move == "defend" and enemymove == "defend":
                await ctx.send("Noone attacked.")
            if move == "attack" and enemymove == "attack":
                efficiency = random.randint(int(SWORD * 0.5), int(SWORD * 1.5))
                HP -= efficiency
                ENEMY_HP -= SWORD
                await ctx.send(
                    f"You hit the enemy for **{SWORD}** damage, he hit you for **{efficiency}** damage.",
                    delete_after=10,
                )
            elif move == "attack" and enemymove != "defend":
                ENEMY_HP -= SWORD
                await ctx.send(
                    f"You hit the enemy for **{SWORD}** damage.", delete_after=10
                )
            elif enemymove == "attack" and move == "recover":
                efficiency = random.randint(int(SWORD * 0.5), int(SWORD * 1.5))
                HP -= efficiency
                await ctx.send(
                    f"The enemy hit you for **{efficiency}** damage.", delete_after=10
                )
            if ENEMY_HP < 1:
                await ctx.send("Enemy defeated! You gained **20 HP**", delete_after=10)
                PROGRESS += random.randint(10, 40)
                ENEMY_HP = 100
                HP += 20

        if HP < 1:
            return await ctx.send("You died.")

        if SWORD < 26:
            maximumstat = random.randint(1, SWORD + 5)
        else:
            maximumstat = random.randint(1, 30)
        shieldorsword = random.choice(["Sword", "Shield"])
        names = ["Rare", "Ancient", "Normal", "Legendary", "Famous"]
        itemvalue = random.randint(1, 250)
        async with self.bot.pool.acquire() as conn:
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
            description="You found a new item when finishing an active adventure!",
            color=0xFF0000,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name="ID", value=item[0], inline=False)
        embed.add_field(name="Name", value=itemname, inline=False)
        embed.add_field(name="Type", value=shieldorsword, inline=False)
        if shieldorsword == "Shield":
            embed.add_field(name="Damage", value="0.00", inline=True)
            embed.add_field(name="Armor", value=f"{maximumstat}.00", inline=True)
        else:
            embed.add_field(name="Damage", value=f"{maximumstat}.00", inline=True)
            embed.add_field(name="Armor", value="0.00", inline=True)
        embed.add_field(name="Value", value=f"${itemvalue}", inline=False)
        embed.set_footer(text=f"Your HP were {HP}")
        await ctx.send(embed=embed)

    @has_char()
    @commands.command(aliases=["s"])
    async def status(self, ctx):
        """Checks your adventure status."""
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
            )
            if not ret:
                return await ctx.send(
                    f"You are on no mission yet. Use `{ctx.prefix}adventure [DungeonID]` to go out on an adventure!"
                )
            isfinished = await conn.fetchrow(
                'SELECT * FROM mission WHERE name=$1 AND clock_timestamp() > "end";',
                ctx.author.id,
            )
            if isfinished:
                sword = await conn.fetchrow(
                    "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                    ctx.author.id,
                )
                shield = await conn.fetchrow(
                    "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                    ctx.author.id,
                )
                playerxp = await conn.fetchval(
                    'SELECT xp FROM profile WHERE "user"=$1;', ctx.author.id
                )
                playerlevel = rpgtools.xptolevel(playerxp)

                swordbonus = sword["damage"] if sword else 0
                shieldbonus = shield["armor"] if shield else 0

                # class test
                swordbonus, shieldbonus = await genstats(
                    self.bot, ctx.author.id, swordbonus, shieldbonus
                )

                boostertest = await conn.fetchval(
                    'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2;',
                    ctx.author.id,
                    2,
                )
                boostertest2 = await conn.fetchval(
                    'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2 AND clock_timestamp() < "end";',
                    ctx.author.id,
                    2,
                )
                if not boostertest and not boostertest2:
                    success = rpgtools.calcchance(
                        swordbonus,
                        shieldbonus,
                        isfinished[3],
                        int(playerlevel),
                        returnsuccess=True,
                    )
                elif boostertest and not boostertest2:
                    await conn.execute(
                        'DELETE FROM boosters WHERE "user"=$1 AND "type"=$2;',
                        ctx.author.id,
                        2,
                    )
                    success = rpgtools.calcchance(
                        swordbonus,
                        shieldbonus,
                        isfinished[3],
                        int(playerlevel),
                        returnsuccess=True,
                    )
                elif boostertest and boostertest2:
                    success = rpgtools.calcchance(
                        swordbonus,
                        shieldbonus,
                        isfinished[3],
                        int(playerlevel),
                        returnsuccess=True,
                        booster=True,
                    )
                if success:
                    if isfinished[3] < 6:
                        maximumstat = float(random.randint(1, isfinished[3] * 5))
                    else:
                        maximumstat = float(random.randint(1, 25))
                    boostertest = await conn.fetchval(
                        'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2;',
                        ctx.author.id,
                        3,
                    )
                    boostertest2 = await conn.fetchval(
                        'SELECT "end" FROM boosters WHERE "user"=$1 AND "type"=$2 AND clock_timestamp() < "end";',
                        ctx.author.id,
                        3,
                    )
                    if not boostertest and not boostertest2:
                        gold = random.randint(1, 30) * isfinished[3]
                    elif boostertest and not boostertest2:
                        await conn.execute(
                            'DELETE FROM boosters WHERE "user"=$1 AND "type"=$2;',
                            ctx.author.id,
                            3,
                        )
                        gold = random.randint(1, 30) * isfinished[3]
                    elif boostertest and boostertest2:
                        gold = int(random.randint(1, 30) * isfinished[3] * 1.25)
                    xp = random.randint(200, 1000) * isfinished[3]
                    shieldorsword = random.choice(["sw", "sh"])
                    names = [
                        "Victo's",
                        "Arsandor's",
                        "Nuhulu's",
                        "Legendary",
                        "Vosag's",
                        "Mitoa's",
                        "Scofin's",
                        "Skeeren's",
                        "Ager's",
                        "Hazuro's",
                        "Atarbu's",
                        "Jadea's",
                        "Zosus'",
                        "Thocubra's",
                        "Utrice's",
                        "Lingoad's",
                        "Zlatorpian's",
                    ]
                    if shieldorsword == "sw":
                        item = await conn.fetchrow(
                            'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                            ctx.author.id,
                            random.choice(names)
                            + random.choice([" Sword", " Blade", " Stich"]),
                            random.randint(1, 40) * isfinished[3],
                            "Sword",
                            maximumstat,
                            0.00,
                        )
                    if shieldorsword == "sh":
                        item = await conn.fetchrow(
                            'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                            ctx.author.id,
                            random.choice(names)
                            + random.choice([" Shield", " Defender", " Aegis"]),
                            random.randint(1, 40) * isfinished[3],
                            "Shield",
                            0.00,
                            maximumstat,
                        )
                    await conn.execute(
                        'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                        item[0],
                        False,
                    )
                    # marriage partner should get 50% of the money
                    partner = await conn.fetchval(
                        'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
                    )
                    if partner != 0:
                        await conn.execute(
                            'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                            int(gold / 2),
                            partner,
                        )
                        # guild money
                    guild = await conn.fetchval(
                        'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
                    )
                    if guild != 0:
                        await conn.execute(
                            'UPDATE guild SET money=money+$1 WHERE "id"=$2;',
                            int(gold / 10),
                            guild,
                        )
                    # !!! TEMPORARY EASTER EVENT !!!
                    # eggs = int(round(isfinished[3] ** 1.5 * random.randint(4, 6), 0))
                    await conn.execute(
                        'UPDATE profile SET "money"="money"+$1, "xp"="xp"+$2, "completed"="completed"+1 WHERE "user"=$3;',
                        gold,
                        xp,
                        # eggs,
                        ctx.author.id,
                    )
                    if partner == 0:
                        await ctx.send(
                            f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item[2]}**. Experience gained: **{xp}**."  # \nYou found **{eggs}** eastereggs! <:easteregg:566251086986608650> (`{ctx.prefix}easter`)
                        )
                    else:
                        await ctx.send(
                            f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item[2]}**. Experience gained: **{xp}**.\nYour partner received **${int(gold/2)}**."  # You found **{eggs}** eastereggs! <:easteregg:566251086986608650> (`{ctx.prefix}easter`)
                        )
                else:
                    await ctx.send("You died on your mission. Try again!")
                    await conn.execute(
                        'UPDATE profile SET deaths=deaths+1 WHERE "user"=$1;',
                        ctx.author.id,
                    )
                await conn.execute(
                    'DELETE FROM mission WHERE "name"=$1;', ctx.author.id
                )
            else:
                # mission = await conn.fetchrow('SELECT * FROM mission WHERE name=$1 AND clock_timestamp() < "end";', ctx.author.id)
                mission = ret
                remain = await conn.fetchval("SELECT $1-clock_timestamp();", mission[2])
                dungeon = await conn.fetchrow(
                    "SELECT * FROM dungeon WHERE id=$1;", mission[3]
                )
                await ctx.send(
                    f"You are currently in the adventure with difficulty `{mission[3]}`.\nApproximate end in `{str(remain).split('.')[0]}`\nDungeon Name: `{dungeon[1]}`"
                )

    @has_char()
    @commands.command(description="Cancels your current mission.")
    async def cancel(self, ctx):
        async with self.bot.pool.acquire() as conn:
            ret = await self.bot.pool.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
            )
            if not ret:
                return await ctx.send("You are on no mission.")
            await conn.execute('DELETE FROM mission WHERE "name"=$1;', ctx.author.id)
        await ctx.send(
            f"Canceled your mission. Use `{ctx.prefix}adventure [missionID]` to start a new one!"
        )

    @has_char()
    @commands.command(description="Your death stats.")
    async def deaths(self, ctx):
        deaths, completed = await self.bot.pool.fetchval(
            'SELECT (deaths, completed) FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if (deaths + completed) != 0:
            rate = round(completed / (deaths + completed) * 100, 2)
        else:
            rate = 100
        await ctx.send(
            f"Out of **{deaths + completed}** adventures, you died **{deaths}** times and survived **{completed}** times, which is a success rate of **{rate}%**."
        )


def setup(bot):
    bot.add_cog(Adventure(bot))
