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
import os
import random
import secrets

from typing import Optional

import discord

from discord.ext import commands

from classes.converters import CoinSide, IntFromTo, IntGreaterThan, MemberWithCharacter
from utils.checks import has_char, has_money, user_has_char
from utils.roulette import RouletteGame


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
        self.twodecks = False

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
                missing -= 11
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

    def samevalue(self, a: int, b: int):
        if a == b:
            return True
        if a in [10, 11, 12, 13] and b in [10, 11, 12, 13]:
            return True
        return False

    def splittable(self, hand):
        if self.samevalue(hand[0][0], hand[1][0]) and not self.twodecks:
            return True
        return False

    def hit(self, hand):
        card = self.deal()
        hand.append(card)
        return hand

    def split(self, hand):
        hand1 = hand[:-1]
        hand2 = [hand[-1]]
        return [hand1, hand2]

    async def player_win(self):
        if self.money > 0:
            await self.ctx.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                self.money * 2,
                self.ctx.author.id,
            )
            await self.ctx.bot.log_transaction(
                self.ctx,
                from_=1,
                to=self.ctx.author.id,
                subject="gambling",
                data={"Amount": self.money * 2},
            )

    async def player_bj_win(self):
        if self.money > 0:
            await self.ctx.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                int(self.money * 2.5),
                self.ctx.author.id,
            )
            await self.ctx.bot.log_transaction(
                self.ctx,
                from_=1,
                to=self.ctx.author.id,
                subject="gambling",
                data={"Amount": int(self.money * 2.5)},
            )

    async def player_cashback(self):
        if self.money > 0:
            await self.ctx.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                self.money,
                self.ctx.author.id,
            )
            await self.ctx.bot.log_transaction(
                self.ctx,
                from_=1,
                to=self.ctx.author.id,
                subject="gambling",
                data={"Amount": self.money},
            )

    def pretty(self, hand):
        return " ".join([card[2] for card in hand])

    async def send(self, additional=""):
        player = self.total(self.player)
        dealer = self.total(self.dealer)
        text = _(
            "The dealer has a {pretty_dealer} for a total of {dealer}\nYou have a {pretty_player} for a total of {player}\n{additional}"
        ).format(
            pretty_dealer=self.pretty(self.dealer),
            dealer=dealer,
            pretty_player=self.pretty(self.player),
            player=player,
            additional=additional,
        )
        if not self.msg:
            self.msg = await self.ctx.send(text)
        else:
            await self.msg.edit(content=text)

    async def run(self):
        self.player = [self.deal()]
        self.player2 = None
        self.dealer = [self.deal()]
        await self.send()
        # Insurance?
        if self.dealer[0][0] > 9 and await self.ctx.confirm(
            _(
                "Would you like insurance? It will cost half your bet and will get you 2:1 back if the dealer has a blackjack. Else it is gone."
            )
        ):
            self.insurance = True
        self.player = self.hit(self.player)
        self.dealer = self.hit(self.dealer)
        if self.has_bj(self.dealer):
            if self.insurance:
                await self.player_cashback()
                return await self.send(
                    additional=_(
                        "The dealer got a blackjack. You had insurance and lost nothing."
                    )
                )
            else:
                return await self.send(
                    additional=_(
                        "The dealer got a blackjack. You lost **${money}**."
                    ).format(money=self.money)
                )
        elif self.has_bj(self.player):
            await self.player_bj_win()
            return await self.send(
                additional=_("You got a blackjack and won **${money}**!").format(
                    money=int(self.money * 1.5)
                )
            )
        else:
            await self.send()
        await self.msg.add_reaction("\U00002934")  # hit
        await self.msg.add_reaction("\U00002935")  # stand
        valid = ["\U00002934", "\U00002935"]
        if self.ctx.character_data["money"] - self.money * 2 >= 0:
            await self.msg.add_reaction("\U000023ec")  # double down
            valid.append("\U000023ec")
        while (
            self.total(self.dealer) < 22
            and self.total(self.player) < 22
            and not self.over
        ):
            if self.twodecks and not self.doubled:  # player has split
                await self.msg.add_reaction("\U0001F501")  # change active deck
                valid.append("\U0001F501")
            if self.splittable(self.player):
                await self.msg.add_reaction("\U00002194")  # split
                valid.append("\U00002194")

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
                await self.ctx.bot.reset_cooldown(self.ctx)
                return await self.ctx.send(
                    _("Blackjack timed out... You lost your money!")
                )
            try:
                await self.msg.remove_reaction(reaction, user)
            except discord.Forbidden:
                pass
            while self.total(self.dealer) < 17:
                self.dealer = self.hit(self.dealer)
            if reaction.emoji == "\U00002934":  # hit
                if self.doubled:
                    valid.append("\U00002935")
                    valid.remove("\U00002934")
                    await self.msg.add_reaction("\U00002935")
                    await self.msg.remove_reaction("\U00002934", self.ctx.bot.user)
                self.player = self.hit(self.player)
                await self.send()
            elif reaction.emoji == "\U00002935":  # stand
                self.over = True
            elif reaction.emoji == "\U00002194":  # split
                self.player2, self.player = self.split(self.player)
                self.hit(self.player)
                self.hit(self.player2)
                self.twodecks = True
                await self.send(
                    additional=_("Split current hand and switched to the second side.")
                )
                valid.remove("\U00002194")
                await self.msg.remove_reaction("\U00002194", self.ctx.bot.user)
            elif reaction.emoji == "\U0001F501":  # change active side
                self.player, self.player2 = self.player2, self.player
                await self.send(additional=_("Switched to the other side."))
            else:  # double down
                if not await has_money(self.ctx.bot, self.ctx.author.id, self.money):
                    return await self.ctx.send(
                        _("Invalid. You're too poor and lose the match.")
                    )
                self.doubled = True
                if self.money > 0:
                    await self.ctx.bot.pool.execute(
                        'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                        self.money,
                        self.ctx.author.id,
                    )
                    await self.ctx.bot.log_transaction(
                        self.ctx,
                        from_=self.ctx.author.id,
                        to=2,
                        subject="gambling",
                        data={"Amount": self.money},
                    )

                self.money *= 2
                valid.remove("\U000023ec")
                valid.remove("\U00002935")
                await self.msg.remove_reaction("\U000023ec", self.ctx.bot.user)
                await self.msg.remove_reaction("\U00002935", self.ctx.bot.user)
                if self.twodecks:
                    valid.remove("\U0001F501")
                    await self.msg.remove_reaction("\U0001F501", self.ctx.bot.user)
                await self.send(
                    additional=_(
                        "You doubled your bid in exchange for only receiving one more card."
                    )
                )

        try:
            await self.msg.clear_reactions()
        except discord.Forbidden:
            pass
        player = self.total(self.player)
        dealer = self.total(self.dealer)

        if player > 21:
            await self.send(
                additional=_("You busted and lost **${money}**.").format(
                    money=self.money
                )
            )
        elif dealer > 21:
            await self.send(
                additional=_("Dealer busts and you won **${money}**!").format(
                    money=self.money
                )
            )
            await self.player_win()
        else:
            if player > dealer:
                await self.send(
                    additional=_(
                        "You have a higher score than the dealer and have won **${money}**"
                    ).format(money=self.money)
                )
                await self.player_win()
            elif dealer > player:
                await self.send(
                    additional=_(
                        "Dealer has a higher score than you and wins. You lost **${money}**."
                    ).format(money=self.money)
                )
            else:
                await self.player_cashback()
                await self.send(
                    additional=_("It's a tie, you got your **${money}** back.").format(
                        money=self.money
                    )
                )


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cards = os.listdir("assets/cards")

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(aliases=["card"])
    @locale_doc
    async def draw(self, ctx):
        _("""Draws a random card.""")
        await ctx.send(file=discord.File(f"assets/cards/{secrets.choice(self.cards)}"))

    @has_char()
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.group(aliases=["rou"], invoke_without_command=True)
    @locale_doc
    async def roulette(self, ctx, money: IntFromTo(0, 100), *, bid: str):
        _(
            """Play a game of French Roulette.
Possible simple bets:
    - noir    (all black numbers)
    - rouge   (all red numbers)
    - pair    (all even numbers)
    - impair  (all odd numbers)
    - manque  (1-18)
    - passe   (19-36)
    - premier (1-12)
    - milieu  (13-24)
    - dernier (25-36)
Complicated bets:
    - colonne (34/35/36) (all numbers in a row on the betting table, either 1, 4, ..., 34 or 2, 5, ..., 35 or 3, 6, ... 36)
    - transversale (vertical low)-(vertical high)    This includes simple and pleine (a vertical row on the betting table, e.g. 19-21. can also be two rows, e.g. 4-9)
        - les trois premiers (numbers 0, 1, 2)
    - carre (low)-(high) (a section of four numbers in a square on the betting table, e.g. 23-27)
        - les quatre premiers (numbers 0, 1, 2, 3)
    - cheval (number 1) (number 2) (a simple bet on two numbers)
    - plein (number) (a simple bet on one number)

To visualize the rows and columns, use the command: roulette table"""
        )
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You're too poor."))
        try:
            game = RouletteGame(money, bid)
        except Exception:
            return await ctx.send(
                _(
                    "Your bid input was invalid. Try the help on this command to view examples."
                )
            )
        await game.run(ctx)

    @roulette.command()
    @locale_doc
    async def table(self, ctx):
        _("""Sends a picture of a French Roulette table.""")
        await ctx.send(file=discord.File("assets/other/roulette.png"))

    @has_char()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["coin"])
    @locale_doc
    async def flip(
        self,
        ctx,
        side: Optional[CoinSide] = "heads",
        *,
        amount: IntFromTo(0, 100_000) = 0,
    ):
        _("""Flip a coin and bid on the outcome.""")
        if ctx.character_data["money"] < amount:
            return await ctx.send(_("You are too poor."))
        result = secrets.choice(
            [
                ("heads", "<:heads:437981551196897281>"),
                ("tails", "<:tails:437981602518138890>"),
            ]
        )
        if result[0] == side:
            if amount > 0:
                await self.bot.pool.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="gambling",
                    data={"Amount": amount},
                )
            await ctx.send(
                _("{result[1]} It's **{result[0]}**! You won **${amount}**!").format(
                    result=result, amount=amount
                )
            )
        else:
            if amount > 0:
                await self.bot.pool.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="gambling",
                    data={"Amount": amount},
                )
            await ctx.send(
                _("{result[1]} It's **{result[0]}**! You lost **${amount}**!").format(
                    result=result, amount=amount
                )
            )

    @has_char()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @locale_doc
    async def bet(
        self,
        ctx,
        maximum: IntGreaterThan(1) = 6,
        tip: IntGreaterThan(0) = 6,
        money: IntFromTo(0, 100_000) = 0,
    ):
        _(
            """Bet on the outcome of a dice roll with [maximum] sides. [tip] specifies the side you bet on. You will win [maximum - 1] * [money] money if you are right and lose [money] if you are wrong."""
        )
        if tip > maximum:
            return await ctx.send(
                _("Invalid Tip. Must be in the Range of `1` to `{maximum}`.").format(
                    maximum=maximum
                )
            )
        if money * (maximum - 1) > 100_000:
            return await ctx.send(_("Spend it in a better way. C'mon!"))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You're too poor."))
        randomn = secrets.randbelow(maximum + 1)
        if randomn == tip:
            if money > 0:
                await self.bot.pool.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    money * (maximum - 1),
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="gambling",
                    data={"Amount": money * (maximum - 1)},
                )
            await ctx.send(
                _(
                    "You won **${money}**! The random number was `{num}`, you tipped `{tip}`."
                ).format(num=randomn, tip=tip, money=money * (maximum - 1))
            )
            if maximum >= 100:
                await self.bot.public_log(
                    f"**{ctx.author}** won **${money * (maximum - 1)}** while betting with `{maximum}`. ({round(100/maximum, 2)}% chance)"
                )
        else:
            if money > 0:
                await self.bot.pool.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="gambling",
                    data={"Amount": money},
                )
            await ctx.send(
                _(
                    "You lost **${money}**! The random number was `{num}`, you tipped `{tip}`."
                ).format(num=randomn, tip=tip, money=money)
            )

    @has_char()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["bj"])
    @locale_doc
    async def blackjack(self, ctx, amount: IntFromTo(0, 1000) = 0):
        _("""[Alpha] Play blackjack against the dealer.""")
        if ctx.character_data["money"] < amount:
            return await ctx.send(_("You're too poor."))
        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            amount,
            ctx.author.id,
        )
        if amount > 0:
            await self.bot.log_transaction(
                ctx, from_=ctx.author.id, to=2, subject="gambling", data={"Amount": amount}
            )
        bj = BlackJack(ctx, amount)
        await bj.run()

    @has_char()
    @commands.command(aliases=["doubleorsteal"])
    @locale_doc
    async def dos(self, ctx, user: MemberWithCharacter = None):
        _(
            "Play a double-or-steal game against someone. You start with $100 and can take it or double it with your money."
        )
        msg = await ctx.send(
            _("React with 💰 to play double-or-steal with {user}!").format(
                user=ctx.author
            )
        )

        def check(r, u):
            if user and user != u:
                return False
            return (
                u != ctx.author
                and not u.bot
                and r.message.id == msg.id
                and str(r.emoji) == "\U0001f4b0"
            )

        await msg.add_reaction("\U0001f4b0")

        try:
            r, u = await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(_("Timed out."))

        if not await user_has_char(self.bot, u.id):
            return await ctx.send(_("{user} has no character.").format(user=u))
        money = 100
        users = (u, ctx.author)

        async with self.bot.pool.acquire() as conn:
            if not await self.bot.has_money(ctx.author, 100, conn=conn):
                return await ctx.send(
                    _("{user} is too poor to double.").format(user=user)
                )
            await conn.execute(
                'UPDATE profile SET "money"="money"-100 WHERE "user"=$1;', ctx.author.id
            )
            await self.bot.log_transaction(
                ctx, from_=ctx.author.id, to=2, subject="gambling", data={"Amount": 100}
            )

        while True:
            user, other = users
            try:
                action = await self.bot.paginator.Choose(
                    title=_("Double or steal ${money}?").format(money=money),
                    entries=[_("Double"), _("Steal")],
                    return_index=True,
                ).paginate(ctx, user=user)
            except self.bot.paginator.NoChoice:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    other.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=other.id,
                    subject="gambling",
                    data={"Amount": money},
                )
                return await ctx.send(_("Timed out."))

            if action:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    user.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=other.id,
                    to=user.id,
                    subject="gambling",
                    data={"Amount": money},
                )
                return await ctx.send(
                    _("{user} stole **${money}**.").format(user=user, money=money)
                )
            else:
                new_money = money * 2
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                        money,
                        other.id,
                    )
                    if not await self.bot.has_money(user.id, new_money, conn=conn):
                        return await ctx.send(
                            _("{user} is too poor to double.").format(user=user)
                        )
                    await conn.execute(
                        'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                        new_money,
                        user.id,
                    )
                    await ctx.send(
                        _("{user} doubled to **${money}**.").format(
                            user=user, money=new_money
                        )
                    )
                    money = new_money
                    users = (other, user)


def setup(bot):
    bot.add_cog(Gambling(bot))
