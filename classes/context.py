"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import re

from discord.ext import commands


class Context(commands.Context):
    """
    A custom version of the default Context.
    We use it to provide a shortcut to the display name and
    for escaping massmentions in ctx.send.
    """

    @property
    def disp(self):
        return self.author.display_name

    async def send(self, content=None, *args, **kwargs):
        escape_massmentions = kwargs.get("escape_massmentions", True)
        escape_mentions = kwargs.get("escape_mentions", False)
        if escape_massmentions and content:
            content = content.replace("@here", "@\u200bhere").replace(
                "@everyone", "@\u200beveryone"
            )
        if escape_mentions and content:
            # There is 2 options here:
            # #1 Simple replace
            # content = re.sub(r"@([!&]?[0-9]{17,21})", "@\u200b\\1", content)
            #
            # #2 Advanced replace (gets matches and replaces with user repr)
            content = re.sub(
                r"<@[!&]?([0-9]{17,21})>",
                lambda x: f"@{self.bot.get_user(int(x.group(1)))}",
                content,
            )
        try:
            del kwargs["escape_mentions"]
        except KeyError:
            pass
        try:
            del kwargs["escape_massmentions"]
        except KeyError:
            pass

        return await super().send(content, *args, **kwargs)
