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

import chess.engine
import discord

from discord.ext import commands

from utils.chess import ChessGame, ProtocolAdapter
from utils.i18n import _, locale_doc


class Chess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.matches = {}
        bot.loop.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_ready()
        try:
            _, adapter = await self.bot.loop.create_connection(
                lambda: ProtocolAdapter(chess.engine.UciProtocol()), "127.0.0.1", 4000
            )
        except ConnectionRefusedError:
            print("FAILED to connect to stockfish backend, unloading chess cog...")
            self.bot.unload_extension("cogs.chess")
            return
        self.engine = adapter.protocol
        await self.engine.initialize()

    @commands.group(invoke_without_command=True)
    @locale_doc
    async def chess(self, ctx):
        _(
            """IdleRPG's Chess system. You can play against AI or other users and gain ELO."""
        )
        await ctx.send(
            _(
                "Please use `{prefix}chess match` to play.\nIf you want to play"
                " ELO-rated, you must use `{prefix}chess register` first."
            ).format(prefix=ctx.prefix)
        )

    @chess.command()
    @locale_doc
    async def register(self, ctx):
        _("""Register an ELO-rating eligible account for Idle's Chess.""")
        async with self.bot.pool.acquire() as conn:
            if await conn.fetchrow(
                'SELECT * FROM chess_players WHERE "user"=$1;', ctx.author.id
            ):
                return await ctx.send(_("You are already registered."))
            await conn.execute(
                'INSERT INTO chess_players ("user") VALUES ($1);', ctx.author.id
            )
        await ctx.send(
            _(
                "You have been registered with an ELO of 1000 as a default. Play"
                " matches to increase it!"
            )
        )

    @chess.command()
    @locale_doc
    async def elo(self, ctx):
        _("""Show your ELO and the best chess players.""")
        async with self.bot.pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM chess_players WHERE "user"=$1;', ctx.author.id
            )
            top_players = await conn.fetch(
                'SELECT * FROM chess_players ORDER BY "elo" DESC LIMIT 15;'
            )
            top_text = ""
            for idx, row in enumerate(top_players):
                user = await self.bot.get_user_global(row["user"]) or "Unknown Player"
                text = _("**{user}** with ELO **{elo}**").format(
                    user=user, elo=row["elo"]
                )
                top_text = f"{top_text}{idx + 1}. {text}\n"
            embed = discord.Embed(title=_("Chess ELOs")).add_field(
                name=_("Top 15"), value=top_text
            )
            if player:
                player_pos = await conn.fetchval(
                    "SELECT position FROM (SELECT chess_players.*, ROW_NUMBER()"
                    " OVER(ORDER BY chess_players.elo DESC) AS position FROM"
                    " chess_players) s WHERE s.user = $1 LIMIT 1;",
                    ctx.author.id,
                )
                text = _("**{user}** with ELO **{elo}**").format(
                    user=ctx.author, elo=player["elo"]
                )
                text = f"{player_pos}. {text}"
                embed.add_field(name=_("Your position"), value=text)
            await ctx.send(embed=embed)

    @chess.group(invoke_without_command=True)
    async def match(
        self, ctx, difficulty: Optional[int] = 3, enemy: discord.Member = None,
    ):
        _(
            """Starts a game of chess, either against a player or AI from difficulty 1 to 10."""
        )
        if enemy == ctx.author:
            return await ctx.send(_("You cannot play against yourself."))
        if difficulty < 1 or difficulty > 10:
            return await ctx.send(_("Difficulty may be 1-10."))
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

        await msg.delete()
        side = emojis[str(r.emoji)]

        if enemy is not None:
            async with self.bot.pool.acquire() as conn:
                player_elo = await conn.fetchval(
                    'SELECT elo FROM chess_players WHERE "user"=$1;', ctx.author.id
                )
                enemy_elo = await conn.fetchval(
                    'SELECT elo FROM chess_players WHERE "user"=$1;', enemy.id
                )
            if player_elo is not None and enemy_elo is not None:
                rated = await ctx.confirm(
                    _(
                        "{author}, would you like to play an ELO-rated match? Your elo"
                        " is {elo1}, their elo is {elo2}."
                    ).format(
                        author=ctx.author.mention, elo1=player_elo, elo2=enemy_elo
                    ),
                )
            else:
                rated = False

            if not await ctx.confirm(
                _(
                    "{user}, you have been challenged to a chess match by {author}."
                    " They will be {color}. Do you accept? {extra}"
                ).format(
                    user=enemy.mention,
                    author=ctx.author.mention,
                    color=side,
                    extra=_("**The match will be ELO rated!**") if rated else "",
                ),
                user=enemy,
            ):
                return await ctx.send(
                    _("{user} rejected the chess match.").format(user=enemy)
                )
        else:
            rated = False

        if self.matches.get(ctx.channel.id):
            return await ctx.send(_("Wait for the match here to end."))
        self.matches[ctx.channel.id] = ChessGame(
            ctx, ctx.author, side, enemy, difficulty, rated
        )
        try:
            await self.matches[ctx.channel.id].run()
        except Exception as e:
            del self.matches[ctx.channel.id]
            raise e
        del self.matches[ctx.channel.id]

    @match.command()
    async def moves(self, ctx):
        _("""Shows the moves of the current match in the channel.""")
        game = self.matches.get(ctx.channel.id)
        if not game:
            return await ctx.send("No game here.")
        moves = "\n".join(
            [f"{idx + 1}. {i}" for idx, i in enumerate(game.pretty_moves())]
        )
        await ctx.send(moves)

    def cog_unload(self):
        if hasattr(self, "engine"):
            self.bot.loop.create_task(self.engine.quit())


def setup(bot):
    bot.add_cog(Chess(bot))
