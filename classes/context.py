"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import datetime

from discord.ext import commands


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.launch_time = (
            datetime.datetime.now()
        )  # we assume the bot is created for use right now

        self.mention_formatter = commands.clean_content()

    @property
    def disp(self):
        return self.author.display_name

    @property
    def uptime(self):
        return self.launch_time - datetime.datetime.now()

    async def send_message(
        self,
        target,
        content=None,
        *,
        escape_mass_mentions=True,
        escape_mentions=False,
        **fields
    ):
        if escape_mass_mentions:
            content = content.replace("@here", "@\u200bhere").replace(
                "@everyone", "@\u200beveryone"
            )
        if escape_mentions:
            content = await self.mention_formatter.convert(self, content)

        await super(Context, self).send_message(target, content=content, **fields)
