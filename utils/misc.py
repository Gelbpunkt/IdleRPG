"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import io
import os
import random
from pathlib import Path

from discord.errors import NotFound
from PIL import Image, ImageDraw, ImageFont

levels = {
    "1": 0,
    "2": 1000,
    "3": 1500,
    "4": 2250,
    "5": 3375,
    "6": 5062,
    "7": 7593,
    "8": 11390,
    "9": 17085,
    "10": 25630,
    "11": 38445,
    "12": 57666,
    "13": 86500,
    "14": 129_750,
    "15": 194_625,
    "16": 291_938,
    "17": 437_907,
    "18": 656_860,
    "19": 985_290,
    "20": 1_500_000,
}


def hex_to_rgb(hex_):
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i : i + 2], 16) for i in (0, 2, 4))


def xptolevel(xp):
    for point in list(levels.values()):
        if xp == point:
            return list(levels.keys())[list(levels.values()).index(point)]
        elif xp < point:
            return list(levels.keys())[list(levels.values()).index(point) - 1]
        elif xp > 1_500_000:
            return "20"


def xptonextlevel(xp):
    level = xptolevel(xp)
    if level == "20":
        return "Infinity"
    else:
        nextxp = levels[str(int(level) + 1)]
        return str(nextxp - xp)


def calcchance(sword, shield, dungeon, level, returnsuccess=False, booster=False):
    if returnsuccess is False:
        return (
            sword + shield + 75 - (dungeon * 10),
            sword + shield + 75 - (dungeon * 2),
            level,
        )
    else:
        randomn = random.randint(0, 100)
        success = (
            sword
            + shield
            + 75
            - (dungeon * (random.randint(2, 10)))
            + random.choice([level, -level])
        )
        if booster:
            success += 25
        return randomn <= success


def makeadventures(percentages):
    images = []

    def key(s):
        return int(s[: s.index(".")])

    allfiles = sorted(os.listdir("assets/adventures"), key=key)
    for filetoopen in allfiles:
        with Image.open("assets/adventures/" + filetoopen) as myf:
            draw = ImageDraw.Draw(myf)
            font = ImageFont.truetype("assets/fonts/CaviarDreams.ttf", 16)
            draw.text(
                (314, 168),
                f"{percentages[allfiles.index(filetoopen)][0]}% to",
                (0, 0, 0),
                font=font,
            )
            draw.text(
                (314, 187),
                f"{percentages[allfiles.index(filetoopen)][1]}%",
                (0, 0, 0),
                font=font,
            )
            output_buffer = io.BytesIO()
            myf.save(output_buffer, "png")
            output_buffer.seek(0)
            images.append(output_buffer)
    return images


async def lookup(bot, userid):
    userid = int(userid)
    member = await bot.get_user_global(userid)
    if member:
        return str(member)
    else:
        try:
            member = await bot.fetch_user(userid)
        except NotFound:
            return "None"
        else:
            return str(member)
