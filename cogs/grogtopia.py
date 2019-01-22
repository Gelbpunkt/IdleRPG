import discord
import random
import asyncio
from discord.ext import commands


class Player:
    def __init__(self, card, chief, user, military):
        self.card = card
        self.chief = chief
        self.user = user
        self.protected = False
        self.military = military

    def __repr__(self):
        return f"<Player chief={self.chief} card={self.card} military={self.military} user={self.user.name}>"

    def can_vote(self, round_no):
        if self.card == "Groggnar" and round_no % 2 == 1:
            return False
        return True

    @property
    def votes(self):
        if self.chief:
            return 2
        return 1

    async def make_move(self, table):
        pass


class Game:
    def __init__(self, ctx, players):
        self.ctx = ctx
        self.players = players
        self.classes = ["Grognar", "Bandit"]

    async def make_table(self):
        table = []
        for u in self.players:
            u_class = random.choice(self.classes)
            table.append(Player(u_class, False, u, False))
        random.shuffle(table)
        self.table = table
        random.choice(self.table).chief = True
        for i in range(5):
            random.choice(self.table).military = True

    async def main(self):
        await self.make_table()
        await self.ctx.send(self.table)


class Grogtopia:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.command()
    async def grogtopia(self, ctx):
        if self.games.get(ctx.channel.id):
            return await ctx.send("There is already a game in here!")
        players = [ctx.author]
        msg = await ctx.send(
            f"{ctx.author.mention} started a game of Grogtopia! React with :wolf: to join the game! **1 person joined**"
        )
        await msg.add_reaction("\U0001f43a")

        def check(reaction, user):
            return (
                user not in players
                and reaction.message.id == msg.id
                and not user.bot
                and str(reaction) == "\U0001f43a"
            )

        self.games[ctx.channel.id] = "forming"

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=30
                )
            except asyncio.TimeoutError:
                del self.games[ctx.channel.id]
                if len(players) < 1:  # 10 later
                    return await ctx.send(
                        "Not enough players joined... 10 are required at least"
                    )
                break
            players.append(user)
            await msg.edit(
                content=f"{ctx.author.mention} started a game of Grogtopia! React with :wolf: to join the game! **{len(players)} joined**"
            )

        game = Game(ctx, players=players)
        self.games[ctx.channel.id] = game
        await game.main()
        del self.games[ctx.channel.id]


def setup(bot):
    bot.add_cog(Grogtopia(bot))
