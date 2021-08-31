"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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
import base64
import hashlib
import hmac
import time

from decimal import Decimal

from discord.errors import NotFound

from utils import random

levels = {
    1: 0,
    2: 1500,
    3: 9000,
    4: 22500,
    5: 42000,
    6: 67500,
    7: 99000,
    8: 136500,
    9: 180000,
    10: 229500,
    11: 285000,
    12: 346500,
    13: 414000,
    14: 487500,
    15: 567000,
    16: 697410,
    17: 857814,
    18: 1055112,
    19: 1297787,
    20: 1596278,
    21: 1931497,
    22: 2298481,
    23: 2689223,
    24: 3092606,
    25: 3494645,
    26: 3879056,
    27: 4228171,
    28: 4608707,
    29: 5023490,
    30: 5475604,
}


def random_token(id_):
    """Returns a random theoretically valid token for a discord user"""
    id_ = base64.b64encode(str(id_).encode()).decode()
    time_ = base64.b64encode(
        int.to_bytes(int(time.time()), 6, byteorder="big")
    ).decode()
    randbytes = bytearray(random.randbits(8) for _ in range(10))
    hmac_ = hmac.new(randbytes, randbytes, hashlib.md5).hexdigest()
    return f"{id_}.{time_}.{hmac_}"


def nice_join(iterable):
    if len(iterable) == 1:
        return iterable[0]
    return f"{', '.join([str(i) for i in iterable[:-1]])} and {iterable[-1]}"


def xptolevel(xp):
    for level, point in levels.items():
        if xp == point:
            return level
        elif xp < point:
            return level - 1
    return 30


def xptonextlevel(xp):
    level = xptolevel(xp)
    if level == 30:
        return "Infinity"
    else:
        nextxp = levels[level + 1]
        return f"{nextxp - xp}"


def calcchance(
    sword, shield, dungeon, level, luck, returnsuccess=False, booster=False, bonus=0
):
    if returnsuccess is False:
        val1 = sword + shield + 75 - dungeon * 7 + bonus - level / Decimal("2")
        val2 = sword + shield + 75 - dungeon + bonus + level
        val1 = round(val1 * luck) if val1 >= 0 else round(val1 / luck)
        val2 = round(val2 * luck) if val2 >= 0 else round(val2 / luck)
        if booster:
            val1 += 25
            val2 += 25
        return (val1, val2)
    else:
        randomn = random.randint(0, 100)
        if booster:
            randomn -= 25
        success = (
            sword
            + shield
            + 75
            - (dungeon * (random.randint(1, 7)))
            + random.choice([level, -level / Decimal("2")])
            + bonus
        )
        if success >= 0:
            success = round(success * luck)
        else:
            success = round(success / luck)
        return randomn <= success


async def lookup(bot, userid, return_none=False):
    userid = int(userid)
    member = await bot.get_user_global(userid)
    if member:
        return str(member)
    else:
        try:
            member = await bot.fetch_user(userid)
        except NotFound:
            if return_none:
                return None
            else:
                return "None"
        else:
            return str(member)
