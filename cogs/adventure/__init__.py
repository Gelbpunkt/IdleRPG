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

from base64 import b64decode
from io import BytesIO

import discord

from discord.ext import commands

from classes.converters import IntFromTo
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import items
from utils import misc as rpgtools
from utils.checks import has_adventure, has_char, has_no_adventure
from utils.maze import Maze


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
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/genadventures",
            json={"percentages": chances},
        ) as r:
            images = await r.json()

        await msg.delete()

        files = [
            discord.File(
                filename=f"Adventure{idx + 1}.png", fp=BytesIO(b64decode(img[22:]))
            )
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
    async def adventure(self, ctx, dungeonnumber: AreaFiftyOneInt(1, 20)):
        _("""Sends your character on an adventure.""")
        if dungeonnumber > int(rpgtools.xptolevel(ctx.character_data["xp"])):
            if dungeonnumber != 21: # bybass level req. for the event
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

    @has_char()
    @has_no_adventure()
    @user_cooldown(7200)
    @commands.command()
    @locale_doc
    async def activeadventure(self, ctx):
        _("""Go out on a docile adventure controlled by reactions.""")
        if not await ctx.confirm(
            _(
                "You are going to be in a labyrinth of size 15x15. There are enemies, treasures and hidden traps. Reach the exit in the bottom right corner for a huge extra bonus!\nAre you ready?\n\nTip: Use a silent channel for this, you may want to read all the messages I will send."
            )
        ):
            return

        msg = await ctx.send(_("**Generating a maze...**"))

        maze = Maze.generate(15, 15)
        direction_emojis = {
            "n": "\U00002b06",
            "e": "\U000027a1",
            "s": "\U00002b07",
            "w": "\U00002b05",
        }
        direction_emojis_inverse = {val: key for key, val in direction_emojis.items()}
        direction_names = {
            "n": _("North"),
            "e": _("East"),
            "s": _("South"),
            "w": _("West"),
        }
        all_directions = set(direction_names.keys())
        x = 0
        y = 0

        sword, shield = await self.bot.get_equipped_items_for(ctx.author)
        attack, defense = await self.bot.generate_stats(
            ctx.author,
            float(sword["damage"] if sword else 0),
            float(shield["armor"] if shield else 0),
        )

        attack = int(attack)
        defense = int(defense)

        hp = 1000

        def free(cell):
            return all_directions - cell.walls

        def fmt_direction(direction):
            return direction_names[direction]

        def player_pos():
            return maze[x, y]

        def is_at_end():
            return x == 14 and y == 14

        def move(x, y, direction):
            if direction == "n":
                y = y - 1
            elif direction == "e":
                x = x + 1
            elif direction == "s":
                y = y + 1
            elif direction == "w":
                x = x - 1
            return x, y

        async def wait_for_move():
            possible = free(player_pos())
            needed = [direction_emojis[direction] for direction in possible]
            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                for r in msg.reactions:
                    if str(r.emoji) not in needed:
                        await msg.remove_reaction(r, ctx.guild.me)
                for r in needed:
                    if r not in [str(r.emoji) for r in msg.reactions]:
                        await msg.add_reaction(r)
            else:
                for direction in possible:
                    await msg.add_reaction(direction_emojis[direction])

            def check(r, u):
                return (
                    u == ctx.author
                    and r.message.id == msg.id
                    and direction_emojis_inverse.get(str(r.emoji), None) in possible
                )

            r, u = await self.bot.wait_for("reaction_add", check=check, timeout=30)

            return direction_emojis_inverse[str(r.emoji)]

        async def update():
            text = ""
            pos = player_pos()
            for direction in ("n", "e", "s", "w"):
                side = fmt_direction(direction)
                fake_x, fake_y = move(x, y, direction)
                fake_cell = maze[fake_x, fake_y]
                if direction in pos.walls:
                    text2 = _("To the {side} is a wall.").format(side=side)
                elif fake_cell.enemy:
                    text2 = _("To the {side} is an enemy.").format(side=side)
                elif fake_cell.treasure:
                    text2 = _("To the {side} is a treasure.").format(side=side)
                else:
                    text2 = _("To the {side} is a floor.").format(side=side)
                text = f"{text}\n{text2}"

            text2 = _("You are on {hp} HP").format(hp=hp)
            text = f"{text}\n\n{text2}"

            await msg.edit(content=text)

        async def handle_specials(hp):
            cell = player_pos()
            if cell.trap:
                damage = random.randint(30, 120)
                await ctx.send(
                    _("You stepped on a trap and took {damage} damage!").format(
                        damage=damage
                    )
                )
                cell.trap = False  # Remove the trap
                return hp - damage
            elif cell.treasure:
                val = attack + defense
                money = random.randint(val, val * 25)
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await ctx.send(
                    _("You found a treasure with **${money}** inside!").format(
                        money=money
                    )
                )
                cell.treasure = False
            elif cell.enemy:

                def to_bar(hp):
                    fields = hp // 100
                    return f"[{'▯' * fields}{'▮' * (10 - fields)}]"

                def is_valid_move(r, u):
                    return (
                        r.message.id == msg.id
                        and u == ctx.author
                        and str(r.emoji) in emojis
                    )

                emojis = {
                    "\U00002694": "attack",
                    "\U0001f6e1": "defend",
                    "\U00002764": "recover",
                }
                enemy = _("Enemy")
                enemy_hp = 1000
                heal_hp = round(attack * 0.25) or 1
                min_dmg = round(attack * 0.5)
                max_dmg = round(attack * 1.5)
                status1 = _("The Fight started")
                status2 = ""

                await msg.clear_reactions()
                for emoji in emojis:
                    await msg.add_reaction(emoji)

                while enemy_hp > 0 and hp > 0:
                    await msg.edit(
                        content=f"""\
```
{ctx.author.name}{" " * (38 - len(ctx.author.name) - len(enemy))}{enemy}
------------++++++++++++++------------
{to_bar(hp)}  {hp}  {enemy_hp}    {to_bar(enemy_hp)}

{status1}
{status2}
```"""
                    )

                    r, u = await self.bot.wait_for(
                        "reaction_add", check=is_valid_move, timeout=30
                    )

                    try:
                        await msg.remove_reaction(r, u)
                    except discord.Forbidden:
                        pass

                    enemy_move = random.choice(["attack", "defend", "recover"])
                    player_move = emojis[str(r.emoji)]

                    if enemy_move == "recover":
                        enemy_hp += heal_hp
                        enemy_hp = 1000 if enemy_hp > 1000 else enemy_hp
                        status1 = _("The Enemy healed themselves for {hp} HP").format(
                            hp=heal_hp
                        )
                    if player_move == "recover":
                        hp += heal_hp
                        hp = 1000 if hp > 1000 else hp
                        status2 = _("You healed yourself for {hp} HP").format(
                            hp=heal_hp
                        )
                    if (enemy_move == "attack" and player_move == "defend") or (
                        enemy_move == "defend" and player_move == "attack"
                    ):
                        status1 = _("Attack blocked.")
                        status2 = ""
                    if enemy_move == "attack" and player_move != "defend":
                        eff = random.randint(min_dmg, max_dmg)
                        hp -= eff
                        status1 = _("The Enemy hit you for {dmg} damage").format(
                            dmg=eff
                        )
                    if player_move == "attack" and enemy_move != "defend":
                        enemy_hp -= attack
                        status2 = _("You hit the enemy for {dmg} damage").format(
                            dmg=attack
                        )

                if enemy_hp <= 0:
                    cell.enemy = False

            return hp

        while not is_at_end():
            await update()
            try:
                direction = await wait_for_move()
            except asyncio.TimeoutError:
                return await msg.edit(content=_("Timed out."))
            x, y = move(x, y, direction)  # Python namespacing sucks, to be honest
            try:
                hp = await handle_specials(hp)  # Should've used a class for this
            except asyncio.TimeoutError:
                return await msg.edit(content=_("Timed out."))
            if hp <= 0:
                return await ctx.send(_("You died."))

        val = attack + defense
        money = random.randint(val * 5, val * 100)
        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
            money,
            ctx.author.id,
        )

        await ctx.send(
            _(
                "You have reached the exit and were rewarded **${money}** for getting out!"
            ).format(money=money)
        )

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
            classes=ctx.character_data["class"],
            race=ctx.character_data["race"],
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

            if (
                random.randint(
                    1,
                    (
                        5
                        if self.bot.in_class_line(
                            ctx.character_data["class"], "Ritualist"
                        )
                        else 10
                    ),
                )
                != 1
            ):
                minstat = round(num * luck_multiply)
                maxstat = round(5 + int(num * 1.5) * luck_multiply)
                
                if num == 51:
                    item = await self.bot.create_random_51_item(
                        minstat=(minstat if minstat > 0 else 1) if minstat < 35 else 35,
                        maxstat=(maxstat if maxstat > 0 else 1) if maxstat < 35 else 35,
                        minvalue=round(num * luck_multiply),
                        maxvalue=round(num * 50 * luck_multiply),
                        owner=ctx.author,
                    )
                
                else:
                    item = await self.bot.create_random_item(
                        minstat=(minstat if minstat > 0 else 1) if minstat < 35 else 35,
                        maxstat=(maxstat if maxstat > 0 else 1) if maxstat < 35 else 35,
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

            if current_level != new_level:
                await self.bot.process_levelup(ctx, new_level)

    @has_char()
    @has_adventure()
    @commands.command()
    @locale_doc
    async def cancel(self, ctx):
        _("""Cancels your current adventure.""")
        if not await ctx.confirm(
            _("Are you sure you want to cancel your current adventure?")
        ):
            return await ctx.send(
                _("Did not cancel your adventure. The journey continues...")
            )
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
        _(
            """Your death stats. Shows statictics from all your adventures ever completed."""
        )
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
