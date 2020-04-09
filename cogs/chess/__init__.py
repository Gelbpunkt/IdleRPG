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
        transport, self.engine = await chess.engine.popen_uci(
            "/idlerpg/stockfish"
        )

    @commands.group(invoke_without_command=True)
    async def match(
        self,
        ctx,
        enemy: Optional[discord.Member] = None,
        difficulty: IntFromTo(1, 10) = 3,
    ):
        if self.matches.get(ctx.channel.id):
            return await ctx.send(_("Wait for the match here to end."))
        self.matches[ctx.channel.id] = ChessGame(
            ctx, ctx.author, "white", enemy, difficulty
        )
        await self.matches[ctx.channel.id].run()
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
