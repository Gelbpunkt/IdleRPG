"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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

from datetime import datetime, timedelta
from enum import Enum
from functools import partial
from typing import Literal, Optional

import discord

from aioscheduler.task import Task
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui.button import Button

from classes.classes import Ritualist
from classes.classes import from_string as class_from_string
from classes.context import Context
from classes.converters import IntFromTo
from classes.enums import DonatorRank
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import items
from utils import misc as rpgtools
from utils import random
from utils.checks import has_adventure, has_char, has_no_adventure
from utils.i18n import _, locale_doc
from utils.maze import Cell, Maze

ADVENTURE_NAMES = {
    1: "Spider Cave",
    2: "Troll Bridge",
    3: "A Night Alone Outside",
    4: "Ogre Raid",
    5: "Proof Of Confidence",
    6: "Dragon Canyon",
    7: "Orc Tower",
    8: "Seamonster's Temple",
    9: "Dark Wizard's Castle",
    10: "Slay The Famous Dragon Arzagor",
    11: "Search For Excalibur",
    12: "Find Atlantis",
    13: "Tame A Phoenix",
    14: "Slay The Death Reaper",
    15: "Meet Adrian In Real Life",
    16: "The League Of Vecca",
    17: "The Gem Expedition",
    18: "Gambling Problems?",
    19: "The Necromancer Of Kord",
    20: "Last One Standing",
    21: "Gambling Problems? Again?",
    22: "Insomnia",
    23: "Illuminated",
    24: "Betrayal",
    25: "IdleRPG",
    26: "Learn Programming",
    27: "Scylla's Temple",
    28: "Trial Of Osiris",
    29: "Meet The War God In Hell",
    30: "Divine Intervention",
}

DIRECTION = Literal["n", "e", "s", "w"]
ALL_DIRECTIONS: set[DIRECTION] = {"n", "e", "s", "w"}


class ActiveAdventureAction(Enum):
    MoveNorth = 0
    MoveEast = 1
    MoveSouth = 2
    MoveWest = 3

    AttackEnemy = 4
    Defend = 5
    Recover = 6


