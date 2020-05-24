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

import discord

from discord.ext import commands

from utils.i18n import _, locale_doc
from utils.werewolf import Game


class Werewolf(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command(aliases=["ww"], brief=_("Play a roumd of Werewolf"))
    @locale_doc
    async def werewolf(self, ctx, mode: str.title = "Classic"):
        _(
            """`[mode]` - The mode to play, see below for more info; defaults to Classic

            Starts a game of Werewolf.
            Game modes:
                Classic - Play the classic werewolf game. (This is the default)
                Blitz   - In Blitz mode, all action timers are limited to 30 seconds and number of days to play is dependent on the number of players plus 3 days. This means not killing anyone every night or every election will likely end the game with no winners.

            This game is mainly based around trust. The goal of the game is to find the werewolves in your community and lynch them."""
        )
        if mode not in ["Classic", "Blitz"]:
            return await ctx.send(
                _("Invalid game mode. View the help on this command.")
            )
        if self.games.get(ctx.channel.id):
            return await ctx.send(_("There is already a game in here!"))
        if ctx.channel.id == self.bot.config.official_tournament_channel_id:
            id_ = await self.bot.start_joins()
            await ctx.send(
                f"{ctx.author.mention} started a mass-game of Werewolf! Go to"
                f" https://join.travitia.xyz/{id_} to join in the next 10 minutes."
            )
            await asyncio.sleep(60 * 10)
            players = await self.bot.get_joins(id_)
        else:
            players = [ctx.author]
            text = _(
                "{author} started a game of Werewolf! React with :wolf: to join the"
                " game! **{num} joined**"
            )
            msg = await ctx.send(text.format(author=ctx.author.mention, num=1))
            await msg.add_reaction("\U0001f43a")

            def check(reaction, user):
                return (
                    user not in players
                    and reaction.message.id == msg.id
                    and reaction.emoji == "\U0001f43a"
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

            # Check for not included participants
            msg = await ctx.channel.fetch_message(msg.id)
            for reaction in msg.reactions:
                if reaction.emoji == "\U0001f43a":
                    async for user in reaction.users():
                        if user != ctx.me and user not in players:
                            players.append(user)
                    break

        if len(players) < 5:
            del self.games[ctx.channel.id]
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Not enough players joined..."))

        game = Game(ctx, players, mode)
        self.games[ctx.channel.id] = game
        try:
            await game.run()
        except Exception as e:
            await ctx.send(
                _("An error happened during the Werewolf. Please try again!")
            )
            del self.games[ctx.channel.id]
            raise e
        try:
            del self.games[ctx.channel.id]
        except KeyError:  # got stuck in between
            pass

    @commands.command(brief=_("Check your werewolf role"))
    @locale_doc
    async def role(self, ctx):
        _(
            """Check your role in the Werewolf game and have the bot DM it to you.

            You must be part of the ongoing game to get your role."""
        )
        game = self.games.get(ctx.channel.id)
        if not game:
            return await ctx.send(
                f"There is no werewolf game in this channel! {ctx.author.mention}"
            )
        if game == "forming":
            return await ctx.send(
                f"The game has yet to be started {ctx.author.mention}."
            )
        if ctx.author not in [player.user for player in game.players]:
            return await ctx.send(f"You're not in the game {ctx.author.mention}.")
        else:
            player = discord.utils.get(game.players, user=ctx.author)
            if player is None:
                return await ctx.send(
                    f"You asked for your role in {ctx.channel.mention}"
                    " but your info couldn't be found."
                )
            else:
                try:
                    await ctx.author.send(
                        f"Checking your role in {ctx.channel.mention}... You are a"
                        " **{role_name}**!{initial_role_info}".format(
                            player_name=player.user.mention,
                            role_name=player.role.name.title().replace("_", " "),
                            initial_role_info=(
                                f" A **{player.initial_role.name.title().replace('_', ' ')}**"
                                " initially."
                            )
                            if player.role != player.initial_role
                            else "",
                        )
                    )
                    await player.send_information()
                    return await ctx.send(
                        f"I sent a DM containing your role info, {ctx.author.mention}."
                    )
                except discord.Forbidden:
                    return await ctx.send(
                        f"I couldn't send a DM to you {ctx.author.mention}."
                    )


def setup(bot):
    bot.add_cog(Werewolf(bot))
