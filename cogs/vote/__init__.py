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
from discord.ext import commands

from utils.i18n import _, locale_doc


class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=_("Vote for the bot on top.gg"))
    @locale_doc
    async def vote(self, ctx):
        _(
            """Vote me up to get a random crate!

            You may receive a common crate (89%), an uncommon crate (6%), a rare crate (4%), a magic crate (0.9%) or a legendary crate (0.1%)

            If your vote was not registered, make sure you are logged into the right account on https://discord.com/login and try again."""
        )
        await ctx.send(
            _(
                """\
Upvote me to receive a random crate! You will be rewarded a few seconds afterwards!
Each of the following links will reward you with one random crate upon voting:

- <https://top.gg/bot/idlerpg>
- <https://discord.ly/idlerpg>"""
            )
        )


def setup(bot):
    bot.add_cog(Vote(bot))
