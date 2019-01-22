import discord
import asyncio
import random
from discord.ext import commands


class TicTacToe:
    def __init__(self, ctx, enemy=None):
        self.ctx = ctx
        self.x = "❌"
        self.o = "⭕"
        self.blank = ":white_square_button:"
        self.possible = {}

        self.player1 = ctx.author
        if not enemy:
            self.player2 = ctx.me
        else:
            self.player2 = enemy

        self.player1_sign = self.x
        self.player2_sign = self.o

        self.field = [
            self.blank,
            self.blank,
            self.blank,
            self.blank,
            self.blank,
            self.blank,
            self.blank,
            self.blank,
            self.blank,
        ]

        self.buttons = {
            "1\u20e3": "1",
            "2\u20e3": "2",
            "3\u20e3": "3",
            "4\u20e3": "4",
            "5\u20e3": "5",
            "6\u20e3": "6",
            "7\u20e3": "7",
            "8\u20e3": "8",
            "9\u20e3": "9",
            "⏹": "stop",
        }

    def make_move_player1(self, field):
        self.field[field] = self.player1_sign

    def make_move_player2(self, field):
        self.field[field] = self.player2_sign

    def get_field_vals(self):
        out = []
        for val in self.field:
            if val == self.player1_sign:
                out.append(1)
            elif val == self.player2_sign:
                out.append(-1)
            else:
                out.append(0)
        return out

    async def handle_player1_win(self):
        if self.ctx.me == self.player2:
            await self.ctx.send("You beat me!")
        else:
            await self.ctx.send(f"{self.player1.mention} won!")
        return True

    async def handle_player2_win(self):
        if self.ctx.me == self.player2:
            await self.ctx.send("I beat you!")
        else:
            await self.ctx.send(f"{self.player2.mention} won!")
        return True

    async def handle_tie(self):
        await self.ctx.send("It's a tie!")
        return True

    async def game_over(self):
        field = self.get_field_vals()
        for row in [field[0:3], field[3:6], field[6:9]]:
            row_sum = sum(row)
            if row_sum == -3:
                return await self.handle_player2_win()
            elif row_sum == 3:
                return await self.handle_player1_win()
        for column in [
            [field[0], field[3], field[6]],
            [field[1], field[4], field[7]],
            [field[2], field[5], field[8]],
        ]:
            col_sum = sum(column)
            if col_sum == -3:
                return await self.handle_player2_win()
            elif col_sum == 3:
                return await self.handle_player1_win()
        for cross in [[field[0], field[4], field[8]], [field[2], field[4], field[6]]]:
            crs_sum = sum(cross)
            if crs_sum == -3:
                return await self.handle_player2_win()
            elif crs_sum == 3:
                return await self.handle_player1_win()
        if not any([f == self.blank for f in self.field]):
            return await self.handle_tie()
        return False

    async def update(self):
        await self.base.edit(
            content=f'{"".join(self.field[0:3])}\n{"".join(self.field[3:6])}\n{"".join(self.field[6:9])}'
        )

    def get_rand_move(self):
        self.field[
            random.choice([f for f in range(9) if self.field[f] == self.blank])
        ] = self.player2_sign

    async def main(self):
        self.base = await self.ctx.send(
            f'{"".join(self.field[0:3])}\n{"".join(self.field[3:6])}\n{"".join(self.field[6:9])}'
        )
        for react in self.buttons:
            await self.base.add_reaction(str(react))

        def check1(r, u):
            if u != self.player1:
                return False
            elif str(r) not in self.buttons.keys():
                return False
            elif r.message.id != self.base.id:
                return False
            return True

        def check2(r, u):
            if u != self.player2:
                return False
            elif str(r) not in self.buttons.keys():
                return False
            elif r.message.id != self.base.id:
                return False
            return True

        while True:
            try:
                react, user = await self.ctx.bot.wait_for(
                    "reaction_add", check=check1, timeout=60
                )
            except asyncio.TimeoutError:
                return await self.ctx.send("Timed out!")
            control = self.buttons.get(str(react))
            if control == "stop":
                return await self.ctx.send(f"{user} stopped the game.")
            field = int(control) - 1
            if self.field[field] != self.blank:
                await self.ctx.send("Already occupied.")
                continue
            self.make_move_player1(field)
            await self.update()
            if await self.game_over():
                break
            if self.player2 == self.ctx.me:
                self.get_rand_move()
            else:
                while True:
                    try:
                        react, user = await self.ctx.bot.wait_for(
                            "reaction_add", check=check2, timeout=60
                        )
                    except asyncio.TimeoutError:
                        return await self.ctx.send("Timed out!")
                    control = self.buttons.get(str(react))
                    if control == "stop":
                        return await self.ctx.send(f"{user} stopped the game.")
                    field = int(control) - 1
                    if self.field[field] != self.blank:
                        await self.ctx.send("Already occupied.")
                        continue
                    self.make_move_player2(field)
                    break
            await self.update()
            if await self.game_over():
                break


class Games:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command(aliases=["ttt"])
    @commands.guild_only()
    async def tictactoe(self, ctx, enemy: discord.Member = None):
        """Play Tic Tac Toe with me or a friend. Made by Adrian#1337, the Python God"""
        if self.games.get(ctx.channel.id):
            return await ctx.send("Already game here!")
        game = TicTacToe(ctx, enemy)
        self.games[ctx.channel.id] = game
        await game.main()
        del self.games[ctx.channel.id]


def setup(bot):
    bot.add_cog(Games(bot))
