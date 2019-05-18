"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
from asyncio import TimeoutError
import re

import discord
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

    async def confirm(self, message, timeout=20):
        emojis = ["\U0000274e", "\U00002705"] # no, yes
        msg = await self.send(embed=discord.Embed(title="Confirmation", description=message, colour=discord.Colour.blurple()))
        for emoji in emojis:
            await msg.add_reaction(emoji)
        def check(r, u):
            return u == self.author and str(r.emoji) in emojis and r.message.id == msg.id
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=timeout)
        except TimeoutError:
            return False
        return bool(emojis.index(str(reaction.emoji)))

    async def send(self, content=None, *args, **kwargs):
        escape_massmentions = kwargs.pop("escape_massmentions", True)
        escape_mentions = kwargs.pop("escape_mentions", False)
        content = str(content) if content is not None else None
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

        return await super().send(content, *args, **kwargs)
