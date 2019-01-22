import discord
from discord.ext import commands
from PIL import Image, ImageOps, ImageDraw, ImageFilter
from collections import defaultdict
import math
from io import BytesIO
import functools
import re
from discord.ext.commands import BucketType

from cogs.shard_communication import user_on_cooldown as user_cooldown


class Images:
    def __init__(self, bot):
        self.bot = bot

    def make_pixels(self, data):
        im = Image.open(data).resize((1024, 1024), resample=Image.NEAREST)
        b = BytesIO()
        im.save(b, format="png")
        b.seek(0)
        return b

    def make_edgy(self, data):
        with Image.open(data) as im:
            edged = im.filter(ImageFilter.FIND_EDGES)
            edged.show()
            b = BytesIO()
            edged.save(b, format="png")
        b.seek(0)
        return b

    def make_edge(self, file):
        with Image.open(file).convert("RGB") as image:
            horizontal = image.filter(
                ImageFilter.Kernel((3, 3), [-1, 0, 1, -1, 0, 1, -1, 0, 1], 1.0)
            )
            vertical = image.filter(
                ImageFilter.Kernel((3, 3), [-1, -1, -1, 0, 0, 0, 1, 1, 1], 1.0)
            )
            modified = Image.blend(horizontal, vertical, 0.5)

            f = BytesIO()
            modified.save(f, format="png")
            f.seek(0)

            return f

    def invert_image(self, file):
        with Image.open(file) as image:
            if image.mode == "RGBA":
                r, g, b, a = image.split()
                r, g, b = map(lambda image: image.point(lambda p: 255 - p), (r, g, b))
                inverted_image = Image.merge(image.mode, (r, g, b, a))
            else:
                inverted_image = ImageOps.invert(image)

            f = BytesIO()
            inverted_image.save(f, format="png")
            f.seek(0)

            return f

    def dist(self, a, b):
        return math.sqrt(sum((c - d) ** 2 for c, d in zip(a, b)))

    def _oil(self, data, radius, levels):
        with Image.open(data) as image:
            with Image.new("RGB", image.size) as out:
                pixels = image.load()
                out_pixels = out.load()
                width, height = image.size

                for x in range(width):
                    for y in range(height):
                        x_min = max(x - radius, 0)
                        x_max = min(x + radius, width)
                        y_min = max(y - radius, 0)
                        y_max = min(y + radius, height)

                        avgR = defaultdict(int)
                        avgG = defaultdict(int)
                        avgB = defaultdict(int)
                        count = defaultdict(int)

                        for x_sub in range(x_min, x_max):
                            for y_sub in range(y_min, y_max):
                                if self.dist((x, y), (x_sub, y_sub)) <= radius:
                                    r, g, b, *_ = pixels[x_sub, y_sub]
                                    lvl = int((((r + g + b) / 3) * levels) / 255)

                                    count[lvl] += 1
                                    avgR[lvl] += r
                                    avgG[lvl] += g
                                    avgB[lvl] += b

                        countmaxkey = max(count.keys(), key=lambda a: count[a])
                        countmax = count[countmaxkey]

                        finR = int(avgR[countmaxkey] / countmax)
                        finG = int(avgG[countmaxkey] / countmax)
                        finB = int(avgB[countmaxkey] / countmax)

                        out_pixels[x, y] = (finR, finG, finB)

                b = BytesIO()
                out.save(b, format="png")
                b.seek(0)
                return b

    @commands.command(description="Pixelfy!")
    async def pixelfy(self, ctx, user: discord.Member = None, size: int = 2):
        try:
            size = [256, 128, 64, 32, 16][size - 1]
        except:
            return await ctx.send("Use 1, 2, 3, 4 or 5 as intensity value.")
        user = user or ctx.author
        url = user.avatar_url_as(format="png", size=size)
        # change size to lower for less pixels
        async with self.bot.session.get(url) as r:
            data = BytesIO(await r.read())
        thing = functools.partial(self.make_pixels, data)
        b = await self.bot.loop.run_in_executor(None, thing)
        file = discord.File(b, filename="pixel.png")
        await ctx.send(file=file)

    @commands.command(description="Edgyfy images.")
    async def edgy(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        async with self.bot.session.get(user.avatar_url_as(format="png")) as r:
            data = BytesIO(await r.read())
        thing = functools.partial(self.make_edge, data)
        b = await self.bot.loop.run_in_executor(None, thing)
        file = discord.File(b, filename="edgy.png")
        await ctx.send(file=file)

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command(description="Inverts an avatar.")
    async def invert(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author

        async with self.bot.session.get(member.avatar_url_as(format="png")) as r:
            with BytesIO(await r.read()) as f:
                func = functools.partial(self.invert_image, f)
                file = await self.bot.loop.run_in_executor(None, func)

                await ctx.send(file=discord.File(file, filename="inverted.png"))

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command(description="Oils an avatar", enabled=False)
    async def oil(self, ctx, *, member: discord.Member = None):
        member = member or ctx.author

        async with self.bot.session.get(
            member.avatar_url_as(format="png", size=256)
        ) as r:
            with BytesIO(await r.read()) as f:
                func = functools.partial(self._oil, f, 3, 20)
                file = await self.bot.loop.run_in_executor(None, func)

                await ctx.send(file=discord.File(file, filename="oil.png"))


def setup(bot):
    bot.add_cog(Images(bot))
