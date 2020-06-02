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
import discord

from discord.ext import commands

from classes.converters import MemberConverter
from utils import random
from utils.i18n import _, locale_doc


def is_starlit():
    def predicate(ctx):
        return ctx.author.id == 549379625587834898

    return commands.check(predicate)


def is_zinquo():
    def predicate(ctx):
        return ctx.author.id == 189929542465355776

    return commands.check(predicate)


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        hidden=True, brief=_("In loving memory of Mary Johanna, ex-developer.")
    )
    @locale_doc
    async def onetruechild(self, ctx):
        _(
            """*In loving memory of Mary Johanna, ex-developer.*

            This custom command was added on May 15th 2019 and references the name of the child (ex-)developer Mary Johanna had with User Terror.
            Anyone can use this command."""
        )
        await ctx.send(_("His name is `#no homo` :heart:"))

    @commands.command(hidden=True, brief=_("Use to have Jester cast a spell ✨"))
    @locale_doc
    async def jester(self, ctx):
        _(
            """*Use to have Jester cast a spell ✨*

            This custom command was added on November 30th 2019, requested by User Jester😈🍭LaVorre.
            Anyone can use this command."""
        )
        await ctx.send(
            random.choice(
                [
                    _(
                        "Jester casts Spirit Guardians on herself. She, and the"
                        " spiritual hamster unicorns have a dance party."
                    ),
                    _(
                        "Jester casts Spiritual Weapon. A comically large spectral"
                        " lollipop🍭 suddenly appears."
                    ),
                    _(
                        "Jester casts Invoke Duplicity.... Now there's twice the Jester"
                        " for twice the pranks!"
                    ),
                ]
            )
        )

    @commands.command(brief=_("It's a secret."))
    @locale_doc
    async def secret(self, ctx):
        _(
            """*It's a secret.*

            This custom command was added on August 22nd 2019, requested by User Terror.
            Anyone can use this command."""
        )
        await ctx.send(
            embed=discord.Embed(
                title=_("Gotcha"), description=_("Shhh, it's a secret!")
            ).set_image(
                url="https://cdn.discordapp.com/attachments/571201192382693376/613965413801263104/image0.jpg"
            ),
            delete_after=3,
        )

    @commands.command(hidden=True, brief=_("Kill someone."))
    async def kill(self, ctx, target: MemberConverter):
        _(
            """`<target>` - A discord user

            *Kill someone.*

            This custom command was added on September 22nd 2019, requested by User Stevelion.
            Anyone can use this command."""
        )
        await ctx.send(
            embed=discord.Embed(
                title=f"{target} has been killed by {ctx.author}."
            ).set_image(
                url="https://media.discordapp.net/attachments/439779845673844739/625403834033766428/kill.gif"
            )
        )

    @is_zinquo()
    @commands.command(hidden=True, brief=_("Summon phoenix"))
    async def phoenix(self, ctx):
        _(
            """This custom command was added on October 23rd by User Zinquo, referencing Greek Mythology.
            Only Zinquo can use this command."""
        )
        await ctx.send(
            "> “When the bones settle and all the ash falls, the phoenix will be"
            " reborn, and life begins anew.”"
        )

    @is_starlit()
    @commands.command(hidden=True, brief=_("Lick someone"))
    async def lick(self, ctx, *, user: MemberConverter):
        _(
            """`<target>` - A discord user

            *Get someone in sick and loving way.*

            This command was added on March 12th 2020, requested by User Little Starlit.
            Only Little Starlit can use this command."""
        )
        await ctx.send(
            embed=discord.Embed(
                title=f"{ctx.author} licks {user}!", colour=ctx.author.colour
            ).set_image(
                url=random.choice(
                    [
                        "https://i.imgur.com/LiLbLw0.gif",
                        "https://i.imgur.com/9tU0AFl.gif",
                    ]
                )
            )
        )


def setup(bot):
    bot.add_cog(Custom(bot))
