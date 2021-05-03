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
from json import loads
from re import findall
from time import time

import discord

from discord.ext import commands

from utils.i18n import _, locale_doc


def get_colour(percent):
    rounded = (round(percent, -1) // 10) - 1
    if rounded == -1:
        rounded = 0
    values = [
        (255, 255, 255),
        (255, 229, 131),
        (241, 255, 0),
        (255, 238, 0),
        (255, 223, 0),
        (255, 215, 0),
        (255, 200, 0),
        (138, 109, 0),
        (74, 74, 74),
        (0, 0, 0),
    ][rounded]
    return discord.Colour.from_rgb(values[0], values[1], values[2])


class Akinator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.regions = {
            "jp": "https://srv11.akinator.com:9172",
            "de": "https://srv7.akinator.com:9145",
            "pt": "https://srv3.akinator.com:9166",
            "ar": "https://srv2.akinator.com:9155",
            "fr": "https://srv3.akinator.com:9165",
            "us": "https://srv2.akinator.com:9157",
            "es": "https://srv6.akinator.com:9127",
            "ru": "https://srv5.akinator.com:9124",
            "il": "https://srv4.akinator.com:9170",
            "cn": "https://srv11.akinator.com:9150",
            "it": "https://srv9.akinator.com:9131",
            "kr": "https://srv2.akinator.com:9156",
            "tr": "https://srv3.akinator.com:9164",
            "nl": "https://srv9.akinator.com:9133",
            "pl": "https://srv7.akinator.com:9143",
        }
        self.games = {}

    @commands.group(aliases=["aki"], brief=_("Starts an akinator session."))
    @locale_doc
    async def akinator(self, ctx):
        _(
            """Play akinator. The game is controlled via the reactions on the embed.
            \U000021A9 stands for undo, \U00002139 shows the current info.

            To change the language, use `{prefix}akinator language`."""
        )
        if ctx.invoked_subcommand:
            return
        if self.games.get(ctx.channel.id):
            return await ctx.send(
                _(
                    "⚠ There is another akinator game in this channel"
                    " currently... Please wait until it finishes!"
                ),
                delete_after=10,
            )
        try:
            api_url = (
                await self.bot.redis.execute("GET", f"aki:language:{ctx.author.id}")
            ).decode("utf-8")
        except AttributeError:
            # if there is no key, we cannot decode it
            api_url = "https://srv2.akinator.com:9157"
        akinator = GameBase(
            self.bot,
            ctx,
            [k for k, v in self.regions.items() if v == api_url][0],
            api_url,
        )
        self.games[ctx.channel.id] = akinator
        await akinator.create_session()
        del self.games[ctx.channel.id]

    @akinator.command(aliases=["lang"])
    async def language(self, ctx):
        _("""Set your preferred language for the Akinator games.""")
        choice_list = [
            f"`{region_code}` - :flag_{region_code}:"
            for region_code in self.regions.keys()
        ]
        choice = await self.bot.paginator.ChoosePaginator(
            title=_("Pick your language!"),
            length=1,
            entries=choice_list,
            choices=list(range(len(choice_list))),
        ).paginate(ctx)
        if choice == 5:
            # if choice is us, we don't need to store the key (less data to store)
            await self.bot.redis.execute("DEL", f"aki:language:{ctx.author.id}")
        await self.bot.redis.execute(
            "SET", f"aki:language:{ctx.author.id}", list(self.regions.values())[choice]
        )
        await ctx.send(
            _(":white_check_mark: Your language has been updated succcessfully"),
            delete_after=10,
        )


class GameBase:
    def __init__(self, bot, ctx, language: str, api_url: str):
        self.ctx = ctx
        self.bot = bot
        self.signature = None
        self.aki_session = None
        self.step = None
        self.progress = 0
        self.msg = None
        if language == "us":
            self.language = "en"
        else:
            self.language = language
        self.api_url = api_url
        self.uid_ext_session = None
        self.frontaddr = None
        self.common_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101"
                " Firefox/61.0"
            ),
        }

    def __repr__(self):
        return (
            f"<GameBase step={self.step} progress={self.progress}"
            f" userid={self.ctx.author.id} channelid={self.ctx.channel.id}>"
        )

    async def get_uid_ext_session(self):
        async with self.bot.session.get(
            f"https://{self.language}.akinator.com/game"
        ) as req:
            html = await req.text()
        self.uid_ext_session = findall("var uid_ext_session = '([^']+)';", html)[0]
        self.frontaddr = findall("var frontaddr = '([^']+)';", html)[0]

    async def create_session(self, region_shortcode: str = "en"):
        await self.get_uid_ext_session()
        params = {
            "callback": "",
            "partner": 1,
            "player": "website-desktop",
            "uid_ext_session": self.uid_ext_session,
            "frontaddr": self.frontaddr,
            "constraint": "ETAT<>'AV'",
            "soft_constraint": "",
            "question_filter": "cat=1",  # NSFW filtering
            "_": int(time()),
        }
        async with self.bot.session.get(
            f"{self.api_url}/ws/new_session", headers=self.common_headers, params=params
        ) as req:
            response = loads(await req.text())
        if not response.get("completion"):
            raise ConnectionError(_("No results..."))
        if response["completion"] == "OK":
            try:
                self.aki_session = response["parameters"]["identification"]["session"]
                self.signature = response["parameters"]["identification"]["signature"]
                self.step = int(response["parameters"]["step_information"]["step"])
                question = response["parameters"]["step_information"]["question"]
                answers = response["parameters"]["step_information"]["answers"]
            except KeyError as e:
                await self.ctx.send(
                    _(":x: Response error (reason: `missing keys`)"), delete_after=10
                )
                raise commands.CommandInvokeError(e)
            answer = await self.question_paginator(question, answers)
            if answer == "nochoice":
                return await self.ctx.send(_("You didn't choose anything..."))
            await self.do_step(answer)
        else:
            await self.error_handler(response["completion"])

    async def do_step(self, answer: int):
        params = {
            "callback": "",
            "session": self.aki_session,
            "signature": self.signature,
            "step": self.step,
            "answer": answer,
            "question_filter": "cat=1",  # NSFW filtering
            "_": int(time()),
        }
        async with self.bot.session.get(
            f"{self.api_url}/ws/answer", headers=self.common_headers, params=params
        ) as req:
            response = loads(await req.text())
        if not response.get("completion"):
            raise ConnectionError(_("No results..."))
        if response["completion"] == "OK":
            try:
                self.step = int(response["parameters"]["step"])
                self.progress = round(float(response["parameters"]["progression"]))
                question = response["parameters"]["question"]
                answers = response["parameters"]["answers"]
            except KeyError as e:
                await self.ctx.send(
                    _(":x: Response error (reason: `missing keys`)"), delete_after=10
                )
                raise commands.CommandInvokeError(e)
            answer = await self.question_paginator(question, answers)
            await self.progress_check(answer)
        else:
            await self.error_handler(response["completion"])

    async def undo_step(self):
        params = {
            "callback": "",
            "session": self.aki_session,
            "signature": self.signature,
            "step": self.step,
            "answer": -1,
            "question_filter": "cat=1",  # NSFW filtering
            "_": int(time()),
        }
        async with self.bot.session.get(
            f"{self.api_url}/ws/answer", headers=self.common_headers, params=params
        ) as req:
            response = loads(await req.text())
        if not response.get("completion"):
            raise ConnectionError(_("No results..."))
        if response["completion"] == "OK":
            try:
                self.step = int(response["parameters"]["step"])
                self.progress = round(float(response["parameters"]["progression"]))
                question = response["parameters"]["question"]
                answers = response["parameters"]["answers"]
            except KeyError as e:
                await self.ctx.send(
                    _(":x: Response error (reason: `missing keys`)"), delete_after=10
                )
                raise commands.CommandInvokeError(e)
            answer = await self.question_paginator(question, answers)
            await self.progress_check(answer)
        else:
            await self.error_handler(response["completion"])

    async def progress_check(self, answer: int):
        if self.progress < 95 and answer not in ["undo", "current", "nochoice"]:
            await self.do_step(answer)
        elif answer == "undo":
            await self.undo_step()
        elif answer == "nochoice":
            # session timed out
            return await self.ctx.send(_("You didn't choose anything..."))
        else:
            # this will handle the current choice too
            await self.check_first_guess()

    async def check_first_guess(self):
        params = {
            "callback": "",
            "session": self.aki_session,
            "signature": self.signature,
            "step": self.step,
            "size": 2,
            "max_pic_width": 246,
            "max_pic_height": 294,
            "pref_photos": "VO-OK",
            "duel_allowed": 1,
            "mode_question": 0,
            "_": int(time()),
        }
        async with self.bot.session.get(
            f"{self.api_url}/ws/list", headers=self.common_headers, params=params
        ) as req:
            response = loads(await req.text())
        if not response.get("completion"):
            raise ConnectionError(_("No results..."))
        if response["completion"] == "OK" and len(
            response["parameters"].get("elements", [])
        ):
            try:
                name = response["parameters"]["elements"][0]["element"]["name"]
                description = response["parameters"]["elements"][0]["element"][
                    "description"
                ]
                ranking = int(
                    response["parameters"]["elements"][0]["element"]["ranking"]
                )
                image_url = (
                    response["parameters"]["elements"][0]["element"][
                        "absolute_picture_path"
                    ]
                    or None
                )
            except KeyError as e:
                await self.ctx.send(
                    _(":x: Response error (reason: `missing keys`)"), delete_after=10
                )
                raise commands.CommandInvokeError(e)
            await self.ctx.send(
                embed=await self.guess_embed(name, description, ranking, image_url)
            )
            try:
                await self.msg.delete()
            except discord.HTTPException:
                pass
        else:
            await self.error_handler(response["completion"])

    async def error_handler(self, completion: str):
        if completion == "WARN - NO QUESTION":
            return await self.ctx.send(_("Bravo, you defeated me! :blush:"))
        elif completion == "KO - SERVER DOWN":
            return await self.ctx.send(
                _(
                    "The server for the choosen language isn't available now... Please"
                    " check back later or choose another language!"
                )
            )
        elif completion == "KO - ELEM LIST IS EMPTY":
            return await self.ctx.send(_("There are no results."))
        else:
            await self.ctx.send(
                _(
                    ":x: Ouch, that's an unknown error... Please start a new session or"
                    " notify the devs."
                ),
                delete_after=10,
            )
            raise ConnectionError(_("Bad API response"))

    async def guess_embed(
        self, name: str, description: str, ranking: int, image_url: str
    ):
        embed = discord.Embed(
            title=_("My guess is {name}").format(name=name),
            description=_(
                "Extra information: {description}\nRanking: {ranking}"
            ).format(description=description, ranking=ranking),
            color=discord.Color.gold(),
        )
        if image_url:
            embed.set_thumbnail(url=image_url)
        return embed

    async def question_paginator(self, question: str, answers: list):
        if self.step >= 15 and self.step % 5 == 0:
            is_guessable = True
        else:
            is_guessable = False
        if not self.step == 0:
            is_undoable = True
        else:
            is_undoable = False
        question_ = _("Question")
        if not self.msg:
            self.msg = await self.ctx.send(_("Loading..."))
        return await self.bot.paginator.Akinator(
            entries=[f"`{answer['answer']}`" for answer in answers],
            return_index=True,
            title=f"{question} - {self.step+1}. {question_}",
            colour=get_colour(self.progress),
            footer_icon=self.ctx.author.avatar.url,
            footer_text=_("Playing with {user}").format(user=self.ctx.disp),
            undo=is_undoable,
            view_current=is_guessable,
            msg=self.msg,
            delete=False,
        ).paginate(self.ctx)


def setup(bot):
    bot.add_cog(Akinator(bot))
