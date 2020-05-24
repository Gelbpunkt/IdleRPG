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
import copy

import discord

from discord.ext import commands

from cogs.help import chunks
from utils import random
from utils.i18n import _, locale_doc
from utils.misc import nice_join


class GameBase:
    def __init__(self, ctx, players: list):
        self.players = players
        self.ctx = ctx

    def rand_chunks(self, iterable):
        idx = 0
        for i in range(0, len(iterable)):
            if i < idx:
                continue
            num = random.randint(1, 4)
            yield iterable[i : i + num]
            idx += num

    async def get_inputs(self):
        all_actions = [
            (
                _("Gather as much food as you can"),
                _("gathers as much food as they can"),
                None,
            ),
            (
                _("Grab a backpack and retreat"),
                _("grabs a backpack and retreats"),
                "leave",
            ),
            (_("Take a pistol and suicide"), _("gives themselves the bullet"), "leave"),
            (_("Ram a knife in your body"), _("commits suicide with a knife"), "leave"),
            (
                _("Run away from the Curnocopia"),
                _("runs away from the Cornucopia"),
                None,
            ),
            (
                _("Search for a pair of Explosives"),
                _("finds a bag full of explosives"),
                None,
            ),
            (_("Look for water"), _("finds a canteen full of water"), None),
            (
                _("Get a first aid kit"),
                _("clutches a first aid kit and runs away"),
                None,
            ),
            (
                _("Grab a backpack"),
                _("grabs a backpack, not realizing it is empty"),
                None,
            ),
            (_("Try to assault USER"), _("kills USER"), ("kill", "USER")),
            (
                _("Kill USER at the water"),
                _("assaults USER while they were drinking water at the river"),
                ("kill", "USER"),
            ),
            (
                _("Try to hide some landmines"),
                _("hides landmines at a few locations"),
                None,
            ),
            (_("Take a bath"), _("baths in the water and enjoys the silence"), None),
        ]
        team_actions = [
            (_("kill USER"), ("kill", "USER")),
            (_("grill at the fireplace and tell each other spooky stories"), None),
            (_("annoy USER"), "user"),
            (_("kill themselves by walking into a landmine"), "killall"),
            (_("have a small party and get drunk"), None),
            (_("watch animes together"), None),
            (_("enjoy the silence"), None),
            (_("attempt to kill USER but fail"), "user"),
            (_("watch a movie together"), "user"),
            (_("track down USER and kill them silently"), ("kill", "USER")),
        ]
        team_actions_2 = [
            (_("kill themselves by walking into a landmine"), "killall"),
            (_("decide they want out of here and commit suicide"), "killall"),
            (_("watch a movie together"), None),
            (_("dance YMCA together"), None),
            (_("sing songs together"), None),
            (_("have a nice romantic evening"), None),
            (_("watch the others being dumb"), None),
            (_("kiss in the moonlight"), None),
            (
                _("watch a movie together when USER suddenly gets shot by a stranger"),
                ("killtogether", "USER"),
            ),
        ]
        user_actions = []
        roundtext = _("**Round {round}**")
        status = await self.ctx.send(
            roundtext.format(round=self.round), delete_after=60
        )
        killed_this_round = []
        for p in self.rand_chunks(self.players):
            if len(p) == 1:
                text = _("Letting {user} choose their action...").format(user=p[0])
                try:
                    await status.edit(content=f"{status.content}\n{text}")
                except discord.errors.NotFound:
                    status = await self.ctx.send(
                        f"{roundtext.format(round=self.round)}\n{text}", delete_after=60
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
                            title=_("Choose an action"),
                        ).paginate(self.ctx, location=p[0])
                    ]
                except (
                    self.ctx.bot.paginator.NoChoice,
                    discord.Forbidden,
                    asyncio.TimeoutError,
                ):
                    await self.ctx.send(
                        _(
                            "I couldn't send a DM to {user}! Choosing random action..."
                        ).format(user=p[0]),
                        delete_after=30,
                    )
                    action = random.choice(actions2)
                if okay or (not okay and isinstance(action[2], tuple)):
                    user_actions.append((p[0], action[1]))
                else:
                    user_actions.append(
                        (p[0], _("attempts to kill {user} but fails").format(user=kill))
                    )
                if action[2]:
                    if action[2] == "leave":
                        killed_this_round.append(p[0])
                    else:
                        if okay:
                            killed_this_round.append(action[2][1])
                text = _("Done")
                try:
                    await status.edit(content=f"{status.content} {text}")
                except discord.errors.NotFound:
                    pass
            else:
                possible_kills = [item for item in p if p not in killed_this_round]
                if len(possible_kills) > 0:
                    target = random.choice(possible_kills)
                else:
                    target = None
                if len(p) > 2:
                    action = random.choice(team_actions)
                else:
                    action = random.choice(team_actions_2)
                users = [u for u in p if u != target]
                if not action[1]:
                    user_actions.append((nice_join([u.name for u in p]), action[0]))
                elif not target:  # fix
                    user_actions.append(
                        (nice_join([u.name for u in p]), _("do nothing."))
                    )
                elif action[1] == "user":
                    user_actions.append(
                        (
                            nice_join([u.name for u in users]),
                            action[0].replace("USER", target.name),
                        )
                    )
                elif action[1] == "killall":
                    user_actions.append((nice_join([u.name for u in p]), action[0]))
                    killed_this_round.extend(p)
                else:
                    if action[1][0] == "kill":
                        user_actions.append(
                            (
                                nice_join([u.name for u in users]),
                                action[0].replace("USER", target.name),
                            )
                        )
                    elif action[1][0] == "killtogether":
                        user_actions.append(
                            (
                                nice_join([u.name for u in p]),
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
        paginator = commands.Paginator(prefix="", suffix="")
        for u, a in user_actions:
            paginator.add_line(f"{u} {a}")
        for page in paginator.pages:
            await self.ctx.send(page, delete_after=60)
        self.round += 1

    async def send_cast(self):
        cast = copy.copy(self.players)
        cast = random.shuffle(cast)
        cast = list(chunks(cast, 2))
        self.cast = cast
        text = _("Team")
        paginator = commands.Paginator(prefix="", suffix="")
        paginator.add_line(_("**The cast**"))
        for i, team in enumerate(cast, start=1):
            if len(team) == 2:
                paginator.add_line(f"{text} #{i}: {team[0].mention} {team[1].mention}")
            else:
                paginator.add_line(f"{text} #{i}: {team[0].mention}")
        for page in paginator.pages:
            await self.ctx.send(page)

    async def main(self):
        self.round = 1
        await self.send_cast()
        while len(self.players) > 1:
            await self.get_inputs()
            await asyncio.sleep(3)
        if len(self.players) == 1:
            await self.ctx.send(
                _("This hunger game's winner is {winner}!").format(
                    winner=self.players[0].mention
                )
            )
        else:
            await self.ctx.send(_("Everyone died!"))


class HungerGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command(aliases=["hg"], brief=_("Play a game of the hunger games"))
    @locale_doc
    async def hungergames(self, ctx):
        _(
            """Starts a game of the hunger games (starts a hunger game?)

            Players will be able to join via the :shallow_pan_of_food: emoji.
            The game is controlled via both random actions and possibly chosen actions.
            Players may choose an action if they get a direct message from the bot. If no action is chosen by the player, the bot chooses one for them.

            Not every player will get the eopportunity to choose an action. Sometimes nobody gets to choose, so don't be discouraged. """
        )
        if self.games.get(ctx.channel.id):
            return await ctx.send(_("There is already a game in here!"))

        if ctx.channel.id == self.bot.config.official_tournament_channel_id:
            id_ = await self.bot.start_joins()
            await ctx.send(
                f"{ctx.author.mention} started a mass-game of Hunger Games! Go to"
                f" https://join.travitia.xyz/{id_} to join in the next 10 minutes."
            )
            await asyncio.sleep(60 * 10)
            players = await self.bot.get_joins(id_)
        else:
            players = [ctx.author]
            text = _(
                "{author} started a game of Hunger Games! React with"
                " :shallow_pan_of_food: to join the game! **{num} joined**"
            )
            msg = await ctx.send(text.format(author=ctx.author.mention, num=1))
            await msg.add_reaction("\U0001f958")

            def check(reaction, user):
                return (
                    user not in players
                    and reaction.message.id == msg.id
                    and reaction.emoji == "\U0001f958"
                    and not user.bot
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
                    content=text.format(author=ctx.author.mention, num=len(players))
                )

        if len(players) < 2:
            del self.games[ctx.channel.id]
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Not enough players joined..."))

        game = GameBase(ctx, players=players)
        self.games[ctx.channel.id] = game
        try:
            await game.main()
        except Exception:
            await ctx.send(
                _("An error happened during the hungergame. Please try again!")
            )
        try:
            del self.games[ctx.channel.id]
        except KeyError:  # got stuck in between
            pass


def setup(bot):
    bot.add_cog(HungerGames(bot))
