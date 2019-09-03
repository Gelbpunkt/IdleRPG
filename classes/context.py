"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

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
import re

from asyncio import TimeoutError
from contextlib import suppress

import discord

from discord.ext import commands

from utils.paginator import NoChoice


class Context(commands.Context):
    """
    A custom version of the default Context.
    We use it to provide a shortcut to the display name and
    for escaping massmentions in ctx.send.
    """

    @property
    def disp(self):
        return self.author.display_name

    async def confirm(
        self,
        message,
        timeout=20,
        user=None,
        emoji_no="\U0000274e",
        emoji_yes="\U00002705",
    ):
        user = user or self.author
        emojis = (emoji_no, emoji_yes)
        
        if user.id == self.bot.user.id:
            return false

        msg = await self.send(
            embed=discord.Embed(
                title="Confirmation",
                description=message,
                colour=discord.Colour.blurple(),
            )
        )
        for emoji in emojis:
            await msg.add_reaction(emoji)

        def check(r, u):
            return u == user and str(r.emoji) in emojis and r.message.id == msg.id

        async def cleanup():
            with suppress(discord.HTTPException):
                await msg.delete()

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=timeout
            )
        except TimeoutError:
            await cleanup()
            raise NoChoice("You did not choose anything.")

        # finally statement should not be used for cleanup because it will be triggered
        # by bot shutdown/cancellation of command
        await cleanup()

        return bool(emojis.index(str(reaction.emoji)))

    async def send(self, content=None, *args, **kwargs):
        if content is not None:
            content = str(content)

            if kwargs.pop("escape_massmentions", True):
                content = content.replace("@here", "@\u200bhere").replace(
                    "@everyone", "@\u200beveryone"
                )
            if kwargs.pop("escape_mentions", False):
                # There are 2 options here:
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
