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
from asyncio import Future, TimeoutError
from typing import Awaitable, Callable

from discord.interactions import Interaction
from discord.ui import Button, View
from discord.user import User

from utils.i18n import _


class JoinView(View):
    def __init__(self, join_button: Button, message: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = message
        join_button.callback = self.button_pressed
        self.add_item(join_button)
        self.joined: set[User] = set()

    async def button_pressed(self, interaction: Interaction) -> None:
        if interaction.user not in self.joined:
            self.joined.add(interaction.user)
            await interaction.response.send_message(self.message, ephemeral=True)
        else:
            await interaction.response.send_message(
                _("You already joined."), ephemeral=True
            )


class SingleJoinView(View):
    def __init__(
        self,
        future: Future[User],
        join_button: Button,
        allowed: User | None = None,
        prohibited: User | None = None,
        check: Callable[[User], Awaitable[bool]] | None = None,
        check_fail_message: str | None = None,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        join_button.callback = self.button_pressed
        self.add_item(join_button)
        self.future = future
        self.allowed = allowed
        self.prohibited = prohibited
        self.check = check
        self.check_fail_message = check_fail_message

    async def button_pressed(self, interaction: Interaction) -> None:
        if interaction.user is None:
            return
        if self.allowed is not None and self.allowed != interaction.user:
            await interaction.response.send_message(
                _("You aren't allowed to join."), ephemeral=True
            )
            return
        if self.prohibited is not None and self.prohibited == interaction.user:
            await interaction.response.send_message(
                _("You are prohibited from joining."), ephemeral=True
            )
            return

        if await self.check(interaction.user):
            self.future.set_result(interaction.user)
            self.stop()
        else:
            await interaction.response.send_message(
                self.check_fail_message, ephemeral=True
            )

    async def on_timeout(self) -> None:
        self.future.set_exception(TimeoutError())
