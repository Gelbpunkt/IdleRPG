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

from typing import Optional

import chess
import discord

from discord.ext import commands

from classes.converters import IntFromTo
from utils.chess import ChessGame


class Chess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.matches = {}
        bot.loop.create_task(self.initialize())

    async def initialize(self):
        transport, self.engine = await chess.engine.popen_uci("/idlerpg/stockfish")

    @commands.group(invoke_without_command=True)
    @locale_doc
    async def chess(self, ctx):
        _(
            """IdleRPG's Chess system. You can play against AI or other users and gain ELO."""
        )
        await ctx.send(
            _("Please use `{prefix}chess match` to play!").format(prefix=ctx.prefix)
        )

    @chess.group(invoke_without_command=True)
    async def match(
        self,
        ctx,
        enemy: Optional[discord.Member] = None,
        difficulty: IntFromTo(1, 10) = 3,
    ):
        emojis = {"\U00002b1c": "white", "\U00002b1b": "black"}
        msg = await ctx.send(_("Please choose the colour you want to take."))
        await msg.add_reaction("\U00002b1c")
        await msg.add_reaction("\U00002b1b")

        def check(r, u):
            return u == ctx.author and r.message.id == msg.id and str(r.emoji) in emojis

        try:
            r, u = await self.bot.wait_for("reaction_add", timeout=30, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(_("You took too long to choose a side."))

        side = emojis[str(r.emoji)]

        if enemy is not None:
            if not await ctx.confirm(
                _(
                    "{user}, you have been challenged to a chess match by {author}. They will be {color}. Do you accept?"
                ).format(user=enemy.mention, author=ctx.author.mention, color=side),
                user=enemy,
            ):
                return await ctx.send(
                    _("{user} rejected the chess match.").format(user=enemy)
                )

        if self.matches.get(ctx.channel.id):
            return await ctx.send(_("Wait for the match here to end."))
        self.matches[ctx.channel.id] = ChessGame(
            ctx, ctx.author, side, enemy, difficulty
        )
        try:
            await self.matches[ctx.channel.id].run()
        except Exception as e:
            del self.matches[ctx.channel.id]
            raise e
        del self.matches[ctx.channel.id]

    @match.command()
    async def moves(self, ctx):
        game = self.matches.get(ctx.channel.id)
        if not game:
            return await ctx.send("No game here.")
        moves = "\n".join(
            [
                (f"{i + 1}. {j[0]} - {j[1]}" if len(j) == 2 else f"{i + 1}. {j[0]} - ?")
                for i, j in enumerate(game.history)
            ]
        )
        await ctx.send(moves)

    def cog_unload(self):
        self.bot.loop.create_task(self.engine.quit())


def setup(bot):
    bot.add_cog(Chess(bot))
