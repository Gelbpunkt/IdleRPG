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

from base64 import b64decode
from io import BytesIO

import discord

from discord.ext import commands

from classes.converters import IntFromTo
from classes.enums import DonatorRank
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import items
from utils import misc as rpgtools
from utils import random
from utils.checks import has_adventure, has_char, has_no_adventure
from utils.i18n import _, locale_doc
from utils.maze import Maze


class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(
        aliases=["missions", "dungeons"], brief=_("Shows adventures and your chances")
    )
    @locale_doc
    async def adventures(self, ctx):
        _(
            """Shows all adventures, their names, descriptions, and your chances to beat them in picture form.
            Your chances are determined by your equipped items, race and class bonuses, your level and your God-given luck.
            The extra +25% added by luck boosters will *not* be displayed in these pictures."""
        )
        damage, defense = await self.bot.get_damage_armor_for(ctx.author)
        all_dungeons = list(self.bot.config.adventure_times.keys())
        level = rpgtools.xptolevel(ctx.character_data["xp"])

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
    @commands.command(
        aliases=["mission", "a"], brief=_("Sends your character on an adventure.")
    )
    @locale_doc
    async def adventure(self, ctx, adventure_number: IntFromTo(1, 30)):
        _(
            """`<adventure_number>` - a whole number from 1 to 30

            Send your character on an adventure with the difficulty `<adventure_number>`.
            The adventure will take `<adventure_number>` hours if no time booster is used, and half as long if a time booster is used.

            If you are in an alliance which owns a city with adventure buildings, your adventure time will be reduced by the adventure building level in %.
            Donators' time will also be reduced:
              - 5% reduction for Silver Donators
              - 10% reduction for Gold Donators
              - 25% reduction for Emerald Donators and above

            Be sure to check `{prefix}status` to check how much time is left, or to check if you survived or died."""
        )
        if adventure_number > int(rpgtools.xptolevel(ctx.character_data["xp"])):
            return await ctx.send(
                _("You must be on level **{level}** to do this adventure.").format(
                    level=adventure_number
                )
            )
        time = self.bot.config.adventure_times[adventure_number]

        if (
            buildings := await self.bot.get_city_buildings(ctx.character_data["guild"])
        ) :
            time -= time * (buildings["adventure_building"] / 100)
        if user_rank := await self.bot.get_donator_rank(ctx.author.id):
            if user_rank >= DonatorRank.emerald:
                time = time * 0.75
            elif user_rank >= DonatorRank.gold:
                time = time * 0.9
            elif user_rank >= DonatorRank.silver:
                time = time * 0.95
        time_booster = await self.bot.get_booster(ctx.author, "time")
        if time_booster:
            time = time / 2
        await self.bot.start_adventure(ctx.author, adventure_number, time)
        await ctx.send(
            _(
                "Successfully sent your character out on an adventure. Use"
                " `{prefix}status` to see the current status of the mission."
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @has_no_adventure()
    @user_cooldown(7200)
    @commands.command(aliases=["aa"], brief=_("Go out on an active adventure."))
    @locale_doc
    async def activeadventure(self, ctx):
        _(
            # xgettext: no-python-format
            """Active adventures will put you into a 15x15 randomly generated maze. You will begin in the top left corner (0,0) and your goal is to find the exit in the bottom right corner (14,14)
            You control your character with the arrow reactions below the message.

            You have 1000HP. The adventure ends when you find the exit or your HP drop to zero.
            You can lose HP by getting damaged by traps or enemies.

            The maze contains safe spaces and treasures but also traps and enemies.
            Each space has a 10% chance of being a trap. If a space does not have a trap, it has a 10% chance of having an enemy.
            Each maze has 5 treasure chests.

            Traps can damage you from 30 to 120 HP.
            Enemy damage is based on your own damage. During enemy fights, you can attack (⚔️), defend (🛡️) or recover HP (❤️)
            Treasure chests can have gold up to 25 times your attack + defense.

            If you reach the end, you will receive a special treasure with gold up to 100 times your attack + defense.

            (It is recommended to draw a map of the maze)
            (This command has a cooldown of 30 minutes)"""
        )
        if not await ctx.confirm(
            _(
                "You are going to be in a labyrinth of size 15x15. There are enemies,"
                " treasures and hidden traps. Reach the exit in the bottom right corner"
                " for a huge extra bonus!\nAre you ready?\n\nTip: Use a silent channel"
                " for this, you may want to read all the messages I will send."
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

        attack, defense = await self.bot.get_damage_armor_for(ctx.author)
        attack, defense = await self.bot.generate_stats(ctx.author, attack, defense)

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
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": money},
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
                await self.bot.reset_cooldown(ctx)
                return await msg.edit(content=_("Timed out."))
            x, y = move(x, y, direction)  # Python namespacing sucks, to be honest
            try:
                hp = await handle_specials(hp)  # Should've used a class for this
            except asyncio.TimeoutError:
                await self.bot.reset_cooldown(ctx)
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
        await self.bot.log_transaction(
            ctx, from_=1, to=ctx.author.id, subject="money", data={"Amount": money}
        )

        await ctx.send(
            _(
                "You have reached the exit and were rewarded **${money}** for getting"
                " out!"
            ).format(money=money)
        )

    @has_char()
    @has_adventure()
    @commands.command(aliases=["s"], brief=_("Checks your adventure status."))
    @locale_doc
    async def status(self, ctx):
        _(
            """Checks the remaining time of your adventures, or if you survived or died. Your chance is checked here, not in `{prefix}adventure`.
            Your chances are determined by your equipped items, race and class bonuses, your level, God-given luck and active luck boosters.

            If you are in an alliance which owns a city with an adventure building, your chance will be increased by 5% per building level.

            If you survive on your adventure, you will receive gold up to the adventure number times 60, XP up to 500 times the adventure number and either a loot or gear item.
            The chance of loot is dependent on the adventure number and whether you use the Ritualist class, [check our wiki](https://wiki.travitia.xyz/index.php?title=Loot) for the exact chances.

            God given luck affects the amount of gold and the gear items' damage/defense and value.

            If you are in a guild, its guild bank will receive 10% of the amount of gold extra.
            If you are married, your partner will receive a portion of your gold extra as well, [check the wiki](https://wiki.travitia.xyz/index.php?title=Family#Adventure_Bonus) for the exact portion."""
        )
        num, time, done = ctx.adventure_data

        if not done:
            # TODO: Embeds ftw
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

        damage, armor = await self.bot.get_damage_armor_for(ctx.author)
        damage, armor = await self.bot.generate_stats(
            ctx.author,
            damage,
            armor,
            classes=ctx.character_data["class"],
            race=ctx.character_data["race"],
        )

        luck_booster = await self.bot.get_booster(ctx.author, "luck")
        current_level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        luck_multiply = ctx.character_data["luck"]
        if (
            buildings := await self.bot.get_city_buildings(ctx.character_data["guild"])
        ) :
            bonus = buildings["adventure_building"]
        else:
            bonus = 0
        success = rpgtools.calcchance(
            damage,
            armor,
            num,
            current_level,
            luck_multiply,
            returnsuccess=True,
            booster=bool(luck_booster),
            bonus=bonus,
        )
        await self.bot.delete_adventure(ctx.author)

        if not success:
            await self.bot.pool.execute(
                'UPDATE profile SET "deaths"="deaths"+1 WHERE "user"=$1;', ctx.author.id
            )
            return await ctx.send(_("You died on your mission. Try again!"))

        gold = round(random.randint(20 * num, 60 * num) * luck_multiply)

        if await self.bot.get_booster(ctx.author, "money"):
            gold = int(gold * 1.25)

        xp = random.randint(250 * num, 500 * num)
        chance_of_loot = 5 if num == 1 else 5 + 1.5 * num
        if self.bot.in_class_line(ctx.character_data["class"], "Ritualist"):
            chance_of_loot *= 2  # can be 100 in a 30

        async with self.bot.pool.acquire() as conn:
            if (random.randint(1, 1000)) > chance_of_loot * 10:
                minstat = round(num * luck_multiply)
                maxstat = round(5 + int(num * 1.5) * luck_multiply)

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
                'UPDATE profile SET "money"="money"+$1, "xp"="xp"+$2,'
                ' "completed"="completed"+1 WHERE "user"=$3;',
                gold,
                xp,
                ctx.author.id,
            )

            if (partner := ctx.character_data["marriage"]) :
                await conn.execute(
                    'UPDATE profile SET "money"="money"+($1*(1+"lovescore"/1000000))'
                    ' WHERE "user"=$2;',
                    int(gold / 2),
                    partner,
                )

            await self.bot.log_transaction(
                ctx,
                from_=1,
                to=ctx.author.id,
                subject="adventure",
                data={
                    "Gold": gold,
                    "Item": item["name"],  # compare against loot names if necessary
                    "Value": item["value"],
                },
            )

            # TODO: Embeds ftw
            await ctx.send(
                _(
                    "You have completed your adventure and received **${gold}** as well"
                    " as a new item: **{item}**. Experience gained: **{xp}**."
                ).format(gold=gold, item=item["name"], xp=xp)
            )

            new_level = int(rpgtools.xptolevel(ctx.character_data["xp"] + xp))

            if current_level != new_level:
                await self.bot.process_levelup(ctx, new_level, current_level)

    @has_char()
    @has_adventure()
    @commands.command(brief=_("Cancels your current adventure."))
    @locale_doc
    async def cancel(self, ctx):
        _(
            """Cancels your ongoing adventure and allows you to start a new one right away. You will not receive any rewards if you cancel your adventure."""
        )
        if not await ctx.confirm(
            _("Are you sure you want to cancel your current adventure?")
        ):
            return await ctx.send(
                _("Did not cancel your adventure. The journey continues...")
            )
        await self.bot.delete_adventure(ctx.author)
        await ctx.send(
            _(
                "Canceled your mission. Use `{prefix}adventure [missionID]` to start a"
                " new one!"
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @commands.command(brief=_("Show some adventure stats"))
    @locale_doc
    async def deaths(self, ctx):
        _(
            """Shows your overall adventure death and completed count, including your success rate."""
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
                "Out of **{total}** adventures, you died **{deaths}** times and"
                " survived **{completed}** times, which is a success rate of"
                " **{rate}%**."
            ).format(
                total=deaths + completed, deaths=deaths, completed=completed, rate=rate
            )
        )


def setup(bot):
    bot.add_cog(Adventure(bot))
