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
import random

from discord.ext import commands


class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_question(self, difficulty="easy"):
        if difficulty not in ("easy", "medium", "hard"):
            raise ValueError("invalid difficulty")
        async with self.bot.session.get(
            f"https://opentdb.com/api.php?amount=1&difficulty={difficulty}"
        ) as r:
            ret = await r.json()
        if ret["response_code"] != 0:
            raise Exception("response error")
        return ret["results"][0]

    async def get_response(self, ctx, question):
        entries = [question["correct_answer"]] + question["incorrect_answers"]
        random.sort(entries)
        answer = await self.bot.paginator.Choose(
            entries=entries,
            title=question["question"],
            footer=f"Difficulty: {question['difficulty']} | Category: {question['category']}",
            timeout=15,
        ).paginate(ctx)
        return answer == question["correct_answer"]

    @commands.command(aliases=["tr"])
    async def trivia(self, ctx, difficulty: str.lower = "easy"):
        _(
            """Answer a trivia question of a given difficulty, which may be easy, medium or hard."""
        )
        try:
            question = await self.get_question(difficulty)
        except ValueError:
            return await ctx.send(_("Invalid difficulty."))
        except Exception:
            return await ctx.send(_("Error generating question."))
        if await self.get_response(ctx, question):
            await ctx.send(_("{author}, correct!").format(author=ctx.author.mention))
        else:
            await ctx.send(
                _("{author}, wrong! Correct would have been: `{solution}`.").format(
                    author=ctx.author.mention, solution=question["correct_answer"]
                )
            )


def setup(bot):
    bot.add_cog(Trivia(bot))
