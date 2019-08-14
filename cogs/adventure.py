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
import functools
import random

import discord
from discord.ext import commands

from classes.converters import IntFromTo
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import items
from utils import misc as rpgtools
from utils.checks import has_adventure, has_char, has_no_adventure


class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(aliases=["missions", "dungeons"])
    @locale_doc
    async def adventures(self, ctx):
        _("""A list of all adventures with success rates, name and time it takes.""")
        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        all_dungeons = list(self.bot.config.adventure_times.keys())
        level = rpgtools.xptolevel(ctx.character_data["xp"])
        damage = sword["damage"] if sword else 0
        defense = shield["armor"] if shield else 0

        msg = await ctx.send(_("Loading images..."))

        chances = []
        for adv in all_dungeons:
            success = rpgtools.calcchance(
                damage,
                defense,
                adv,
                int(level),
                ctx.character_data["luck"],
                returnsuccess=False,
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

    @has_char()
    @has_no_adventure()
    @commands.command(aliases=["mission", "a", "dungeon"])
    @locale_doc
    async def adventure(self, ctx, dungeonnumber: IntFromTo(1, 20)):
        _("""Sends your character on an adventure.""")
        if dungeonnumber > int(rpgtools.xptolevel(ctx.character_data["xp"])):
            return await ctx.send(
                _("You must be on level **{level}** to do this adventure.").format(
                    level=dungeonnumber
                )
            )
        time_booster = await self.bot.get_booster(ctx.author, "time")
        time = self.bot.config.adventure_times[dungeonnumber]
        if time_booster:
            time = time / 2
        await self.bot.start_adventure(ctx.author, dungeonnumber, time)
        await ctx.send(
            _(
                "Successfully sent your character out on an adventure. Use `{prefix}status` to see the current status of the mission."
            ).format(prefix=ctx.prefix)
        )

    @has_no_adventure()
    @user_cooldown(3600)
    @commands.command()
    @locale_doc
    async def activeadventure(self, ctx):
        _("""Go out on an active, action based adventure.""")
        msg = await ctx.send(_("**Active adventure loading...**"))
        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        SWORD = sword["damage"] if sword else 0
        SHIELD = shield["armor"] if shield else 0
        # class test
        SWORD, SHIELD = await self.bot.generate_stats(
            ctx.author, float(SWORD), float(SHIELD)
        )
        HP = 100
        PROGRESS = 0  # percent
        emojis = {
            "\U00002694": "attack",
            "\U0001f6e1": "defend",
            "\U00002764": "recover",
        }

        def is_valid_move(r, u):
            return r.message.id == msg.id and u == ctx.author and str(r.emoji) in emojis

        ENEMY_HP = 100

        for emoji in emojis:
            await msg.add_reaction(emoji)

        while PROGRESS < 100 and HP > 0:
            await msg.edit(
                content=_(
                    """
**{user}'s Adventure**
```
Progress: {progress}%
HP......: {hp}

Enemy
HP......: {enemy_hp}

Use the reactions attack, defend or recover
```
"""
                ).format(user=ctx.disp, progress=PROGRESS, hp=HP, enemy_hp=ENEMY_HP)
            )
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30, check=is_valid_move
                )
            except asyncio.TimeoutError:
                return await ctx.send(
                    _("Adventure stopped because you refused to move.")
                )
            try:
                await msg.remove_reaction(reaction, ctx.author)
            except discord.Forbidden:
                pass
            move = emojis[str(reaction.emoji)]
            enemymove = random.choice(["attack", "defend", "recover"])
            if move == "recover":
                HP += 20
                await ctx.send(_("You healed yourself for 20 HP."), delete_after=5)
            if enemymove == "recover":
                ENEMY_HP += 20
                await ctx.send(_("The enemy healed himself for 20 HP."), delete_after=5)
            if move == "attack" and enemymove == "defend":
                await ctx.send(_("Your attack was blocked!"), delete_after=5)
            if move == "defend" and enemymove == "attack":
                await ctx.send(_("Enemy attack was blocked!"), delete_after=5)
            if move == "defend" and enemymove == "defend":
                await ctx.send(_("Noone attacked."))
            if move == "attack" and enemymove == "attack":
                efficiency = random.randint(int(SWORD * 0.5), int(SWORD * 1.5))
                HP -= efficiency
                ENEMY_HP -= SWORD
                await ctx.send(
                    _(
                        "You hit the enemy for **{damage}** damage, he hit you for **{damage2}** damage."
                    ).format(damage=SWORD, damage2=efficiency),
                    delete_after=5,
                )
            elif move == "attack" and enemymove != "defend":
                ENEMY_HP -= SWORD
                await ctx.send(
                    _("You hit the enemy for **{damage}** damage.").format(
                        damage=SWORD
                    ),
                    delete_after=5,
                )
            elif enemymove == "attack" and move == "recover":
                efficiency = random.randint(int(SWORD * 0.5), int(SWORD * 1.5))
                HP -= efficiency
                await ctx.send(
                    _("The enemy hit you for **{damage}** damage.").format(
                        damage=efficiency
                    ),
                    delete_after=5,
                )
            if ENEMY_HP < 1:
                await ctx.send(
                    _("Enemy defeated! You gained **20 HP**"), delete_after=5
                )
                PROGRESS += random.randint(10, 40)
                ENEMY_HP = 100
                HP += 20

        if HP < 1:
            return await ctx.send(_("You died."))

        avg = (SWORD + SHIELD) // 2
        maxstat = round((avg + 5) * ctx.character_data["luck"])
        item = await self.bot.create_random_item(
            minstat=1,
            maxstat=(maxstat if maxstat < 30 else 30),
            minvalue=1,
            maxvalue=250,
            owner=ctx.author,
        )
        embed = discord.Embed(
            title=_("You gained an item!"),
            description=_("You found a new item when finishing an active adventure!"),
            color=0xFF0000,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name=_("ID"), value=item["id"], inline=False)
        embed.add_field(name=_("Name"), value=item["name"], inline=False)
        embed.add_field(name=_("Type"), value=item["type"], inline=False)
        embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
        embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
        embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
        embed.set_footer(text=_("Your HP were {hp}").format(hp=HP))
        await ctx.send(embed=embed)

    @has_char()
    @has_adventure()
    @commands.command(aliases=["s"])
    @locale_doc
    async def status(self, ctx):
        _("""Checks your adventure status.""")
        num, time, done = ctx.adventure_data

        if not done:
            return await ctx.send(
                _(
                    """\
You are currently on an adventure with difficulty `{difficulty}`.
Time until it completes: `{time_left}`
Adventure name: `{adventure}`"""
                ).format(
                    difficulty=num,
                    time_left=time,
                    adventure=self.bot.config.adventure_names[num],
                )
            )

        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        sword, shield = await self.bot.generate_stats(
            ctx.author,
            sword["damage"] if sword else 0,
            shield["armor"] if shield else 0,
            class_=ctx.character_data["class"],
        )

        luck_booster = await self.bot.get_booster(ctx.author, "luck")
        current_level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        luck_multiply = ctx.character_data["luck"]
        success = rpgtools.calcchance(
            sword,
            shield,
            num,
            current_level,
            luck_multiply,
            returnsuccess=True,
            booster=bool(luck_booster),
        )
        await self.bot.delete_adventure(ctx.author)

        if not success:
            await self.bot.pool.execute(
                'UPDATE profile SET "deaths"="deaths"+1 WHERE "user"=$1;', ctx.author.id
            )
            return await ctx.send(_("You died on your mission. Try again!"))

        gold = round(
            random.randint(20 * (num - 1) or 1, 60 * (num - 1) or 70) * luck_multiply
        )

        if await self.bot.get_booster(ctx.author, "money"):
            gold = int(gold * 1.25)

        xp = random.randint(250 * num, 500 * num)

        async with self.bot.pool.acquire() as conn:

            if random.randint(1, 10) < 10:
                minstat = round(num * luck_multiply)
                maxstat = round(5 + int(num * 1.5) * luck_multiply)
                item = await self.bot.create_random_item(
                    minstat=minstat if minstat < 35 else 35,
                    maxstat=maxstat if maxstat < 35 else 35,
                    minvalue=round(num * luck_multiply),
                    maxvalue=round(num * 50 * luck_multiply),
                    owner=ctx.author,
                )
            else:
                item = items.get_item()
                await conn.execute(
                    'INSERT INTO loot ("name", "value", "user") VALUES ($1, $2, $3);',
                    item["name"],
                    item["value"],
                    ctx.author.id,
                )

            if (guild := ctx.character_data["guild"]) :
                await conn.execute(
                    'UPDATE guild SET "money"="money"+$1 WHERE "id"=$2;',
                    int(gold / 10),
                    guild,
                )

            await conn.execute(
                'UPDATE profile SET "money"="money"+$1, "xp"="xp"+$2, "completed"="completed"+1 WHERE "user"=$3;',
                gold,
                xp,
                ctx.author.id,
            )

            if (partner := ctx.character_data["marriage"]) :
                await conn.execute(
                    'UPDATE profile SET "money"="money"+($1*(1+"lovescore"/1000000)) WHERE "user"=$2;',
                    int(gold / 2),
                    partner,
                )

            await ctx.send(
                _(
                    "You have completed your adventure and received **${gold}** as well as a new item: **{item}**. Experience gained: **{xp}**."
                ).format(gold=gold, item=item["name"], xp=xp)
            )

            new_level = int(rpgtools.xptolevel(ctx.character_data["xp"] + xp))

            if current_level == new_level:
                return

            if (reward := random.choice(["crates", "money", "item"])) == "crates":
                if new_level < 6:
                    column = "crates_common"
                    amount = new_level
                    reward_text = f"**{amount}** <:CrateCommon:598094865666015232>"
                elif new_level < 10:
                    column = "crates_uncommon"
                    amount = round(new_level / 2)
                    reward_text = f"**{amount}** <:CrateUncommon:598094865397579797>"
                elif new_level < 15:
                    column = "crates_rare"
                    amount = 2
                    reward_text = "**2** <:CrateRare:598094865485791233>"
                elif new_level < 20:
                    column = "crates_rare"
                    amount = 3
                    reward_text = "**3** <:CrateRare:598094865485791233>"
                else:
                    column = "crates_magic"
                    amount = 1
                    reward_text = "**1** <:CrateMagic:598094865611358209>"
                await self.bot.pool.execute(
                    f'UPDATE profile SET {column}={column}+$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
            elif reward == "item":
                stat = round(new_level * 1.5)
                item = await self.bot.create_random_item(
                    minstat=stat,
                    maxstat=stat,
                    minvalue=1000,
                    maxvalue=1000,
                    owner=ctx.author,
                    insert=False,
                )
                item["name"] = _("Level {new_level} Memorial").format(
                    new_level=new_level
                )
                reward_text = "a special weapon"
                await self.bot.create_item(**item)
            elif reward == "money":
                money = new_level * 1000
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                reward_text = f"**${money}**"

            await ctx.send(
                _(
                    "You reached a new level: **{new_level}** :star:! You received {reward} as a reward :tada:!"
                ).format(new_level=new_level, reward=reward_text)
            )

    @has_char()
    @has_adventure()
    @commands.command()
    @locale_doc
    async def cancel(self, ctx):
        _("""Cancels your current adventure.""")
        await self.bot.delete_adventure(ctx.author)
        await ctx.send(
            _(
                "Canceled your mission. Use `{prefix}adventure [missionID]` to start a new one!"
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def deaths(self, ctx):
        _("""Your death stats.""")
        deaths, completed = await self.bot.pool.fetchval(
            'SELECT (deaths, completed) FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if (deaths + completed) != 0:
            rate = round(completed / (deaths + completed) * 100, 2)
        else:
            rate = 100
        await ctx.send(
            _(
                "Out of **{total}** adventures, you died **{deaths}** times and survived **{completed}** times, which is a success rate of **{rate}%**."
            ).format(
                total=deaths + completed, deaths=deaths, completed=completed, rate=rate
            )
        )


def setup(bot):
    bot.add_cog(Adventure(bot))
