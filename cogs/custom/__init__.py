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
from discord import Embed
from discord.ext import commands

from classes.converters import MemberConverter
from utils.i18n import _, locale_doc


def is_exzyond():
    def predicate(ctx):
        return ctx.author.id == 422954629849022475

    return commands.check(predicate)


exz_emotions = {
    "hug": (
        "hugs",
        "https://media.tenor.com/images/d5c635dcb613a9732cfd997b6a048f80/tenor.gif",
    ),
    "cuddle": (
        "cuddles",
        "https://media.tenor.com/images/735ba60b011d4a1949c902167a1898f9/tenor.gif",
    ),
    "kiss": (
        "kisses",
        "https://media1.tenor.com/images/af1216d35f8ec076b593401b19ddd0bf/tenor.gif",
    ),
    "pat": (
        "pats",
        "https://media.tenor.com/images/ed6688a51ea92a8c1de0d58e0e4dcb86/tenor.gif",
    ),
    "slap": (
        "slaps",
        "https://media.tenor.com/images/f12ea58221df986b9d62eb1a95ee96e1/tenor.gif",
    ),
    "punch": (
        "punches",
        "https://media.tenor.com/images/df65530317816545e3d3754e647597ed/tenor.gif",
    ),
}


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_exzyond()
    @commands.command(
        hidden=True,
        brief=_("A custom command for ExZyond to express several emotions."),
        name="ExZ",
    )
    @locale_doc
    async def _exz(self, ctx, user: MemberConverter, emotion: str):
        _(
            """*A custom command for ExZyond to express several emotions.*

            This custom group of commands were added on December 1st 2020, requested by User ExZyond."""
        )
        if (picked_emotion := exz_emotions.get(emotion.lower())):
            await ctx.send(
                embed=Embed(
                    title=f"{ctx.author.display_name} {picked_emotion[0]} {user.display_name}."
                ).set_image(url=picked_emotion[1])
            )
        else:
            await ctx.send(
                f"You need to provide one from the following: `{', '.join(exz_emotions.keys())}`!"
            )


def setup(bot):
    bot.add_cog(Custom(bot))
