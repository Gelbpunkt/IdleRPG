"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import copy
import random

import discord
from discord.ext import commands


class GameBase:
    def __init__(self, ctx, players: list):
        self.players = players
        self.ctx = ctx

    def chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i : i + n]

    def rand_chunks(self, l):
        idx = 0
        for i in range(0, len(l)):
            if i < idx:
                continue
            num = random.randint(1, 4)
            yield l[i : i + num]
            idx += num

    def nice_join(self, l):
        return f"{', '.join(l[:-1])} and {l[-1]}"

    async def get_inputs(self):
        all_actions = [
            (
                "Gather as much food as you can",
                "gathers as much food as they can",
                None,
            ),
            ("Grab a backpack and retreat", "grabs a backpack and retreats", "leave"),
            ("Take a pistol and suicide", "gives themselves the bullet", "leave"),
            ("Ram a knife in your body", "commits suicide with a knife", "leave"),
            ("Run away from the Curnocopia", "runs away from the Cornucopia", None),
            ("Search for a pair of Explosives", "finds a bag full of explosives", None),
            ("Look for water", "finds a canteen full of water", None),
            ("Get a first aid kit", "clutches a first aid kit and runs away", None),
            ("Grab a backpack", "grabs a backpack, not realizing it is empty", None),
            ("Try to assault USER", "kills USER", ("kill", "USER")),
            (
                "Kill USER at the water",
                "assaults USER while they were drinking water at the river",
                ("kill", "USER"),
            ),
            ("Try to hide some landmines", "hides landmines at a few locations", None),
            ("Take a bath", "baths in the water and enjoys the silence", None),
        ]
        team_actions = [
            ("kill USER", ("kill", "USER")),
            ("grill at the fireplace and tell each other spooky stories", None),
            ("annoy USER", "user"),
            ("kill themselves by walking into a landmine", "killall"),
            ("have a small party and get drunk", None),
            ("watch animes together", None),
            ("enjoy the silence", None),
            ("attempt to kill USER but fail", "user"),
            ("watch a movie together", "user"),
            ("track down USER and kill them silently", ("kill", "USER")),
        ]
        team_actions_2 = [
            ("kill themselves by walking into a landmine", "killall"),
            ("decide they want out of here and commit suicide", "killall"),
            ("watch a movie together", None),
            ("dance YMCA together", None),
            ("sing songs together", None),
            ("have a nice romantic evening", None),
            ("watch the others being dumb", None),
            ("kiss in the moonlight", None),
            (
                "watch a movie together when USER suddely gets shot by a stranger",
                ("killtogether", "USER"),
            ),
        ]
        user_actions = []
        status = await self.ctx.send(f"**Round {self.round}**", delete_after=60)
        killed_this_round = []
        for p in self.rand_chunks(self.players):
            if len(p) == 1:
                try:
                    await status.edit(
                        content=f"{status.content}\nLetting {p[0]} choose their action..."
                    )
                except discord.errors.NotFound:
                    status = await self.ctx.send(
                        f"**Round {self.round}**\nLetting {p[0]} choose their action...",
                        delete_after=60,
                    )
                actions = random.sample(all_actions, 3)
                possible_kills = [
                    item
                    for item in self.players
                    if item not in killed_this_round and item != p[0]
                ]
                if len(possible_kills) > 0:
                    kill = random.choice(possible_kills)
                    okay = True
                else:
                    kill = random.choice([i for i in self.players if i != p[0]])
                    okay = False
                actions2 = []
                for a, b, c in actions:
                    if c == ("kill", "USER"):
                        actions2.append(
                            (
                                a.replace("USER", kill.name),
                                b.replace("USER", kill.name),
                                ("kill", kill),
                            )
                        )
                    else:
                        actions2.append((a, b, c))
                actions_desc = [a[0] for a in actions2]
                try:
                    action = actions2[
                        await self.ctx.bot.paginator.Choose(
                            entries=actions_desc,
                            return_index=True,
                            title="Choose an action",
                        ).paginate(self.ctx, location=p[0])
                    ]
                except (self.ctx.bot.paginator.NoChoice, discord.Forbidden):
                    await self.ctx.send(
                        f"I couldn't send a DM to {p[0].mention}! (This is a known bug if your reaction didn't do anything) Choosing random action..."
                    )
                    action = random.choice(actions2)
                if okay or (not okay and isinstance(action[2], tuple)):
                    user_actions.append((p[0], action[1]))
                else:
                    user_actions.append((p[0], f"attempts to kill {kill} but fails"))
                if action[2]:
                    if action[2] == "leave":
                        killed_this_round.append(p[0])
                    else:
                        if okay:
                            killed_this_round.append(action[2][1])
                try:
                    await status.edit(
                        content=f"{status.content}\nLetting {p[0]} choose their action... Done"
                    )
                except discord.errors.NotFound:
                    status = await self.ctx.send(
                        f"**Round {self.round}**\nLetting {p[0]} choose their action... Done",
                        delete_after=60,
                    )
            else:
                if len(p) > 2:
                    action = random.choice(team_actions)
                else:
                    action = random.choice(team_actions_2)
                possible_kills = [item for item in p if item not in killed_this_round]
                target = random.choice(possible_kills)
                users = [u for u in p if u != target]
                if not action[1]:
                    user_actions.append(
                        (self.nice_join([u.name for u in p]), action[0])
                    )
                elif action[1] == "user":
                    user_actions.append(
                        (
                            self.nice_join([u.name for u in users]),
                            action[0].replace("USER", target.name),
                        )
                    )
                elif action[1] == "killall":
                    user_actions.append(
                        (self.nice_join([u.name for u in p]), action[0])
                    )
                    killed_this_round.extend(p)
                else:
                    if action[1][0] == "kill":
                        user_actions.append(
                            (
                                self.nice_join([u.name for u in users]),
                                action[0].replace("USER", target.name),
                            )
                        )
                    elif action[1][0] == "killtogether":
                        user_actions.append(
                            (
                                self.nice_join([u.name for u in p]),
                                action[0].replace("USER", target.name),
                            )
                        )
                    killed_this_round.append(target)
        await asyncio.sleep(2)
        for p in killed_this_round:
            try:
                self.players.remove(p)
            except ValueError:
                pass
        await self.ctx.send(
            "\n".join([f"{u} {a}" for u, a in user_actions]), delete_after=60
        )
        self.round += 1

    async def send_cast(self):
        cast = copy.copy(self.players)
        random.shuffle(cast)
        cast = list(self.chunks(cast, 2))
        self.cast = cast
        cast = "\n".join(
            [
                f"Team #{i}: {team[0].mention} {team[1].mention}"
                if len(team) == 2
                else f"Team #{i}: {team[0].mention}"
                for i, team in enumerate(cast, start=1)
            ]
        )
        await self.ctx.send(f"**The cast**\n{cast}")

    async def main(self):
        self.round = 1
        await self.send_cast()
        while len(self.players) > 1:
            await self.get_inputs()
            await asyncio.sleep(3)
        if len(self.players) == 1:
            await self.ctx.send(
                f"This hunger game's winner is {self.players[0].mention}!"
            )
        else:
            await self.ctx.send("Everyone died!")


class HungerGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command()
    async def hungergames(self, ctx):
        if self.games.get(ctx.channel.id):
            return await ctx.send("There is already a game in here!")
        players = [ctx.author]
        msg = await ctx.send(
            f"{ctx.author.mention} started a game of Hunger Games! React with :shallow_pan_of_food: to join the game! **1 joined**"
        )
        await msg.add_reaction("\U0001f958")

        def check(reaction, user):
            return (
                user not in players and reaction.message.id == msg.id and not user.bot
            )

        self.games[ctx.channel.id] = "forming"

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=30
                )
            except asyncio.TimeoutError:
                break
            players.append(user)
            await msg.edit(
                content=f"{ctx.author.mention} started a game of Hunger Games! React with :shallow_pan_of_food: to join the game! **{len(players)} joined**"
            )

        if len(players) < 2:
            del self.games[ctx.channel.id]
            return await ctx.send("Not enough players joined...")
            
        game = GameBase(ctx, players=players)
        self.games[ctx.channel.id] = game
        await game.main()
        del self.games[ctx.channel.id]


def setup(bot):
    bot.add_cog(HungerGames(bot))
