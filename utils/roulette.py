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
import secrets

ALL_NUMBERS = list(range(37))

STATIC_BIDS = {
    "rouge": [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
    "noir": [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35],
    "pair": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36],
    "impair": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35],
    "manque": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "passe": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36],
    "premier": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "milieu": [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
    "dernier": [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36],
    "34": [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
    "35": [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
    "36": [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
    "les trois premiers": [0, 1, 2],
    "les quatre premiers": [0, 1, 2, 3],
}


def get_row(number):
    for i in ("34", "35", "36"):
        if number in STATIC_BIDS[i]:
            return i
    return None


def get_colour(number):
    if number in STATIC_BIDS["rouge"]:
        return "red"
    elif number in STATIC_BIDS["noir"]:
        return "black"
    else:  # 0
        return "green"


def verify_numbers(numbers):
    for i in numbers:
        if not 0 < i < 37:
            return False
    return True


class RouletteGame:
    """A game of french roulette with french words."""

    def __init__(self, money, bet):
        self.money = money
        self.bet_type, self.payout, self.numbers = self.parse_bet(bet)
        self.ctx = None
        self.message = None
        self.result = None

    def parse_bet(self, text):
        """Parses a bet in French roulette.
        Possible simple bets:
            - noir
            - rouge
            - pair
            - impair
            - manque
            - passe
            - premier
            - milieu
            - dernier
        Complicated bets:
            - colonne (34/35/36)
            - transversale (vertical low)-(vertical high)    This includes simple and pleine
                - les trois premiers
                - les quatre premiers
            - carre (low)-(high)
            - cheval (number 1) (number 2)
            - plein (number)
        Returns a tuple of bid type, payout and the arguments (numbers) that would win.
        """
        chunks = text.lower().split()
        if chunks[0] == "les" and len(chunks) == 3:
            bid_type = " ".join(chunks)
        else:
            bid_type = chunks[0]

        if bid_type in ("noir", "rouge", "pair", "impair", "manque", "passe"):
            # Simple bets 1:1
            return bid_type, 1, STATIC_BIDS[bid_type]
        elif bid_type in ("premier", "milieu", "dernier"):
            # Simple bets 2:1
            return bid_type, 2, STATIC_BIDS[bid_type]
        elif bid_type == "colonne":
            # Simple bet 2:1 with argument
            return bid_type, 2, STATIC_BIDS[chunks[1]]
        elif bid_type == "transversale":
            numbers = [int(i) for i in chunks[1].split("-")]
            diff = abs(numbers[1] - numbers[0])
            if diff == 2:
                # Transversale pleine
                numbers = sorted(
                    [numbers[0], (numbers[0] + numbers[1]) // 2, numbers[1]]
                )
                # they must be in seperate rows
                assert numbers[0] in STATIC_BIDS["34"]
                return bid_type, 11, numbers
            elif diff == 5:
                # Transversale simple
                numbers = list(range(numbers[0], numbers[1] + 1))
                # they must be in seperate rows
                assert numbers[0] in STATIC_BIDS["34"]
                assert verify_numbers(numbers)
                return bid_type, 5, numbers
        elif bid_type == "les trois premiers":
            return bid_type, 11, STATIC_BIDS[bid_type]
        elif bid_type == "les quatre premiers":
            return bid_type, 8, STATIC_BIDS[bid_type]
        elif bid_type == "carre":
            numbers = [int(i) for i in chunks[1].split("-")]
            diff = abs(numbers[1] - numbers[0])
            assert diff == 4
            numbers = [numbers[0], numbers[0] + 1, numbers[1] - 1, numbers[1]]
            assert verify_numbers(numbers)
            return bid_type, 8, numbers
        elif bid_type == "cheval":
            assert len(chunks) == 3
            numbers = [int(chunks[1]), int(chunks[2])]
            assert verify_numbers(numbers)
            return bid_type, 17, numbers
        elif bid_type == "plein":
            assert len(chunks) == 2
            numbers = [int(chunks[1])]
            assert verify_numbers(numbers)
            return bid_type, 35, numbers
        raise ValueError  # we got somewhere we don't know

    async def run(self, ctx):
        self.ctx = ctx
        # They pay for the roll
        await self.remove_money()
        # The result of the roll
        self.result = secrets.choice(ALL_NUMBERS)
        self.message = await ctx.send(
            _("<a:roulette:691749187284369419> Spinning the wheel...")
        )
        await asyncio.sleep(3)
        if self.result in self.numbers:
            await self.handle_win()
        else:
            await self.handle_loss()

    async def remove_money(self):
        await self.ctx.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            self.money,
            self.ctx.author.id,
        )

    async def handle_win(self):
        await self.ctx.bot.pool.execute(
            'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
            self.money * (self.payout + 1),
            self.ctx.author.id,
        )
        await self.message.edit(
            content=_(
                "It's a :{colour}_circle: {number}! You won **${money}**!"
            ).format(
                colour=get_colour(self.result),
                number=self.result,
                money=self.money * self.payout,
            )
        )
        await self.ctx.bot.log_transaction(
            self.ctx,
            from_=1,
            to=self.ctx.author.id,
            subject="gambling",
            data={"Amount": self.money * self.payout},
        )

    async def handle_loss(self):
        await self.message.edit(
            content=_(
                "It's a :{colour}_circle: {number}! You lost **${money}**!"
            ).format(
                colour=get_colour(self.result), number=self.result, money=self.money
            )
        )
        await self.ctx.bot.log_transaction(
            self.ctx,
            from_=self.ctx.author.id,
            to=2,
            subject="gambling",
            data={"Amount": self.money},
        )
