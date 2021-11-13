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
from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

import discord

from discord.ext import commands

from classes.errors import NoChoice
from utils.i18n import _

if TYPE_CHECKING:
    from classes.bot import Bot


class Confirmation(discord.ui.View):
    def __init__(
        self,
        text: str,
        ctx: Context,
        future: asyncio.Future,
        user: discord.User,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.text = text
        self.ctx = ctx
        self.future = future
        self.allowed_user = user
        self.message: discord.Message | None = None

    async def start(
        self,
    ) -> None:
        self.message = await self.ctx.send(
            embed=discord.Embed(
                title=_("Confirmation"),
                description=self.text,
                colour=discord.Colour.blurple(),
            ),
            view=self,
        )

    def cleanup(self) -> None:
        asyncio.create_task(self.message.delete())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.allowed_user.id == interaction.user.id:
            return True
        else:
            asyncio.create_task(
                interaction.response.send_message(
                    _("This command was not initiated by you."), ephemeral=True
                )
            )
            return False

    async def on_timeout(self) -> None:
        self.cleanup()
        self.future.set_exception(NoChoice(_("You didn't choose anything.")))

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.red, row=0)
    async def no(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.future.set_result(False)
        self.stop()
        self.cleanup()

    @discord.ui.button(emoji="✔️", style=discord.ButtonStyle.green, row=0)
    async def yes(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.future.set_result(True)
        self.stop()
        self.cleanup()


class Context(commands.Context):
    """
    A custom version of the default Context.
    We use it to provide a shortcut to the display name and
    for escaping massmentions in ctx.send.
    """

    bot: Bot

    @property
    def disp(self) -> str:
        return self.author.display_name

    def __repr__(self):
        return "<Context>"

    async def confirm(
        self,
        message: str,
        timeout: int = 20,
        user: discord.User | discord.Member | None = None,
    ) -> bool:
        future: asyncio.Future[bool] = asyncio.Future()
        await Confirmation(
            message, self, future, user=user or self.author, timeout=timeout
        ).start()
        confirmed = await future

        if confirmed:
            return confirmed
        else:
            await self.bot.reset_cooldown(self)
            if self.command.root_parent:
                if self.command.root_parent.name == "guild":
                    await self.bot.reset_guild_cooldown(self)
                elif self.command.root_parent.name == "alliance":
                    await self.bot.reset_alliance_cooldown(self)
            return False
