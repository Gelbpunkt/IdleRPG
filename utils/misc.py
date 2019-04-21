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


def makebg(background, imgtype):
    with Image.open(background).convert("RGBA").resize(
        (800, 600), resample=Image.NEAREST
    ) as bg:
        if imgtype == 1:
            with Image.open("assets/profiles/Foreground.png") as fg:
                bg = Image.alpha_composite(bg, fg)
                output_buffer = io.BytesIO()
                bg.save(output_buffer, "png")
                output_buffer.seek(0)
                return output_buffer
        elif imgtype == 2:
            with Image.open("assets/profiles/Foreground2.png") as fg:
                bg = Image.alpha_composite(bg, fg)
                output_buffer = io.BytesIO()
                bg.save(output_buffer, "png")
                output_buffer.seek(0)
                return output_buffer


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


def profile_image(
    profile,
    sword,
    shield,
    mission,
    missionend,
    ranks,
    color,
    image,
    marriage,
    guild,
    extras,
):
    level = xptolevel(profile[3])
    try:
        if not str(missionend)[:7].startswith("-"):
            endstr = f"{str(missionend)[:7]} left"
        else:
            endstr = "finished"
        missionnumber = mission[3]
        missionstring = f"Adventure {missionnumber}, {endstr}"
    except (KeyError, IndexError):
        missionstring = "You are in no adventure!"
    if guild:
        guild = guild[0]
    else:
        guild = "No guild"

    with Image.open(image) as my_image:
        if color:
            try:
                color = color.lstrip("#")
                color = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                color = (255, 255, 255)
        else:
            color = (255, 255, 255)
        draw = ImageDraw.Draw(my_image)
        font = ImageFont.truetype("assets/fonts/CaviarDreams.ttf", 34)
        font2 = ImageFont.truetype("assets/fonts/CaviarDreams.ttf", 24)
        font3 = ImageFont.truetype("assets/fonts/CaviarDreams.ttf", 28)
        draw.text((73, 21), profile[1], color, font=font)
        draw.text((742, 34), str(level), (0, 0, 0), font=font2)
        draw.text((98, 315), str(profile[2]), color, font=font)
        draw.text((98, 386), str(profile[4]), color, font=font)
        draw.text((81, 138), sword[0], color, font=font2)
        draw.text((487, 130), str(sword[1]), color, font=font3)
        draw.text((81, 224), shield[0], color, font=font2)
        draw.text((487, 221), str(shield[1]), color, font=font3)
        draw.text((271, 457), str(ranks[0]), color, font=font)
        draw.text((419, 457), str(ranks[1]), color, font=font)
        draw.text((264, 570.8), missionstring, color, font=font2)
        draw.text((589, 351), marriage, color, font=font2)
        draw.text((589, 444), guild, color, font=font2)
        draw.text((127, 517), profile[13], color, font=font2)
        if int(extras[0]) != 0:
            draw.text((570, 135), f"(+{int(extras[0])})", color, font=font2)
        if int(extras[1]) != 0:
            draw.text((570, 223), f"(+{int(extras[1])})", color, font=font2)
        if profile[13] in [
            "Mage",
            "Wizard",
            "Pyromancer",
            "Elementalist",
            "Dark Caster",
        ]:
            with Image.open(Path("assets/icons/elementalist.png")).resize(
                (50, 50), resample=Image.NEAREST
            ) as overlay:
                my_image.paste(overlay, (723, 506), overlay)
        elif profile[13] in ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"]:
            with Image.open(Path("assets/icons/thief.png")).resize(
                (50, 50), resample=Image.NEAREST
            ) as overlay:
                my_image.paste(overlay, (723, 506), overlay)
        elif profile[13] in ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"]:
            with Image.open(Path("assets/icons/warrior.png")).resize(
                (50, 50), resample=Image.NEAREST
            ) as overlay:
                my_image.paste(overlay, (723, 506), overlay)
        elif profile[13] in ["Novice", "Proficient", "Artisan", "Master", "Paragon"]:
            with Image.open(Path("assets/icons/paragon.png")).resize(
                (50, 50), resample=Image.NEAREST
            ) as overlay:
                my_image.paste(overlay, (723, 506), overlay)
        elif profile[13] in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
            with Image.open(Path("assets/icons/ranger.png")).resize(
                (50, 50), resample=Image.NEAREST
            ) as overlay:
                my_image.paste(overlay, (723, 506), overlay)
        output_buffer = io.BytesIO()
        my_image.save(output_buffer, "png")
        output_buffer.seek(0)
        return output_buffer


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
