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
import random

import discord

from utils.maze import Maze

direction_emojis = {
    "n": "\U00002b06",
    "e": "\U000027a1",
    "s": "\U00002b07",
    "w": "\U00002b05",
}
direction_emojis_inverse = {val: key for key, val in direction_emojis.items()}
direction_names = {"n": _("North"), "e": _("East"), "s": _("South"), "w": _("West")}
all_directions = set(direction_names.keys())


def free(cell):
    return all_directions - cell.walls


def fmt_direction(direction):
    return direction_names[direction]


class Castle:
    def __init__(self, bot):
        self.bot = bot
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    async def run(self):
        maze = Maze.generate(50, 50)
        for player in self.players:
            await self.bot.loop.create_task(player.run(maze, self.bot))


class Player:
    def __init__(self, user, stats):
        self.user = user
        self.hp = stats["hp"]
        self.attack = int(stats["damage"])
        self.defense = int(stats["armor"])
        self.x = random.randint(0, 40)
        self.y = random.randint(0, 40)
        self.maze = None
        self.msg = None
        self.bot = None

    @property
    def position(self):
        return self.maze[self.x, self.y]

    @property
    def at_end(self):
        return self.x == 49 and self.y == 49

    def move(self, direction):
        if direction == "n":
            self.y -= 1
        elif direction == "e":
            self.x += 1
        elif direction == "s":
            self.y += 1
        elif direction == "w":
            self.x -= 1

    def fake_move(self, direction):
        if direction == "n":
            return self.x, self.y - 1
        elif direction == "e":
            return self.x + 1, self.y
        elif direction == "s":
            return self.x, self.y + 1
        elif direction == "w":
            return self.x - 1, self.y

    async def get_move(self):
        possible = free(self.position)
        needed = [direction_emojis[direction] for direction in possible]
        for r in self.msg.reactions:
            if str(r.emoji) not in needed:
                await self.msg.remove_reaction(r, self.bot.user)
        for r in needed:
            if r not in [str(r.emoji) for r in self.msg.reactions]:
                await self.msg.add_reaction(r)
        else:
            for direction in possible:
                await self.msg.add_reaction(direction_emojis[direction])

        possible = [direction_emojis[i] for i in possible]
        r, u = await self.bot.wait_for_dms(
            "reaction_add",
            check={
                "emoji": {"name": possible},
                "user_id": self.user.id,
                "message_id": self.msg.id,
            },
            timeout=30,
        )

        return direction_emojis_inverse[str(r.emoji)]

    async def update(self):
        text = ""
        pos = self.position
        for direction in ("n", "e", "s", "w"):
            side = fmt_direction(direction)
            fake_x, fake_y = self.fake_move(direction)
            fake_cell = self.maze[fake_x, fake_y]
            if direction in pos.walls:
                text2 = _("To the {side} is a wall.").format(side=side)
            elif fake_cell.enemy:
                text2 = _("To the {side} is an enemy.").format(side=side)
            elif fake_cell.treasure:
                text2 = _("To the {side} is a treasure.").format(side=side)
            else:
                text2 = _("To the {side} is a floor.").format(side=side)
            text = f"{text}\n{text2}"

        text2 = _("You are on {hp} HP").format(hp=self.hp)
        text = f"{text}\n\n{text2}"

        if self.msg:
            await self.msg.edit(content=text)
        else:
            self.msg = await self.user.send(text)

    async def handle_specials(self):
        cell = self.position
        if cell.trap:
            damage = random.randint(30, 120) if random.randint(1, 3) == 1 else 1000
            await self.user.send(
                "You stepped on a trap and took {damage} damage!".format(damage=damage)
            )
            cell.trap = False  # Remove the trap
            self.hp -= damage
        elif cell.treasure:
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_magic"="crates_magic"+$1 WHERE "user"=$2;',
                1,
                self.user.id,
            )
            await self.user.send(
                "You found a treasure with {emote} inside!".format(
                    emote=self.bot.cogs["Crates"].emotes.magic
                )
            )
            cell.treasure = False
        elif cell.enemy:
            cell.enemy = False

            def to_bar(hp):
                fields = hp // 100
                return f"[{'▯' * fields}{'▮' * (10 - fields)}]"

            def is_valid_move(r, u):
                return (
                    r.message.id == self.msg.id
                    and u == self.user
                    and str(r.emoji) in emojis
                )

            emojis = {
                "\U00002694": "attack",
                "\U0001f6e1": "defend",
                "\U00002764": "recover",
            }
            enemy = _("Enemy")
            enemy_hp = 1000
            heal_hp = round(self.attack * 0.25) or 1
            min_dmg = round(self.attack * 0.5)
            max_dmg = round(self.attack * 1.5)
            status1 = _("The Fight started")
            status2 = ""

            for r in self.msg.reactions:
                await self.msg.remove_reaction(r, self.bot.user)
            for emoji in emojis:
                await self.msg.add_reaction(emoji)

            while enemy_hp > 0 and self.hp > 0:
                await self.msg.edit(
                    content=f"""\
```
{self.user.name}{" " * (38 - len(self.user.name) - len(enemy))}{enemy}
------------++++++++++++++------------
{to_bar(self.hp)}  {self.hp}  {enemy_hp}    {to_bar(enemy_hp)}

{status1}
{status2}
```"""
                )

                r, u = await self.bot.wait_for(
                    "reaction_add", check=is_valid_move, timeout=30
                )

                try:
                    await self.msg.remove_reaction(r, u)
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
                    self.hp += heal_hp
                    self.hp = 1000 if self.hp > 1000 else self.hp
                    status2 = _("You healed yourself for {hp} HP").format(hp=heal_hp)
                if (enemy_move == "attack" and player_move == "defend") or (
                    enemy_move == "defend" and player_move == "attack"
                ):
                    status1 = _("Attack blocked.")
                    status2 = ""
                if enemy_move == "attack" and player_move != "defend":
                    eff = random.randint(min_dmg, max_dmg)
                    self.hp -= eff
                    status1 = _("The Enemy hit you for {dmg} damage").format(dmg=eff)
                if player_move == "attack" and enemy_move != "defend":
                    enemy_hp -= self.attack
                    status2 = _("You hit the enemy for {dmg} damage").format(
                        dmg=self.attack
                    )

    async def run(self, maze, bot):
        self.maze = maze
        self.bot = bot
        while not self.at_end and self.hp > 0:
            await self.update()
            try:
                direction = await self.get_move()
            except asyncio.TimeoutError:
                return await self.msg.edit(content=_("Timed out."))
            self.move(direction)
            try:
                await self.handle_specials()
            except asyncio.TimeoutError:
                return await self.msg.edit(content=_("Timed out."))

        if self.hp <= 0:
            return await self.user.send("You died.")

        await self.user.send("You have reached the exit!")
