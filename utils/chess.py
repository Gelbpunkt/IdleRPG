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
import datetime
import io
import re

from typing import Optional

import chess
import chess.engine
import chess.pgn
import chess.svg
import discord

from async_timeout import timeout

from classes.context import Context
from utils import random
from utils.i18n import _
from utils.paginator import NoChoice


async def update_player_elos(bot, player1, player2, outcome):
    """
    Updates Chess elos for 2 players after a match based on
    their old elos and the match outcome.
    Score shall be 1 if player 1 won, 0.5 if it's a tie and 0
    if player 2 won.

    newrating = oldrating + K ⋅(score − expectedscore)

    Here K is the K-factor, which is the weight of the game. This is determined as following:

    - It is 40 if the number of played games is smaller than 30.
    - It is 20 if the number of played games is greater than 30 and the rating is less than 2400.
    - It is 10 if the number of played games is greater than 30 and the rating is more than 2400.
    - It is 40 if rating is less than 2300 and the age of the player is less than 18. We assume that everyone is 18+.

    The expected score is:
    Ea = 1 / (1 + 10 ^ ((Rb - Ra) / 400))
    """
    async with bot.pool.acquire() as conn:
        player1_elo = await conn.fetchval(
            'SELECT elo FROM chess_players WHERE "user"=$1;', player1.id
        )
        player2_elo = await conn.fetchval(
            'SELECT elo FROM chess_players WHERE "user"=$1;', player2.id
        )
        num_matches_1 = await conn.fetchval(
            'SELECT COUNT(*) FROM chess_matches WHERE "player1"=$1 OR "player2"=$1;',
            player1.id,
        )
        num_matches_2 = await conn.fetchval(
            'SELECT COUNT(*) FROM chess_matches WHERE "player1"=$1 OR "player2"=$1;',
            player2.id,
        )
        if num_matches_1 < 30:
            k_1 = 40
        elif player1_elo < 2400:
            k_1 = 20
        else:
            k_1 = 10
        if num_matches_2 < 30:
            k_2 = 40
        elif player2_elo < 2400:
            k_2 = 20
        else:
            k_2 = 10
        if outcome == "1-0":
            score = 1
        elif outcome == "1/2-1/2":
            score = 0.5
        else:
            score = 0
        expected_score_1 = 1 / (1 + 10 ** ((player2_elo - player1_elo) / 400))
        expected_score_2 = 1 / (1 + 10 ** ((player1_elo - player2_elo) / 400))

        new_rating_1 = round(player1_elo + k_1 * (score - expected_score_1))
        new_rating_2 = round(player2_elo + k_2 * (1 - score - expected_score_2))

        await conn.execute(
            'UPDATE chess_players SET "elo"=$1 WHERE "user"=$2;',
            new_rating_1,
            player1.id,
        )
        await conn.execute(
            'UPDATE chess_players SET "elo"=$1 WHERE "user"=$2;',
            new_rating_2,
            player2.id,
        )


# https://github.com/niklasf/python-chess/issues/492
class ProtocolAdapter(asyncio.Protocol):
    def __init__(self, protocol):
        self.protocol = protocol

    def connection_made(self, transport):
        self.transport = TransportAdapter(transport)
        self.protocol.connection_made(self.transport)

    def connection_lost(self, exc):
        self.transport.alive = False
        self.protocol.connection_lost(exc)

    def data_received(self, data):
        self.protocol.pipe_data_received(1, data)


class TransportAdapter(
    asyncio.SubprocessTransport, asyncio.ReadTransport, asyncio.WriteTransport
):
    def __init__(self, transport):
        self.alive = True
        self.transport = transport

    def get_pipe_transport(self, fd):
        return self

    def write(self, data):
        self.transport.write(data)

    def get_returncode(self):
        return None if self.alive else 0

    def get_pid(self):
        return None

    def close(self):
        self.transport.close()

    # Unimplemented: kill(), send_signal(signal), terminate(), and various flow
    # control methods.


