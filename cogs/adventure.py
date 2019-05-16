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
from utils.checks import has_adventure, has_char, has_no_adventure


class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(aliases=["missions", "dungeons"])
    async def adventures(self, ctx):
        """A list of all adventures with success rates, name and time it takes."""
        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        all_dungeons = list(self.bot.config.adventure_times.keys())
        level = rpgtools.xptolevel(ctx.character_data["xp"])
        damage = sword["damage"] if sword else 0
        defense = shield["armor"] if shield else 0

        msg = await ctx.send("Loading images...")

        chances = []
        for adv in all_dungeons:
            success = rpgtools.calcchance(
                damage, defense, adv, int(level), returnsuccess=False
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
        time_booster = await self.bot.get_booster(ctx.author, "time")
        time = self.bot.config.adventure_times[dungeonnumber]
        if time_booster:
            time = time / 2
        await self.bot.start_adventure(ctx.author, dungeonnumber, time)
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
    @has_adventure()
    @commands.command(aliases=["s"])
    async def status(self, ctx):
        """Checks your adventure status."""
        num, time, done = ctx.adventure_data
        if done:
            sword, shield = await self.bot.get_equipped_items_for(ctx.author)
            playerlevel = rpgtools.xptolevel(ctx.character_data["xp"])

            sword = sword["damage"] if sword else 0
            shield = shield["armor"] if shield else 0

            # class test
            sword, shield = await genstats(self.bot, ctx.author.id, sword, shield)

            luck_booster = await self.bot.get_booster(ctx.author, "luck")
            success = rpgtools.calcchance(
                sword,
                shield,
                num,
                int(playerlevel),
                returnsuccess=True,
                booster=bool(luck_booster),
            )
            if success:
                maximumstat = (
                    float(random.randint(1, num * 5))
                    if num < 6
                    else float(random.randint(1, 25))
                )
                if await self.bot.get_booster(ctx.author, "money"):
                    gold = int(random.randint(1, 30) * num * 1.25)
                else:
                    gold = random.randint(1, 30) * num
                xp = random.randint(200, 1000) * num
                type_ = random.choice(["Sword", "Shield"])
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
                damage = maximumstat if type_ == "Sword" else 0
                armor = maximumstat if type_ == "Shield" else 0
                name = random.choice(names) + (
                    random.choice([" Sword", " Blade", " Stich"])
                    if type_ == "Sword"
                    else random.choice([" Shield", " Defender", " Aegis"])
                )
                async with self.bot.pool.acquire() as conn:
                    item = await conn.fetchrow(
                        'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                        ctx.author.id,
                        name,
                        random.randint(1, 40) * num,
                        type_,
                        damage,
                        armor,
                    )
                    await conn.execute(
                        'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                        item["id"],
                        False,
                    )
                    # marriage partner should get 50% of the money
                    if ctx.character_data["marriage"]:
                        await conn.execute(
                            'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                            int(gold / 2),
                            ctx.character_data["marriage"],
                        )
                    # guild money
                    if ctx.character_data["guild"]:
                        await conn.execute(
                            'UPDATE guild SET money=money+$1 WHERE "id"=$2;',
                            int(gold / 10),
                            ctx.character_data["guild"],
                        )
                    await conn.execute(
                        'UPDATE profile SET "money"="money"+$1, "xp"="xp"+$2, "completed"="completed"+1 WHERE "user"=$3;',
                        gold,
                        xp,
                        ctx.author.id,
                    )
                    if not ctx.character_data["marriage"]:
                        await ctx.send(
                            f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item['name']}**. Experience gained: **{xp}**."
                        )
                    else:
                        await ctx.send(
                            f"You have completed your dungeon and received **${gold}** as well as a new weapon: **{item['name']}**. Experience gained: **{xp}**.\nYour partner received **${int(gold/2)}**."
                        )
            else:
                await ctx.send("You died on your mission. Try again!")
                await self.bot.pool.execute(
                    'UPDATE profile SET deaths=deaths+1 WHERE "user"=$1;', ctx.author.id
                )
            await self.bot.delete_adventure(ctx.author)
        else:
            dungeon = self.bot.config.adventure_names[num]
            await ctx.send(
                f"You are currently in the adventure with difficulty `{num}`.\nApproximate end in `{str(time).split('.')[0]}`\nDungeon Name: `{dungeon}`"
            )

    @has_char()
    @has_adventure()
    @commands.command()
    async def cancel(self, ctx):
        """Cancels your current adventure."""
        await self.bot.delete_adventure(ctx.author)
        await ctx.send(
            f"Canceled your mission. Use `{ctx.prefix}adventure [missionID]` to start a new one!"
        )

    @has_char()
    @commands.command()
    async def deaths(self, ctx):
        """Your death stats."""
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
