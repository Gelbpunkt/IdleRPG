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
from discord.ext import commands

from utils.i18n import _, locale_doc


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


def setup(bot):
    bot.add_cog(Custom(bot))