class ChessGame:
    def __init__(
        self,
        ctx: Context,
        player: discord.User,
        player_color: str = "white",
        enemy: Optional[discord.User] = None,
        difficulty: Optional[int] = None,
        rated: bool = False,
    ):
        self.player = player
        self.enemy = enemy
        self.ctx = ctx
        self.board = chess.Board()
        self.engine = ctx.bot.cogs["Chess"].engine
        self.history = []
        self.move_no = 0
        self.status = "initialized"
        self.colors = {
            player: player_color,
            enemy: "black" if player_color == "white" else "white",
        }
        self.rated = rated

        if self.enemy is None:
            self.limit = chess.engine.Limit(depth=difficulty)

    def pretty_moves(self):
        history = chess.Board().variation_san(self.board.move_stack)
        splitted = re.split(r"\s?\d+\.\s", history)[1:]
        return splitted

    def parse_move(self, move, color):
        if move == "0-0":
            if color == "white":
                move = "e1g1"
            else:
                move = "e8g8"
        elif move == "0-0-0":
            if color == "white":
                move = "e1c1"
            else:
                move = "e8c8"
        elif move == "resign":
            return "resign"
        elif move == "draw":
            return "draw"
        try:
            move = self.board.parse_san(move)
        except ValueError:
            move = chess.Move.from_uci(move)
        if move not in self.board.legal_moves:
            return False
        return move

    async def get_board(self):
        svg = chess.svg.board(
            board=self.board,
            flipped=self.board.turn == chess.BLACK,
            lastmove=self.board.peek() if self.board.move_stack else None,
            check=self.board.king(self.board.turn) if self.board.is_check() else None,
        )
        async with self.ctx.bot.trusted_session.post(
            f"{self.ctx.bot.config.okapi_url}/api/genchess", json={"xml": svg}
        ) as r:
            file_ = io.BytesIO(await r.read())
        return file_

    async def get_move_from(self, player):
        if player is None:
            return await self.get_ai_move()
        file_ = await self.get_board()
        self.msg = await self.ctx.send(
            _(
                "**Move {move_no}: {player}'s turn**\nSimply type your move. You have 2"
                " minutes to enter a valid move. I accept normal notation as well as"
                " `resign` or `draw`.\nExample: `g1f3`, `Nf3`, `0-0` or `xe3`.\nMoves"
                " are case-sensitive! Pieces uppercase: `N`, `Q` or `B`, fields"
                " lowercase: `a`, `b` or `h`. Castling is `0-0` or `0-0-0`."
            ).format(move_no=self.move_no, player=player.mention),
            file=discord.File(fp=file_, filename="board.png"),
        )

        def check(msg):
            if not (msg.author == player and msg.channel == self.ctx.channel):
                return
            try:
                return bool(self.parse_move(msg.content, self.colors[player]))
            except ValueError:
                return False

        try:
            move = self.parse_move(
                (
                    await self.ctx.bot.wait_for("message", timeout=120, check=check)
                ).content,
                self.colors[player],
            )
        except asyncio.TimeoutError:
            self.status = f"{self.colors[player]} resigned"
            await self.ctx.send(_("You entered no valid move! You lost!"))
            move = "timeout"
        if self.enemy is not None or self.colors[self.player] == "black":
            await self.msg.delete()
            self.msg = None
        return move

    async def get_ai_move(self):
        if self.colors[self.player] == "black":
            self.msg = await self.ctx.send(
                _(
                    "**Move {move_no}**\nLet me think... This might take up to 2"
                    " minutes"
                ).format(move_no=self.move_no)
            )
        else:
            await self.msg.edit(
                content=_(
                    "**Move {move_no}**\nLet me think... This might take up to 2"
                    " minutes"
                ).format(move_no=self.move_no)
            )
        try:
            async with timeout(120):
                move = await self.engine.play(self.board, self.limit)
        except asyncio.TimeoutError:
            move = random.choice(list(self.board.legal_moves))
            await self.msg.delete()
            return move
        await self.msg.delete()
        if move.draw_offered:
            return "draw"
        elif move.resigned:
            return "resign"
        else:
            return move.move

    def make_move(self, move):
        self.board.push(move)

    async def get_ai_draw_response(self):
        msg = await self.ctx.send(_("Waiting for AI draw response..."))
        try:
            async with timeout(120):
                move = await self.engine.play(self.board, self.limit)
        except asyncio.TimeoutError:
            await msg.delete()
            return False
        await msg.delete()
        return move.draw_offered

    async def get_player_draw_response(self, player):
        try:
            return await self.ctx.confirm(
                _("Your enemy has proposed a draw, {player}. Do you agree?").format(
                    player=player.mention
                ),
                user=player,
            )
        except NoChoice:
            return False

    async def run(self):
        self.status = "playing"
        white, black = reversed(sorted(self.colors, key=lambda x: self.colors[x]))
        current = white
        while not self.board.is_game_over() and self.status == "playing":
            self.move_no += 1
            move = await self.get_move_from(current)
            if move == "resign":
                self.status = f"{self.colors[current]} resigned"
                break
            elif move == "timeout":
                break
            elif move == "draw":
                if self.enemy is None and current is not None:  # player offered AI
                    draw_accepted = await self.get_ai_draw_response()
                else:  # AI offered player or player offered player
                    draw_accepted = await self.get_player_draw_response(
                        black if current == white else white
                    )
                if draw_accepted:
                    self.status = "draw"
                else:
                    if self.msg and self.enemy is None and current is not None:
                        await self.msg.delete()
                    await self.ctx.send(_("The draw was rejected."), delete_after=10)
                    self.move_no -= 1
                    continue
            else:
                self.make_move(move)
                if self.history and len(self.history[-1]) == 1:
                    self.history[-1].append(move)
                else:
                    self.history.append([move])

            # swap current player
            current = black if current == white else white

        next_ = black if current == white else white
        if self.status == "draw":
            result = "1/2-1/2"
        elif self.status.endswith("resigned"):
            result = "1-0" if next_ == white else "0-1"
        else:
            result = self.board.result()
        file_ = await self.get_board()
        game = chess.pgn.Game.from_board(self.board)
        game.headers["Event"] = "IdleRPG Chess"
        game.headers["Site"] = (
            f"#{self.ctx.channel.name} in {self.ctx.guild.name}"
            if self.ctx.guild
            else "DMs"
        )
        game.headers["Date"] = datetime.date.today().isoformat()
        game.headers["Round"] = "1"
        game.headers["White"] = str(white) if white is not None else "AI"
        game.headers["Black"] = str(black) if black is not None else "AI"
        game.headers["Result"] = result
        game = f"{game}\n\n"

        if self.rated:
            if result == "1-0":
                winner = white.id
            elif result == "1/2-1/2":
                winner = None
            else:
                winner = black.id

            await update_player_elos(self.ctx.bot, white, black, result)
            await self.ctx.bot.pool.execute(
                'INSERT INTO chess_matches ("player1", "player2", "result", "pgn",'
                ' "winner") VALUES ($1, $2, $3, $4, $5);',
                white.id,
                black.id,
                result,
                game,
                winner,
            )

        if self.board.is_checkmate():
            await self.ctx.send(
                _("**Checkmate! {result}**").format(result=result),
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.board.is_stalemate():
            await self.ctx.send(
                _("**Stalemate! {result}**").format(result=result),
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.board.is_insufficient_material():
            await self.ctx.send(
                _("**Insufficient material! {result}**").format(result=result),
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.status.endswith("resigned"):
            await self.ctx.send(
                f"**{self.status.title()}! {result}**",
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.status == "draw":
            await self.ctx.send(
                _("**Draw accepted! {result}**").format(result=result),
                file=discord.File(fp=file_, filename="board.png"),
            )

        await self.ctx.send(
            _("For the nerds:"),
            file=discord.File(fp=io.BytesIO(game.encode()), filename="match.pgn"),
        )