class ActiveAdventureDirectionView(discord.ui.View):
    def __init__(
        self,
        user: discord.User,
        future: asyncio.Future[ActiveAdventureAction],
        possible_actions: set[ActiveAdventureAction],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.user = user
        self.future = future

        north = Button(
            style=ButtonStyle.primary,
            label=_("North"),
            disabled=ActiveAdventureAction.MoveNorth not in possible_actions,
            emoji="\U00002b06",
            row=0,
        )
        east = Button(
            style=ButtonStyle.primary,
            label=_("East"),
            disabled=ActiveAdventureAction.MoveEast not in possible_actions,
            emoji="\U000027a1",
            row=0,
        )
        south = Button(
            style=ButtonStyle.primary,
            label=_("South"),
            disabled=ActiveAdventureAction.MoveSouth not in possible_actions,
            emoji="\U00002b07",
            row=0,
        )
        west = Button(
            style=ButtonStyle.primary,
            label=_("West"),
            disabled=ActiveAdventureAction.MoveWest not in possible_actions,
            emoji="\U00002b05",
            row=0,
        )

        attack = Button(
            style=ButtonStyle.secondary,
            label=_("Attack"),
            disabled=ActiveAdventureAction.AttackEnemy not in possible_actions,
            emoji="\U00002694",
            row=1,
        )
        defend = Button(
            style=ButtonStyle.secondary,
            label=_("Defend"),
            disabled=ActiveAdventureAction.Defend not in possible_actions,
            emoji="\U0001f6e1",
            row=1,
        )
        recover = Button(
            style=ButtonStyle.secondary,
            label=_("Recover"),
            disabled=ActiveAdventureAction.Recover not in possible_actions,
            emoji="\U00002764",
            row=1,
        )

        north.callback = partial(self.handle, action=ActiveAdventureAction.MoveNorth)
        east.callback = partial(self.handle, action=ActiveAdventureAction.MoveEast)
        south.callback = partial(self.handle, action=ActiveAdventureAction.MoveSouth)
        west.callback = partial(self.handle, action=ActiveAdventureAction.MoveWest)
        attack.callback = partial(self.handle, action=ActiveAdventureAction.AttackEnemy)
        defend.callback = partial(self.handle, action=ActiveAdventureAction.Defend)
        recover.callback = partial(self.handle, action=ActiveAdventureAction.Recover)

        self.add_item(north)
        self.add_item(east)
        self.add_item(south)
        self.add_item(west)
        self.add_item(attack)
        self.add_item(defend)
        self.add_item(recover)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user.id

    async def handle(
        self, interaction: Interaction, action: ActiveAdventureAction
    ) -> None:
        self.stop()
        self.future.set_result(action)

    async def on_timeout(self) -> None:
        self.future.set_exception(asyncio.TimeoutError())


class ActiveAdventure:
    def __init__(
        self, ctx: Context, attack: int, defense: int, width: int = 15, height: int = 15
    ) -> None:
        self.ctx = ctx

        self.original_hp = attack * 100
        self.original_enemy_hp = attack * 10

        self.width = width
        self.height = height
        self.maze = Maze.generate(width=width, height=height)
        self.player_x = 0
        self.player_y = 0
        self.attack = attack
        self.defense = defense
        self.hp = attack * 100

        self.heal_hp = round(attack * 0.25) or 1
        self.min_dmg = round(attack * 0.5)
        self.max_dmg = round(attack * 1.5)

        self.enemy_hp: Optional[int] = None

        self.message: Optional[discord.Message] = None
        self.status_text: Optional[str] = _("The active adventure has started.")

    def move(self, action: ActiveAdventureAction) -> None:
        if action == ActiveAdventureAction.MoveNorth:
            self.player_y -= 1
        elif action == ActiveAdventureAction.MoveEast:
            self.player_x += 1
        elif action == ActiveAdventureAction.MoveSouth:
            self.player_y += 1
        elif action == ActiveAdventureAction.MoveWest:
            self.player_x -= 1

        self.maze.player = (self.player_x, self.player_y)

        if self.enemy_hp:
            status_1 = None
            status_2 = None

            enemy_action = random.choice(
                [
                    ActiveAdventureAction.AttackEnemy,
                    ActiveAdventureAction.Defend,
                    ActiveAdventureAction.Recover,
                ]
            )

            if enemy_action == ActiveAdventureAction.Recover:
                self.enemy_hp += self.heal_hp
                self.enemy_hp = 1000 if self.enemy_hp > 1000 else self.enemy_hp
                status_1 = ("The Enemy healed themselves for {hp} HP").format(
                    hp=self.heal_hp
                )

            if action == ActiveAdventureAction.Recover:
                self.hp += self.heal_hp
                self.hp = 1000 if self.hp > 1000 else self.hp
                status_2 = _("You healed yourself for {hp} HP").format(hp=self.heal_hp)

            if (
                enemy_action == ActiveAdventureAction.AttackEnemy
                and action == ActiveAdventureAction.Defend
            ) or (
                enemy_action == ActiveAdventureAction.Defend
                and action == ActiveAdventureAction.AttackEnemy
            ):
                status_1 = _("Attack blocked.")
            else:
                if enemy_action == ActiveAdventureAction.AttackEnemy:
                    eff = random.randint(self.min_dmg, self.max_dmg)
                    self.hp -= eff
                    status_1 = _("The Enemy hit you for {dmg} damage").format(dmg=eff)
                if action == ActiveAdventureAction.AttackEnemy:
                    self.enemy_hp -= self.attack
                    status_2 = _("You hit the enemy for {dmg} damage").format(
                        dmg=self.attack
                    )

            if status_1 and status_2:
                self.status_text = f"{status_1}\n{status_2}"
            elif status_1:
                self.status_text = status_1
            elif status_2:
                self.status_text = status_2

    async def reward(self, treasure: bool = True) -> int:
        val = self.attack + self.defense
        if treasure:
            money = random.randint(val, val * 25)
        else:
            # The adventure end reward
            money = random.randint(val * 5, val * 100)
        async with self.ctx.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                self.ctx.author.id,
            )
            await self.ctx.bot.log_transaction(
                self.ctx,
                from_=1,
                to=self.ctx.author.id,
                subject="money",
                data={"Amount": money},
                conn=conn,
            )

        return money

    async def run(self) -> None:
        while not self.is_at_exit and self.hp > 0:
            try:
                move = await self.get_move()
            except asyncio.TimeoutError:
                return await self.message.edit(content=_("Timed out."))

            # Reset status message since it'll change now
            self.status_text = None

            self.move(move)

            if self.enemy_hp is not None and self.enemy_hp <= 0:
                self.status_text = _("You defeated the enemy.")
                self.enemy_hp = None
                self.cell.enemy = False

            # Handle special cases of cells

            if self.cell.trap:
                damage = random.randint(self.original_hp // 10, self.original_hp // 8)
                self.hp -= damage
                self.status_text = _(
                    "You stepped on a trap and took {damage} damage!"
                ).format(damage=damage)
                self.cell.trap = False
            elif self.cell.treasure:
                money_rewarded = await self.reward()
                self.status_text = _(
                    "You found a treasure with **${money}** inside!"
                ).format(money=money_rewarded)
                self.cell.treasure = False
            elif self.cell.enemy and self.enemy_hp is None:
                self.enemy_hp = self.original_enemy_hp

        if self.hp <= 0:
            await self.message.edit(content=_("You died."))
            return

        money_rewarded = await self.reward(treasure=False)

        await self.message.edit(
            content=_(
                "You have reached the exit and were rewarded **${money}** for getting"
                " out!"
            ).format(money=money_rewarded),
            view=None,
        )

    @property
    def player_hp_bar(self) -> str:
        fields = int(self.hp / self.original_hp * 10)
        return f"[{'▯' * fields}{'▮' * (10 - fields)}]"

    @property
    def enemy_hp_bar(self) -> str:
        fields = int(self.enemy_hp / self.original_enemy_hp * 10)
        return f"[{'▯' * fields}{'▮' * (10 - fields)}]"

    async def get_move(self) -> ActiveAdventureAction:
        explanation_text = _("`@` - You, `!` - Enemy, `*` - Treasure")

        if self.enemy_hp is None:
            hp_text = _("You are on {hp} HP").format(hp=self.hp)

            if self.status_text is not None:
                text = f"{self.status_text}```\n{self.maze}\n```\n{explanation_text}\n{hp_text}"
            else:
                text = f"```\n{self.maze}\n```\n{explanation_text}\n{hp_text}"
        else:
            enemy = _("Enemy")
            hp = _("HP")
            fight_status = f"""```
{self.ctx.disp}
{"-" * len(self.ctx.disp)}
{self.player_hp_bar}  {self.hp} {hp}

{enemy}
{"-" * len(enemy)}
{self.enemy_hp_bar}  {self.enemy_hp} {hp}
```"""

            if self.status_text is not None:
                text = f"{self.status_text}```\n{self.maze}\n```\n{explanation_text}\n{fight_status}"
            else:
                text = f"```\n{self.maze}\n```\n{explanation_text}\n{fight_status}"

        possible = set()

        if self.enemy_hp is not None:
            possible.add(ActiveAdventureAction.AttackEnemy)
            possible.add(ActiveAdventureAction.Defend)
            possible.add(ActiveAdventureAction.Recover)
        else:
            free = self.free
            if "n" in free:
                possible.add(ActiveAdventureAction.MoveNorth)
            if "e" in free:
                possible.add(ActiveAdventureAction.MoveEast)
            if "s" in free:
                possible.add(ActiveAdventureAction.MoveSouth)
            if "w" in free:
                possible.add(ActiveAdventureAction.MoveWest)

        future = asyncio.Future()
        view = ActiveAdventureDirectionView(self.ctx.author, future, possible)

        if self.message:
            await self.message.edit(content=text, view=view)
        else:
            self.message = await self.ctx.send(content=text, view=view)

        return await future

    @property
    def free(self) -> set[DIRECTION]:
        return ALL_DIRECTIONS - self.cell.walls

    @property
    def is_at_exit(self) -> bool:
        return self.player_x == self.width - 1 and self.player_y == self.height - 1

    @property
    def cell(self) -> Cell:
        return self.maze[self.player_x, self.player_y]


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
            Your chances are determined by your equipped items, race and class bonuses, your level and your God-given luck."""
        )
        damage, defense = await self.bot.get_damage_armor_for(ctx.author)
        level = rpgtools.xptolevel(ctx.character_data["xp"])
        luck_booster = await self.bot.get_booster(ctx.author, "luck")

        chances = []
        for adv in range(1, 31):
            success = rpgtools.calcchance(
                damage,
                defense,
                adv,
                int(level),
                ctx.character_data["luck"],
                booster=luck_booster,
                returnsuccess=False,
            )
            chances.append(success)

        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/genadventures",
            json={"percentages": chances},
        ) as r:
            images = await r.json()

        pages = [
            discord.Embed().set_image(
                url=f"https://image-renderer.idlerpg.xyz/?image={key}"
            )
            for key in images
        ]

        await self.bot.paginator.Paginator(extras=pages).paginate(ctx)

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
        if adventure_number > rpgtools.xptolevel(ctx.character_data["xp"]):
            return await ctx.send(
                _("You must be on level **{level}** to do this adventure.").format(
                    level=adventure_number
                )
            )
        time = timedelta(hours=adventure_number)

        if buildings := await self.bot.get_city_buildings(ctx.character_data["guild"]):
            time -= time * (buildings["adventure_building"] / 100)
        if user_rank := await self.bot.get_donator_rank(ctx.author.id):
            if user_rank >= DonatorRank.emerald:
                time = time * 0.75
            elif user_rank >= DonatorRank.gold:
                time = time * 0.9
            elif user_rank >= DonatorRank.silver:
                time = time * 0.95
        if await self.bot.get_booster(ctx.author, "time"):
            time = time / 2
        await self.bot.start_adventure(ctx.author, adventure_number, time)

        async with self.bot.pool.acquire() as conn:
            remind_adv = await conn.fetchval(
                'SELECT "adventure_reminder" FROM user_settings WHERE "user"=$1;',
                ctx.author.id,
            )
            if remind_adv:
                subject = f"{adventure_number}"
                finish_time = datetime.utcnow() + time
                await self.bot.cogs["Scheduling"].create_reminder(
                    subject,
                    ctx,
                    finish_time,
                    partial(
                        self.bot.cogs["Scheduling"]._remind_adventure,
                        ctx.author.id,
                        ctx.channel.id,
                        subject,
                    ),
                    conn=conn,
                    type="adventure",
                )

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
            """Active adventures will put you into a randomly generated maze. You will begin in the top left corner and your goal is to find the exit in the bottom right corner.
            You control your character with the arrow buttons below the message.

            You have a fixed amount of HP based on your items. The adventure ends when you find the exit or your HP drop to zero.
            You can lose HP by getting damaged by traps or enemies.

            The maze contains safe spaces and treasures but also traps and enemies.
            Each space has a 10% chance of being a trap. If a space does not have a trap, it has a 10% chance of having an enemy.
            Each maze has 5 treasure chests.

            Traps can damage you from 1/10 of your total HP to up to 1/8 of your total HP.
            Enemy damage is based on your own damage. During enemy fights, you can attack (⚔️), defend (🛡️) or recover HP (❤️)
            Treasure chests can have gold up to 25 times your attack + defense.

            If you reach the end, you will receive a special treasure with gold up to 100 times your attack + defense.

            (This command has a cooldown of 30 minutes)"""
        )
        if not await ctx.confirm(
            _(
                "You are going to be in a labyrinth. There are enemies,"
                " treasures and hidden traps. Reach the exit in the bottom right corner"
                " for a huge extra bonus!\nAre you ready?\n\nTip: Use a silent channel"
                " for this, you may want to read all the messages I will send."
            )
        ):
            return

        attack, defense = await self.bot.get_damage_armor_for(ctx.author)

        await ActiveAdventure(ctx, int(attack), int(defense), width=12, height=12).run()

    @has_char()
    @has_adventure()
    @commands.command(aliases=["s"], brief=_("Checks your adventure status."))
    @locale_doc
    async def status(self, ctx):
        _(
            """Checks the remaining time of your adventures, or if you survived or died. Your chance is checked here, not in `{prefix}adventure`.
            Your chances are determined by your equipped items, race and class bonuses, your level, God-given luck and active luck boosters.

            If you are in an alliance which owns a city with an adventure building, your chance will be increased by 1% per building level.

            If you survive on your adventure, you will receive gold up to the adventure number times 60, XP up to 500 times the adventure number and either a loot or gear item.
            The chance of loot is dependent on the adventure number and whether you use the Ritualist class, [check our wiki](https://wiki.idlerpg.xyz/index.php?title=Loot) for the exact chances.

            God given luck affects the amount of gold and the gear items' damage/defense and value.

            If you are in a guild, its guild bank will receive 10% of the amount of gold extra.
            If you are married, your partner will receive a portion of your gold extra as well, [check the wiki](https://wiki.idlerpg.xyz/index.php?title=Family#Adventure_Bonus) for the exact portion."""
        )
        num, time, done = ctx.adventure_data

        if not done:
            # TODO: Embeds ftw
            return await ctx.send(
                embed=discord.Embed(
                    title=_("Adventure Status"),
                    description=_(
                        "You are currently on an adventure with difficulty"
                        " **{difficulty}**.\nTime until it completes:"
                        " **{time_left}**\nAdventure name: **{adventure}**"
                    ).format(
                        difficulty=num,
                        time_left=time,
                        adventure=ADVENTURE_NAMES[num],
                    ),
                    colour=self.bot.config.game.primary_colour,
                )
            )

        damage, armor = await self.bot.get_damage_armor_for(ctx.author)

        luck_booster = await self.bot.get_booster(ctx.author, "luck")
        current_level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        luck_multiply = ctx.character_data["luck"]
        if buildings := await self.bot.get_city_buildings(ctx.character_data["guild"]):
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
            return await ctx.send(
                embed=discord.Embed(
                    title=_("Adventure Failed"),
                    description=_("You died on your mission. Try again!"),
                    colour=0xFF0000,
                )
            )

        gold = round(random.randint(20 * num, 60 * num) * luck_multiply)

        if await self.bot.get_booster(ctx.author, "money"):
            gold = int(gold * 1.25)

        xp = random.randint(250 * num, 500 * num)
        chance_of_loot = 5 if num == 1 else 5 + 1.5 * num

        classes = [class_from_string(c) for c in ctx.character_data["class"]]
        if any(c.in_class_line(Ritualist) for c in classes if c):
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
                    conn=conn,
                )
                storage_type = "inventory"

            else:
                item = items.get_item()
                await conn.execute(
                    'INSERT INTO loot ("name", "value", "user") VALUES ($1, $2, $3);',
                    item["name"],
                    item["value"],
                    ctx.author.id,
                )
                storage_type = "loot"

            if guild := ctx.character_data["guild"]:
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

            if partner := ctx.character_data["marriage"]:
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
                conn=conn,
            )

            # TODO: Embeds ftw
            await ctx.send(
                embed=discord.Embed(
                    title=_("Adventure Completed"),
                    description=_(
                        "You have completed your adventure and received **${gold}** as"
                        " well as a new item:\n**{item}** added to your"
                        " `{prefix}{storage_type}`\nType: **{type}**\n{stat}Value:"
                        " **{value}**\nExperience gained: **{xp}**."
                    ).format(
                        gold=gold,
                        type=_("Loot item") if storage_type == "loot" else item["type"],
                        item=item["name"],
                        stat=""
                        if storage_type == "loot"
                        else _("Damage: **{damage}**\n").format(damage=item["damage"])
                        if item["damage"]
                        else _("Armor: **{armor}**\n").format(armor=item["armor"]),
                        value=item["value"],
                        prefix=ctx.prefix,
                        storage_type=storage_type,
                        xp=xp,
                    ),
                    colour=0x00FF00,
                )
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

        reminder = await self.bot.pool.fetchrow(
            'DELETE FROM reminders WHERE "user"=$1 AND "type"=$2 RETURNING "id", "internal_id";',
            ctx.author.id,
            "adventure",
        )
        if reminder:
            fake_task = Task(0, reminder["internal_id"], 0)
            self.bot.schedule_manager.cancel(fake_task)

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
        deaths, completed = (
            ctx.character_data["deaths"],
            ctx.character_data["completed"],
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
