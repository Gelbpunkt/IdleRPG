"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import os
import random
import secrets
from typing import Optional

import discord
from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan
from utils.checks import has_char


class BlackJack:
    def __init__(self, ctx, money):
        self.cards = {
            "adiamonds": "<:adiamonds:508321810832556033>",
            "2diamonds": "<:2diamonds:508321809536385024>",
            "3diamonds": "<:3diamonds:508321809729585172>",
            "4diamonds": "<:4diamonds:508321809678991362>",
            "5diamonds": "<:5diamonds:508321810098683910>",
            "6diamonds": "<:6diamonds:508321810325176333>",
            "7diamonds": "<:7diamonds:508321810300010497>",
            "8diamonds": "<:8diamonds:508321810635292693>",
            "9diamonds": "<:9diamonds:508321810836881438>",
            "10diamonds": "<:10diamonds:508321811016974376>",
            "jdiamonds": "<:jdiamonds:508321810878824460>",
            "qdiamonds": "<:qdiamonds:508321811016974376>",
            "kdiamonds": "<:kdiamonds:508321811612696576>",
            "aclubs": "<:aclubs:508321811151192064>",
            "2clubs": "<:2clubs:508321809221812245>",
            "3clubs": "<:3clubs:508321809410818096>",
            "4clubs": "<:4clubs:508321809926717450>",
            "5clubs": "<:5clubs:508321810127912970>",
            "6clubs": "<:6clubs:508321810622971904>",
            "7clubs": "<:7clubs:508321810182438955>",
            "8clubs": "<:8clubs:508321810421514279>",
            "9clubs": "<:9clubs:508321810677497894>",
            "10clubs": "<:10clubs:508321810794676234>",
            "jclubs": "<:jclubs:508321811176488960>",
            "qclubs": "<:qclubs:508321811407306762>",
            "kclubs": "<:kclubs:508321811365101578>",
            "ahearts": "<:ahearts:508321810828361742>",
            "2hearts": "<:2hearts:508321809632854016>",
            "3hearts": "<:3hearts:508321809662345231>",
            "4hearts": "<:4hearts:508321810023186442>",
            "5hearts": "<:5hearts:508321810396348456>",
            "6hearts": "<:6hearts:508321810249678852>",
            "7hearts": "<:7hearts:508321810417451008>",
            "8hearts": "<:8hearts:508321810635423748>",
            "9hearts": "<:9hearts:508321810727829533>",
            "10hearts": "<:10hearts:508321810970836992>",
            "jhearts": "<:jhearts:508321811373621249>",
            "qhearts": "<:qhearts:508321867954782208>",
            "khearts": "<:khearts:508321811424083969>",
            "aspades": "<:aspades:508321810811584527>",
            "2spades": "<:2spades:508321809591173120>",
            "3spades": "<:3spades:508321809981112340>",
            "4spades": "<:4spades:508321810190696458>",
            "5spades": "<:5spades:508321810400673824>",
            "6spades": "<:6spades:508321810358599680>",
            "7spades": "<:7spades:508321810874630155>",
            "8spades": "<:8spades:508321810828492820>",
            "9spades": "<:9spades:508321810815647744>",
            "10spades": "<:10spades:508321810874499083>",
            "jspades": "<:jspades:508321811298254875>",
            "qspades": "<:qspades:508321868193726464>",
            "kspades": "<:kspades:508321811457507329>",
        }
        self.prepare_deck()
        self.ctx = ctx
        self.msg = None
        self.over = False
        self.money = money
        self.insurance = False
        self.doubled = False

    def prepare_deck(self):
        self.deck = []
        for colour in ["hearts", "diamonds", "spades", "clubs"]:
            for value in range(2, 15):  # 11 = Jack, 12 = Queen, 13 = King, 14 = Ace
                if value == 11:
                    card = "j"
                elif value == 12:
                    card = "q"
                elif value == 13:
                    card = "k"
                elif value == 14:
                    card = "a"
                else:
                    card = str(value)
                self.deck.append((value, colour, self.cards[f"{card}{colour}"]))
        self.deck = self.deck * 6  # BlackJack is played with 6 sets of cards
        random.shuffle(self.deck)

    def deal(self):
        return self.deck.pop()

    def calc_aces(self, value, aces):
        missing = 21 - value
        num_11 = 0
        num_1 = 0
        for i in range(aces):
            if missing < 11:
                num_1 += 1
                missing -= 1
            else:
                num_11 += 1
                missing -= 1
        return num_11 * 11 + num_1

    def total(self, hand):
        value = sum(
            [card[0] if card[0] < 11 else 10 for card in hand if card[0] != 14]
        )  # ignore aces for now
        aces = sum([1 for card in hand if card[0] == 14])
        value += self.calc_aces(value, aces)
        return value

    def has_bj(self, hand):
        return self.total(hand) == 21

    def hit(self, hand):
        card = self.deal()
        hand.append(card)
        return hand

    async def player_win(self):
        await self.ctx.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
            self.money * 2,
            self.ctx.author.id,
        )

    async def player_cashback(self):
        await self.ctx.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
            self.money,
            self.ctx.author.id,
        )

    def pretty(self, hand):
        return " ".join([card[2] for card in hand])

    async def send(self, additional=""):
        player = self.total(self.player)
        dealer = self.total(self.dealer)
        text = f"The dealer has a {self.pretty(self.dealer)} for a total of {dealer}\nYou have a {self.pretty(self.player)} for a total of {player}\n{additional}"
        if not self.msg:
            self.msg = await self.ctx.send(text)
        else:
            await self.msg.edit(content=text)

    async def run(self):
        self.player = [self.deal()]
        self.dealer = [self.deal()]
        await self.send()
        # Insurance?
        if await self.ctx.confirm(
            "Would you like insurance? It will cost half your bet and will get you 2:1 back if the dealer has a blackjack. Else it is gone."
        ):
            self.insurance = True
        self.player = self.hit(self.player)
        self.dealer = self.hit(self.dealer)
        if self.has_bj(self.dealer):
            if self.insurance:
                await self.player_cashback()
                return await self.send(
                    additional="The dealer got a blackjack. You had insurance and lost nothing."
                )
            else:
                return await self.send(
                    additional="The dealer got a blackjack. You lost."
                )
        elif self.has_bj(self.player):
            await self.player_win()
            return await self.send(additional="You got a blackjack and won!")
        await self.msg.add_reaction("\U00002934")  # hit
        await self.msg.add_reaction("\U00002935")  # stand
        await self.msg.add_reaction("\U000023ec")  # double down
        valid = ["\U00002934", "\U00002935", "\U000023ec"]
        while (
            self.total(self.dealer) < 22
            and self.total(self.player) < 22
            and not self.over
        ):

            def check(reaction, user):
                return (
                    reaction.message.id == self.msg.id
                    and user == self.ctx.author
                    and str(reaction.emoji) in valid
                )

            try:
                reaction, user = await self.ctx.bot.wait_for(
                    "reaction_add", check=check, timeout=20
                )
            except asyncio.TimeoutError:
                return await self.ctx.send(
                    "Blackjack timed out... You lost your money!"
                )
            try:
                await self.msg.remove_reaction(reaction, user)
            except discord.Forbidden:
                pass
            while self.total(self.dealer) < 17:
                self.dealer = self.hit(self.dealer)
            if reaction.emoji == "\U00002934":
                if self.doubled:
                    valid.append("\U00002935")
                    valid.remove("\U00002934")
                    await self.msg.add_reaction("\U00002935")
                    await self.msg.remove_reaction("\U00002934", self.ctx.bot.user)
                self.player = self.hit(self.player)
                await self.send()
            elif reaction.emoji == "\U00002935":
                self.over = True
            else:
                self.doubled = True
                await self.ctx.bot.pool.execute(
                    'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                    self.money,
                    self.ctx.author.id,
                )

                self.money *= 2
                valid.remove("\U000023ec")
                valid.remove("\U00002935")
                await self.msg.remove_reaction("\U000023ec", self.ctx.bot.user)
                await self.msg.remove_reaction("\U00002935", self.ctx.bot.user)
                await self.send(
                    additional="You doubled your bid in exchange for only receiving one more card."
                )

        player = self.total(self.player)
        dealer = self.total(self.dealer)
        if player > 21:
            await self.send(additional="You busted and loose.")
        elif dealer > 21:
            await self.send(additional="Dealer busts and you win!")
            await self.player_win()
        else:
            if player > dealer:
                await self.send(
                    additional="You have a higher score than the dealer and win."
                )
                await self.player_win()
            elif dealer > player:
                await self.send(
                    additional="Dealer has a higher score than you and wins."
                )
            else:
                await self.send(additional="It's a tie. You loose your bet.")


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cards = os.listdir("assets/cards")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["card"])
    async def draw(self, ctx):
        """Draws a random card."""
        await ctx.send(file=discord.File(f"assets/cards/{secrets.choice(self.cards)}"))

    @has_char()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["coin"])
    async def flip(
        self,
        ctx,
        side: Optional[str.lower] = "heads",
        *,
        amount: IntFromTo(0, 100_000) = 0,
    ):
        """Flip a coin and bid on the outcome."""
        if side not in ["heads", "tails"]:
            return await ctx.send(f"Use `heads` or `tails` instead of `{side}`.")
        if ctx.character_data["money"] < amount:
            return await ctx.send("You are too poor.")
        result = secrets.choice(
            [
                ("heads", "<:heads:437981551196897281>"),
                ("tails", "<:tails:437981602518138890>"),
            ]
        )
        if result[0] == side:
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await ctx.send(f"{result[1]} It's **{result[0]}**! You won **${amount}**!")
        else:
            await self.bot.pool.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await ctx.send(f"{result[1]} It's **{result[0]}**! You lost **${amount}**!")

    @has_char()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    async def bet(
        self,
        ctx,
        maximum: IntGreaterThan(1) = 6,
        tip: IntGreaterThan(0) = 6,
        money: IntFromTo(0, 100_000) = 0,
    ):
        if tip > maximum:
            return await ctx.send(
                f"Invalid Tip. Must be in the Range of `1` to `{maximum}`."
            )
        if money * (maximum - 1) > 100_000:
            return await ctx.send("Spend it in a better way. C'mon!")
        if ctx.character_data["money"] < money:
            return await ctx.send("You're too poor.")
        randomn = secrets.randbelow(maximum + 1)
        if randomn == tip:
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                money * (maximum - 1),
                ctx.author.id,
            )
            await ctx.send(
                f"You won **${money*(maximum-1)}**! The random number was `{randomn}`, you tipped `{tip}`."
            )
        else:
            await self.bot.pool.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            await ctx.send(
                f"You lost **${money}**! The random number was `{randomn}`, you tipped `{tip}`."
            )

    @has_char()
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(aliases=["bj"])
    async def blackjack(self, ctx, amount: IntFromTo(0, 1000) = 0):
        """[Alpha] Play blackjack against the dealer. Dealer rules, means wins in case of tie."""
        if ctx.character_data["money"] < amount:
            return await ctx.send("You're too poor.")
        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            amount,
            ctx.author.id,
        )
        bj = BlackJack(ctx, amount)
        await bj.run()


def setup(bot):
    bot.add_cog(Gambling(bot))
