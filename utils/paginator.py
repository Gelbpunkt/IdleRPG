"""
Original, main Paginator class written by EvieePy
Modified by the IdleRPG Project

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

The MIT License (MIT)
Copyright (c) 2018 EvieePy
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import asyncio

from typing import Any, Generator

import discord

from discord.ext import commands

from classes.context import Context
from classes.errors import NoChoice
from utils.i18n import _


def pager(
    entries: list[Any] | tuple[Any], chunk: int
) -> Generator[list[Any] | tuple[Any, ...], None, None]:
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]


class TextPaginator:
    __slots__ = ("ctx", "reactions", "_paginator", "current", "message", "update_lock")

    def __init__(
        self, ctx: "Context", prefix: str | None = None, suffix: str | None = None
    ) -> None:
        self._paginator = commands.Paginator(
            prefix=prefix, suffix=suffix, max_size=1950
        )
        self.current = 0
        self.message: discord.Message | None = None
        self.ctx = ctx
        self.update_lock = asyncio.Semaphore(value=2)
        self.reactions = {
            "⏮": "first",
            "◀": "previous",
            "⏹": "stop",
            "▶": "next",
            "⏭": "last",
            "🔢": "choose",
        }

    @property
    def pages(self) -> list[str]:
        return self._paginator.pages

    @property
    def page_count(self) -> int:
        return len(self.pages)

    async def add_line(self, line: str) -> None:
        before = self.page_count
        if isinstance(line, str):
            self._paginator.add_line(line)
        else:
            for _line in line:
                self._paginator.add_line(_line)
        after = self.page_count
        if after > before:
            self.current = after - 1
        asyncio.create_task(self.update())

    async def react(self) -> None:
        if self.message is None:
            raise Exception("May not be called before sending the message.")
        for emoji in self.reactions:
            await self.message.add_reaction(emoji)

    async def send(self) -> None:
        self.message = await self.ctx.send(
            self.pages[self.current] + f"Page {self.current + 1} / {self.page_count}"
        )
        asyncio.create_task(self.react())
        asyncio.create_task(self.listener())

    async def update(self) -> None:
        if self.update_lock.locked():
            return

        async with self.update_lock:
            if self.update_lock.locked():
                await asyncio.sleep(1)
            if not self.message:
                await asyncio.sleep(0.5)
            else:
                await self.message.edit(
                    content=self.pages[self.current]
                    + f"Page {self.current + 1} / {self.page_count}"
                )

    async def listener(self) -> None:
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == self.ctx.author
                and self.message is not None
                and reaction.message.id == self.message.id
                and reaction.emoji in self.reactions
            )

        while not self.ctx.bot.is_closed():
            try:
                reaction, user = await self.ctx.bot.wait_for(
                    "reaction_add", check=check, timeout=120
                )
            except asyncio.TimeoutError:
                if self.message is not None:
                    await self.message.delete()
                return
            action = self.reactions[reaction.emoji]
            if action == "first":
                self.current = 0
            elif action == "previous" and self.current != 0:
                self.current -= 1
            elif action == "next" and self.page_count != self.current + 1:
                self.current += 1
            elif action == "last":
                self.current = self.page_count - 1
            elif action == "stop":
                if self.message is not None:
                    await self.message.delete()
                return
            elif action == "choose":
                choose_msg = await self.ctx.send(
                    _("Please send a number between 1 and {max_pages}").format(
                        max_pages=self.page_count + 1
                    )
                )

                def new_check(msg):
                    return (
                        msg.author.id == self.ctx.author.id
                        and msg.content.isdigit()
                        and 0 < int(msg.content) <= self.page_count
                    )

                try:
                    m = await self.ctx.bot.wait_for(
                        "message", check=new_check, timeout=30
                    )
                    await choose_msg.delete()
                except TimeoutError:
                    if self.message is not None:
                        await self.message.delete()
                    await self.ctx.send(
                        _("Took too long to choose a number. Cancelling.")
                    )
                    return
                self.current = int(m.content) - 1
            await self.update()


class Paginator:
    def __init__(
        self,
        extras: list[discord.Embed] = [],
        title: str = "Untitled",
        footer: str | None = None,
        colour: int | None = None,
        entries: list[str] = [],
        fmt: str = "",
        prepend: str = "",
        append: str = "",
        length: int = 10,
        timeout: int = 30,
        return_index: bool = False,
    ):
        self.extras = extras
        self.entries = entries
        self.title = title
        self.footer = footer
        self.timeout = timeout
        self.return_index = return_index
        self.length = length
        self.colour = colour
        self.fmt = fmt
        self.prepend = prepend
        self.append = append
        self.pages = []

    def formatter(self, chunk):
        return "\n".join(
            f"{self.prepend}{self.fmt}{value}{self.fmt[::-1]}{self.append}"
            for value in chunk
        )

    async def paginate(self, ctx, location=None, user=None) -> None:
        if self.colour is None:
            self.colour = ctx.bot.config.game.primary_colour

        if self.extras:
            self.pages = [p for p in self.extras if isinstance(p, discord.Embed)]

        if self.entries:
            chunks = list(pager(self.entries, self.length))

            for index, chunk in enumerate(chunks):
                page = discord.Embed(
                    title=f"{self.title} - {index + 1}/{len(chunks)}", color=self.colour
                )
                page.description = self.formatter(chunk)

                if self.footer:
                    page.set_footer(text=self.footer)
                self.pages.append(page)

        view = NormalPaginator(ctx, self.pages, timeout=self.timeout)

        await view.start(location or ctx, user=user)


class ChooseLong(discord.ui.View):
    def __init__(
        self,
        ctx: Context,
        future: asyncio.Future,
        pages: list[discord.Embed],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.future = future
        self.current = 0
        self.pages = pages
        self.max = len(self.pages) - 1
        self.message: discord.Message | None = None
        self.allowed_user = ctx.author

    async def start(
        self,
        messagable: discord.abc.Messageable,
        user: discord.User | None = None,
    ) -> None:
        self.allowed_user = (
            user
            if user
            else (
                messagable
                if isinstance(messagable, (discord.User, discord.Member))
                else self.ctx.author
            )
        )
        self.message = await messagable.send(embed=self.pages[0], view=self)

    def cleanup(self) -> None:
        asyncio.create_task(self.message.delete())

    async def update(self) -> None:
        await self.message.edit(embed=self.pages[self.current])

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
        self.future.set_exception(NoChoice("You didn't choose anything."))

    @discord.ui.button(label="First", style=discord.ButtonStyle.blurple, row=0)
    async def first(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != 0:
            self.current = 0
            await self.update()

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple, row=0)
    async def previous(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != 0:
            self.current -= 1
            await self.update()

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, row=0)
    async def stop_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        await self.on_timeout()
        self.stop()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, row=0)
    async def next(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != self.max:
            self.current += 1
            await self.update()

    @discord.ui.button(label="Last", style=discord.ButtonStyle.blurple, row=0)
    async def last(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != self.max:
            self.current = self.max
            await self.update()

    async def handle(
        self, interaction: discord.Interaction, selected: str | int
    ) -> None:
        self.future.set_result(selected)
        self.stop()
        self.cleanup()


class NormalPaginator(ChooseLong):
    def __init__(
        self,
        ctx: Context,
        pages: list[discord.Embed],
        *args,
        **kwargs,
    ) -> None:
        super(ChooseLong, self).__init__(*args, **kwargs)
        self.ctx = ctx
        self.current = 0
        self.pages = pages
        self.max = len(self.pages) - 1

    async def on_timeout(self) -> None:
        self.cleanup()

    async def handle(
        self, interaction: discord.Interaction, selected: str | int
    ) -> None:
        self.stop()
        self.cleanup()


class ChooseShop(NormalPaginator):
    def __init__(
        self,
        ids: list[int],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ids = ids

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.green, row=1, emoji="💰")
    async def buy(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        item_id = self.ids[self.current]
        command = self.ctx.bot.get_command("buy")
        if not await command.can_run(self.ctx):
            return await interaction.response.send_message(
                _("You don't have a character anymore."), ephemeral=True
            )
        if not await self.ctx.invoke(command, itemid=item_id):
            return
        del self.pages[self.current]
        del self.ids[self.current]

        if len(self.pages) == 0:
            self.stop()
            self.cleanup()
            return

        if self.current == self.max:
            self.current -= 1

        self.max = len(self.pages) - 1
        self.pages = [
            page.set_footer(
                text=_("Item {num} of {total}").format(
                    num=idx + 1, total=len(self.pages)
                )
            )
            for idx, page in enumerate(self.pages)
        ]

        await self.update()


class ShopPaginator:
    def __init__(
        self,
        entries: list[tuple[discord.Embed, int]] = [],
    ):
        self.entries = entries

    async def paginate(self, ctx, location=None, user=None) -> None:
        embeds = [i[0] for i in self.entries]
        ids = [i[1] for i in self.entries]
        view = ChooseShop(ids, ctx, embeds, timeout=90)

        await view.start(location or ctx)


class ChoosePaginator:
    def __init__(
        self,
        placeholder: str | None = None,
        choices: list[str] | None = None,
        extras: list[discord.Embed] = [],
        title: str = "Untitled",
        footer: str | None = None,
        colour: int | None = None,
        entries: list[str] = [],
        fmt: str = "",
        prepend: str = "",
        append: str = "",
        length: int = 10,
        timeout: int = 30,
        return_index: bool = False,
    ):
        self.extras = extras
        self.entries = entries
        self.placeholder = placeholder or title
        self.title = title
        self.footer = footer
        self.choices = choices or entries
        self.timeout = timeout
        self.return_index = return_index
        self.length = length
        self.colour = colour
        self.fmt = fmt
        self.prepend = prepend
        self.append = append
        self.pages = []

        entry_count = len(self.entries) + len(self.extras)
        assert entry_count == len(self.choices)
        assert 2 <= entry_count <= 25

    def formatter(self, chunk):
        return "\n".join(
            f"{self.prepend}{self.fmt}{value}{self.fmt[::-1]}{self.append}"
            for value in chunk
        )

    async def paginate(self, ctx, location=None, user=None) -> str:
        if self.colour is None:
            self.colour = ctx.bot.config.game.primary_colour

        if self.extras:
            self.pages = [p for p in self.extras if isinstance(p, discord.Embed)]

        if self.entries:
            chunks = list(pager(self.entries, self.length))

            for index, chunk in enumerate(chunks):
                page = discord.Embed(
                    title=f"{self.title} - {index + 1}/{len(chunks)}", color=self.colour
                )
                page.description = self.formatter(chunk)

                if self.footer:
                    page.set_footer(text=self.footer)
                self.pages.append(page)

        future = asyncio.Future()
        view = ChooseLong(ctx, future, self.pages, timeout=self.timeout)
        select = ChooseSelect(
            placeholder=self.placeholder,
            return_index=self.return_index,
            row=1,
        )
        for index, choice in enumerate(self.choices):
            if not self.return_index:
                select.add_option(label=choice)
            else:
                select.add_option(label=choice, value=f"{index}")

        view.add_item(select)

        await view.start(location or ctx, user=user)

        return await future


class ChooseView(discord.ui.View):
    def __init__(
        self, ctx: commands.Context, future: asyncio.Future, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.future = future
        self.allowed_user = ctx.author

    async def start(
        self,
        embed: discord.Embed,
        messagable: discord.abc.Messageable,
        user: discord.User | None,
    ) -> None:
        self.allowed_user = (
            user
            if user
            else messagable
            if isinstance(messagable, (discord.User, discord.Member))
            else self.ctx.author
        )
        self.message = await messagable.send(embed=embed, view=self)

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
        self.future.set_exception(NoChoice("You didn't choose anything."))

    async def handle(
        self, interaction: discord.Interaction, selected: str | int
    ) -> None:
        self.future.set_result(selected)
        self.stop()
        await interaction.message.edit(view=discord.ui.View())


class ChooseSelect(discord.ui.Select):
    def __init__(self, return_index: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.return_index = return_index

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.return_index:
            await self._view.handle(interaction, int(self.values[0]))
        else:
            await self._view.handle(interaction, self.values[0])


class Choose:
    def __init__(
        self,
        entries: list[str],
        title: str = "Untitled",
        placeholder: str | None = None,
        choices: list[str] | None = None,
        footer: str | None = None,
        colour: int | None = None,
        timeout: int = 30,
        return_index: bool = False,
    ):
        self.entries = entries
        self.placeholder = placeholder or title
        self.choices = choices if choices is not None else entries
        self.title = title
        self.footer = footer
        self.colour = colour
        self.timeout = timeout
        self.return_index = return_index

        assert len(self.entries) == len(self.choices)
        assert 2 <= len(self.entries) <= 25

    async def paginate(self, ctx, location=None, user=None) -> str:
        if self.colour is None:
            self.colour = ctx.bot.config.game.primary_colour

        future = asyncio.Future()
        view = ChooseView(ctx, future, timeout=self.timeout)
        select = ChooseSelect(
            placeholder=self.placeholder, return_index=self.return_index
        )
        em = discord.Embed(title=self.title, description="", colour=self.colour)
        for index, chunk in enumerate(self.entries):
            em.description = f"{em.description}\U0001f539 {chunk}\n"
            if not self.return_index:
                select.add_option(label=self.choices[index])
            else:
                select.add_option(label=self.choices[index], value=f"{index}")

        if self.footer:
            em.set_footer(text=self.footer)

        view.add_item(select)

        await view.start(em, location or ctx, user=user)

        return await future
