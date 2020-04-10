import asyncio
import datetime
import io

from functools import partial
from typing import Optional

import chess
import chess.engine
import chess.pgn
import chess.svg
import discord

from async_timeout import timeout

from classes.context import Context


def calculate_player_elos(player1_elo, player2_elo, score):
    """
    Calculates Chess elos for 2 players after a match based on
    their old elos and the match outcome.
    Score shall be 1 if player 1 won, 0.5 if it's a tie and 0
    if player 2 won.

    newrating = oldrating + K ⋅(score − expectedscore)

    Here K is the K-factor, which is the weight of the game. This is determined as following:

    - It is 40 if the number of played games is smaller than 30.
    - It is 20 if the number of played games is greater than 30 and the rating is less than 2400.
    - It is 10 if the number of played games is greater than 30 and the rating is more than 2400.
    - It is 40 if rating is less than 2300 and the age of the player is less than 18. We assume that everyone is 18+ and has played 30 games

    The expected score is:
    Ea = 1 / (1 + 10 ^ ((Rb - Ra) / 400))
    """
    expected_score_1 = 1 / (1 + 10 ** ((player2_elo - player1_elo) / 400))
    expected_score_2 = 1 / (1 + 10 ** ((player1_elo - player2_elo) / 400))
    k_1 = 20 if player1_elo < 2400 else 10  # just assuming
    k_2 = 20 if player2_elo < 2400 else 10  # just assuming

    new_rating_1 = player1_elo + k_1 * (score - expected_score_1)
    new_rating_2 = player2_elo + k_2 * (1 - score - expected_score_2)

    return round(new_rating_1), round(new_rating_2)


class ChessGame:
    def __init__(
        self,
        ctx: Context,
        player: discord.User,
        player_color: str = "white",
        enemy: Optional[discord.User] = None,
        difficulty: Optional[int] = None,
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

        self.get_player_move = partial(self.get_move_from, player)
        if self.enemy is None:
            self.limit = chess.engine.Limit(depth=difficulty)

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
            board=self.board, flipped=self.board.turn == chess.BLACK
        )
        async with self.ctx.bot.trusted_session.post(f"{self.ctx.bot.config.okapi_url}/api/genchess", data={"xml": svg}) as r:
            file_ = io.BytesIO(await r.read())
        return file_

    async def get_move_from(self, player):
        if player is None:
            return await self.get_ai_move()
        file_ = await self.get_board()
        self.msg = await self.ctx.send(
            f"**Move {self.move_no}: {player.mention}'s turn**\nSimply type your move. You have 2 minutes to enter a valid move. I accept normal notation as well as `resign` or `draw`.\nExample: `g1f3`, `Nf3`, `0-0` or `xe3`",
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
            await self.ctx.send("You entered no valid move! You lost!")
            move = "timeout"
        finally:
            if self.enemy is not None or self.colors[self.player] == "black":
                await self.msg.delete()
            return move

    async def get_ai_move(self):
        if self.colors[self.player] == "black":
            self.msg = await self.ctx.send(f"**Move {self.move_no}**\nLet me think... This might take up to 2 minutes")
        else:
            await self.msg.edit(content=f"**Move {self.move_no}**\nLet me think... This might take up to 2 minutes")
        try:
            async with timeout(120):
                move = await self.engine.play(self.board, self.limit)
        except asyncio.TimeoutError:
            move = random.choice(list(self.board.legal_moves))
        await self.msg.delete()
        if move.draw_offered:
            return "draw"
        elif move.resigned:
            return "resign"
        else:
            return move.move

    def make_move(self, move):
        self.board.push(move)

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
                self.status = "draw"  # TODO
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

        if self.board.is_checkmate():
            await self.ctx.send(
                f"**Checkmate! {result}**",
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.board.is_stalemate():
            await self.ctx.send(
                "**Stalemate!**", file=discord.File(fp=file_, filename="board.png")
            )
        elif self.board.is_insufficient_material():
            await self.ctx.send(
                "**Insufficient material! {result}**",
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.status.endswith("resigned"):
            await self.ctx.send(
                f"**{self.status.title()}! {result}**",
                file=discord.File(fp=file_, filename="board.png"),
            )
        elif self.status == "draw":
            await self.ctx.send(
                "**You accepted a draw! {result}**",
                file=discord.File(fp=file_, filename="board.png"),
            )

        await self.ctx.send(
            "For the nerds:",
            file=discord.File(fp=io.BytesIO(game.encode()), filename="match.pgn"),
        )
