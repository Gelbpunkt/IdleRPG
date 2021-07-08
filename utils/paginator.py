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

from typing import Any, AsyncGenerator, Optional, Union

import discord

from discord.ext import commands

from classes.context import Context
from classes.errors import NoChoice
from utils.i18n import _


async def pager(
    entries: Union[list[Any], tuple[Any]], chunk: int
) -> AsyncGenerator[Union[list[Any], tuple[Any, ...]], None]:
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]


class TextPaginator:
    __slots__ = ("ctx", "reactions", "_paginator", "current", "message", "update_lock")

    def __init__(
        self, ctx: "Context", prefix: Optional[str] = None, suffix: Optional[str] = None
    ) -> None:
        self._paginator = commands.Paginator(
            prefix=prefix, suffix=suffix, max_size=1950
        )
        self.current = 0
        self.message: Optional[discord.Message] = None
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
        self.ctx.bot.loop.create_task(self.update())

    async def react(self) -> None:
        if self.message is None:
            raise Exception("May not be called before sending the message.")
        for emoji in self.reactions:
            await self.message.add_reaction(emoji)

    async def send(self) -> None:
        self.message = await self.ctx.send(
            self.pages[self.current] + f"Page {self.current + 1} / {self.page_count}"
        )
        self.ctx.bot.loop.create_task(self.react())
        self.ctx.bot.loop.create_task(self.listener())

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

    __slots__ = (
        "entries",
        "extras",
        "title",
        "description",
        "colour",
        "footer",
        "length",
        "prepend",
        "append",
        "fmt",
        "timeout",
        "ordered",
        "controls",
        "controller",
        "pages",
        "current",
        "previous",
        "eof",
        "base",
        "names",
    )

    def __init__(self, **kwargs: Any) -> None:
        self.entries = kwargs.get("entries", None)
        self.extras = kwargs.get("extras", None)

        self.title = kwargs.get("title", None)
        self.description = kwargs.get("description", None)
        self.colour = kwargs.get("colour", None)
        self.footer = kwargs.get("footer", None)

        self.length = kwargs.get("length", 10)
        self.prepend = kwargs.get("prepend", "")
        self.append = kwargs.get("append", "")
        self.fmt = kwargs.get("fmt", "")
        self.timeout = kwargs.get("timeout", 90)
        self.ordered = kwargs.get("ordered", False)

        self.controller = None
        self.pages: list[discord.Embed] = []
        self.base: Optional[discord.Message] = None

        self.current = 0
        self.previous = 0
        self.eof = 0

        self.controls = {
            "⏮": 0.0,
            "◀": -1,
            "⏹": "stop",
            "▶": +1,
            "⏭": None,
            "🔢": "choose",
        }

    async def indexer(self, ctx: "Context", ctrl: str) -> None:
        if self.base is None:
            raise Exception("Should not be called manually")
        if ctrl == "stop":
            ctx.bot.loop.create_task(self.stop_controller(self.base))

        elif ctrl == "choose":
            choose_msg = await ctx.send(
                _("Please send a number between 1 and {max_pages}").format(
                    max_pages=int(self.eof) + 1
                )
            )

            def check(msg):
                return (
                    msg.author.id == ctx.author.id
                    and msg.content.isdigit()
                    and 0 < int(msg.content) <= int(self.eof) + 1
                )

            try:
                m = await ctx.bot.wait_for("message", check=check, timeout=30)
                await choose_msg.delete()
            except TimeoutError:
                if self.base is not None:
                    await self.base.delete()
                await ctx.send(_("Took too long to choose a number. Cancelling."))
                return
            self.current = int(m.content) - 1

        elif isinstance(ctrl, int):
            self.current += ctrl
            if self.current > self.eof or self.current < 0:
                self.current -= ctrl
        else:
            self.current = int(ctrl)

    async def reaction_controller(self, ctx: "Context") -> None:
        bot = ctx.bot
        author = ctx.author

        if self.colour is None:
            self.colour = ctx.bot.config.game.primary_colour
        self.base = await ctx.send(embed=self.pages[0])

        if len(self.pages) == 1:
            await self.base.add_reaction("⏹")
        else:
            for reaction in self.controls:
                try:
                    await self.base.add_reaction(reaction)
                except discord.HTTPException:
                    return

        def check(r: discord.Reaction, u: discord.User) -> bool:
            if str(r) not in self.controls.keys():
                return False
            elif u.id == bot.user.id or r.message.id != self.base.id:
                return False
            elif u.id != author.id:
                return False
            return True

        while True:
            try:
                react, user = await bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                return ctx.bot.loop.create_task(self.stop_controller(self.base))

            control = self.controls.get(str(react))

            try:
                await self.base.remove_reaction(react, user)
            except discord.HTTPException:
                pass

            self.previous = self.current
            await self.indexer(ctx, control)

            if self.previous == self.current:
                continue

            try:
                await self.base.edit(embed=self.pages[self.current])
            except KeyError:
                pass

    async def stop_controller(self, message: discord.Message) -> None:
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            self.controller.cancel()
        except Exception:
            pass

    def formmater(self, chunk):
        return "\n".join(
            f"{self.prepend}{self.fmt}{value}{self.fmt[::-1]}{self.append}"
            for value in chunk
        )

    async def paginate(self, ctx):
        if self.extras:
            self.pages = [p for p in self.extras if isinstance(p, discord.Embed)]

        if not self.colour:
            self.colour = ctx.bot.config.game.primary_colour

        if self.entries:
            chunks = [c async for c in pager(self.entries, self.length)]

            for index, chunk in enumerate(chunks):
                page = discord.Embed(
                    title=f"{self.title} - {index + 1}/{len(chunks)}", color=self.colour
                )
                page.description = self.formmater(chunk)

                if hasattr(self, "footer"):
                    if self.footer:
                        page.set_footer(text=self.footer)
                self.pages.append(page)

        if not self.pages:
            raise ValueError(
                "There must be enough data to create at least 1 page for pagination."
            )

        self.eof = float(len(self.pages) - 1)
        self.controls["⏭"] = self.eof
        self.controller = ctx.bot.loop.create_task(self.reaction_controller(ctx))


class ShopPaginator:

    __slots__ = (
        "entries",
        "timeout",
        "controls",
        "controller",
        "pages",
        "current",
        "previous",
        "eof",
        "base",
        "names",
        "items",
    )

    def __init__(self, **kwargs: Any) -> None:
        self.entries = kwargs.get("entries", None)

        self.timeout = kwargs.get("timeout", 90)

        self.controller = None
        self.pages: list[tuple[discord.Embed, int]] = []
        self.base: Optional[discord.Message] = None

        self.current = 0
        self.previous = 0
        self.eof = 0

        self.controls = {
            "⏮": 0.0,
            "◀": -1,
            "⏹": "stop",
            "▶": +1,
            "⏭": None,
            "🔢": "choose",
            "💰": "buy",
        }

    async def indexer(self, ctx: "Context", ctrl: str) -> None:
        if self.base is None:
            raise Exception("Should not be called manually")
        if ctrl == "stop":
            ctx.bot.loop.create_task(self.stop_controller(self.base))

        elif ctrl == "choose":
            choose_msg = await ctx.send(
                _("Please send a number between 1 and {max_pages}").format(
                    max_pages=int(self.eof) + 1
                )
            )

            def check(msg):
                return (
                    msg.author.id == ctx.author.id
                    and msg.content.isdigit()
                    and 0 < int(msg.content) <= int(self.eof) + 1
                )

            try:
                m = await ctx.bot.wait_for("message", check=check, timeout=30)
                await choose_msg.delete()
            except TimeoutError:
                if self.base is not None:
                    await self.base.delete()
                await ctx.send(_("Took too long to choose a number. Cancelling."))
                return
            self.current = int(m.content) - 1

        elif ctrl == "buy":
            item_id = self.pages[self.current][1]
            await self.buy(ctx, item_id)

        elif isinstance(ctrl, int):
            self.current += ctrl
            if self.current > self.eof or self.current < 0:
                self.current -= ctrl
        else:
            self.current = int(ctrl)

    async def buy(self, ctx: "Context", item_id: int):
        command = ctx.bot.get_command("buy")
        if not await command.can_run(ctx):
            # ensures players have a character and updates ctx.character_data
            await ctx.send(
                _("Looks like you deleted your character in the meantime...")
            )
            ctx.bot.loop.create_task(self.stop_controller(self.base))
        if not await ctx.invoke(command, itemid=item_id):
            return
        del self.pages[self.current]
        if len(self.pages) == 0:
            ctx.bot.loop.create_task(self.stop_controller(self.base))
        self.eof -= 1
        self.controls["⏭"] = self.eof
        try:
            await self.base.edit(
                embed=self.pages[self.current][0].set_footer(
                    text=_("Item {num} of {total}").format(
                        num=self.current + 1, total=int(self.eof) + 1
                    )
                )
            )
        except IndexError:
            self.current -= 1
            await self.base.edit(
                embed=self.pages[self.current][0].set_footer(
                    text=_("Item {num} of {total}").format(
                        num=self.current + 1, total=int(self.eof) + 1
                    )
                )
            )

    async def reaction_controller(self, ctx: "Context") -> None:
        bot = ctx.bot
        author = ctx.author

        self.base = await ctx.send(embed=self.pages[0][0])

        if len(self.pages) == 1:
            await self.base.add_reaction("⏹")
            await self.base.add_reaction("💰")
        else:
            for reaction in self.controls:
                try:
                    await self.base.add_reaction(reaction)
                except discord.HTTPException:
                    return

        def check(r: discord.Reaction, u: discord.User) -> bool:
            if str(r) not in self.controls.keys():
                return False
            elif u.id == bot.user.id or r.message.id != self.base.id:
                return False
            elif u.id != author.id:
                return False
            return True

        while True:
            try:
                react, user = await bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                return ctx.bot.loop.create_task(self.stop_controller(self.base))

            control = self.controls.get(str(react))

            try:
                await self.base.remove_reaction(react, user)
            except discord.HTTPException:
                pass

            self.previous = self.current
            await self.indexer(ctx, control)

            if self.previous == self.current:
                continue

            try:
                await self.base.edit(
                    embed=self.pages[self.current][0].set_footer(
                        text=_("Item {num} of {total}").format(
                            num=self.current + 1, total=int(self.eof) + 1
                        )
                    )
                )
            except KeyError:
                pass

    async def stop_controller(self, message: discord.Message) -> None:
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            self.controller.cancel()
        except Exception:
            pass

    async def paginate(self, ctx):
        self.pages = [p for p in self.entries if isinstance(p[0], discord.Embed)]

        if not self.pages:
            raise ValueError(
                "There must be enough data to create at least 1 page for pagination."
            )

        self.eof = float(len(self.pages) - 1)
        self.controls["⏭"] = self.eof
        self.controller = ctx.bot.loop.create_task(self.reaction_controller(ctx))


class AdventurePaginator:

    __slots__ = (
        "embeds",
        "files",
        "timeout",
        "ordered",
        "controls",
        "controller",
        "pages",
        "current",
        "previous",
        "eof",
        "base",
        "names",
    )

    def __init__(self, **kwargs):
        self.embeds = kwargs["embeds"]
        self.files = kwargs["files"]
        self.timeout = kwargs.get("timeout", 90)
        self.ordered = kwargs.get("ordered", False)

        self.controller = None
        self.pages = []
        self.names = []
        self.base = None

        self.current = 0
        self.previous = 0
        self.eof = 0

        self.controls = {
            "⏮": 0.0,
            "◀": -1,
            "⏹": "stop",
            "▶": +1,
            "⏭": None,
            "🔢": "choose",
        }

    async def indexer(self, ctx, ctrl):
        if ctrl == "stop":
            ctx.bot.loop.create_task(self.stop_controller(self.base))

        elif ctrl == "choose":
            choose_msg = await ctx.send(
                _("Please send a number between 1 and {max_pages}").format(
                    max_pages=int(self.eof) + 1
                )
            )

            def check(msg):
                return (
                    msg.author.id == ctx.author.id
                    and msg.content.isdigit()
                    and 0 < int(msg.content) <= int(self.eof) + 1
                )

            try:
                m = await ctx.bot.wait_for("message", check=check, timeout=30)
                await choose_msg.delete()
            except TimeoutError:
                if self.base is not None:
                    await self.base.delete()
                await ctx.send(_("Took too long to choose a number. Cancelling."))
                return
            self.current = int(m.content) - 1

        elif isinstance(ctrl, int):
            self.current += ctrl
            if self.current > self.eof or self.current < 0:
                self.current -= ctrl
        else:
            self.current = int(ctrl)

    async def reaction_controller(self, ctx):
        bot = ctx.bot
        author = ctx.author

        self.base = await ctx.send(embed=self.pages[0], file=self.files[0])

        if len(self.pages) == 1:
            await self.base.add_reaction("⏹")
        else:
            for reaction in self.controls:
                try:
                    await self.base.add_reaction(reaction)
                except discord.HTTPException:
                    return

        def check(r, u):
            if str(r) not in self.controls.keys():
                return False
            elif u.id == bot.user.id or r.message.id != self.base.id:
                return False
            elif u.id != author.id:
                return False
            return True

        while True:
            try:
                react, user = await bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                return ctx.bot.loop.create_task(self.stop_controller(self.base))

            control = self.controls.get(str(react))

            try:
                await self.base.remove_reaction(react, user)
            except discord.HTTPException:
                pass

            self.previous = self.current
            await self.indexer(ctx, control)

            if self.previous == self.current:
                continue

            try:
                await self.base.delete()
                try:
                    self.files[self.current].reset()
                except ValueError:
                    return
                self.base = await ctx.send(
                    embed=self.pages[self.current], file=self.files[self.current]
                )
                for reaction in self.controls:
                    try:
                        await self.base.add_reaction(reaction)
                    except discord.HTTPException:
                        return
            except KeyError:
                pass

    async def stop_controller(self, message):
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            self.controller.cancel()
        except Exception:
            pass

    async def paginate(self, ctx):
        self.pages = [p for p in self.embeds if isinstance(p, discord.Embed)]

        if not self.pages:
            raise ValueError(
                "There must be enough data to create at least 1 page for pagination."
            )

        self.eof = float(len(self.pages) - 1)
        self.controls["⏭"] = self.eof
        self.controller = ctx.bot.loop.create_task(self.reaction_controller(ctx))


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

    def cleanup(self, interaction: discord.Interaction) -> None:
        asyncio.create_task(interaction.message.delete())

    async def update(self, interaction: discord.Interaction) -> None:
        await interaction.message.edit(embed=self.pages[self.current])

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.ctx.author.id == interaction.user.id:
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

    @discord.ui.button(label="First", style=discord.ButtonStyle.blurple, row=0)
    async def first(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current = 0
        await self.update(interaction)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple, row=0)
    async def previous(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != 0:
            self.current -= 1
        await self.update(interaction)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, row=0)
    async def stop_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        await self.on_timeout()
        self.stop()
        self.cleanup(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, row=0)
    async def next(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        if self.current != self.max:
            self.current += 1
        await self.update(interaction)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.blurple, row=0)
    async def last(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.current = self.max
        await self.update(interaction)

    async def handle(
        self, interaction: discord.Interaction, selected: Union[str, int]
    ) -> None:
        self.future.set_result(selected)
        self.stop()
        self.cleanup(interaction)


class ChoosePaginator:
    def __init__(
        self,
        placeholder: Optional[str] = None,
        choices: Optional[list[str]] = None,
        extras: list[discord.Embed] = [],
        title: str = "Untitled",
        footer: Optional[str] = None,
        colour: Optional[int] = None,
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
        assert not any(len(i) > 25 for i in self.choices)

    def formmater(self, chunk):
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
            chunks = [c async for c in pager(self.entries, self.length)]

            for index, chunk in enumerate(chunks):
                page = discord.Embed(
                    title=f"{self.title} - {index + 1}/{len(chunks)}", color=self.colour
                )
                page.description = self.formmater(chunk)

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

        if not location:
            await ctx.send(embed=self.pages[0], view=view)
        else:
            await location.send(embed=self.pages[0], view=view)

        return await future


class ChooseView(discord.ui.View):
    def __init__(
        self, ctx: commands.Context, future: asyncio.Future, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.future = future

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.ctx.author.id == interaction.user.id:
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
        self, interaction: discord.Interaction, selected: Union[str, int]
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
        placeholder: Optional[str] = None,
        choices: Optional[list[str]] = None,
        footer: Optional[str] = None,
        colour: Optional[int] = None,
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
        assert not any(len(i) > 25 for i in self.choices)

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

        if not location:
            await ctx.send(embed=em, view=view)
        else:
            await location.send(embed=em, view=view)

        return await future


class Akinator:
    def __init__(
        self,
        entries,
        title=None,
        footer_text=None,
        footer_icon=None,
        colour=None,
        timeout=30,
        return_index=False,
        undo=True,
        view_current=True,
        msg=None,
        delete=True,
    ):
        self.entries = entries
        self.title = title or "Untitled"
        self.footer_text = footer_text or discord.Embed.Empty
        self.footer_icon = footer_icon or discord.Embed.Empty
        self.colour = colour
        self.timeout = timeout
        self.return_index = return_index
        self.undo = undo
        self.view_current = view_current
        self.msg = msg
        self.delete = delete

    async def paginate(self, ctx):
        if len(self.entries) > 10:
            raise ValueError("Exceeds maximum size")
        elif len(self.entries) < 2:
            raise ValueError(
                "There must be enough data to create at least 1 page for choosing."
            )
        if self.colour is None:
            self.colour = ctx.bot.config.game.primary_colour
        em = discord.Embed(title=self.title, description="", colour=self.colour)
        self.emojis = []
        for index, chunk in enumerate(self.entries):
            if index < 9:
                self.emojis.append(f"{index+1}\u20e3")
            else:
                self.emojis.append("\U0001f51f")
            em.description = f"{em.description}{self.emojis[index]} {chunk}\n"

        em.set_footer(icon_url=self.footer_icon, text=self.footer_text)

        self.controller = em
        return await self.reaction_controller(ctx)

    async def reaction_placer(self, base):
        for emoji in self.emojis:
            await base.add_reaction(emoji)

        if self.undo:
            self.emojis.append("\U000021a9")
            await base.add_reaction("\U000021a9")
        if self.view_current:
            self.emojis.append("\U00002139")
            await base.add_reaction("\U00002139")

    async def reaction_controller(self, ctx):
        if not self.msg:
            base = await ctx.send(embed=self.controller)
        else:
            base = self.msg
            await self.msg.edit(content=None, embed=self.controller)

        place_task = ctx.bot.loop.create_task(self.reaction_placer(base))

        def check(r, u):
            if str(r) not in self.emojis:
                return False
            elif u.id == ctx.bot.user.id or r.message.id != base.id:
                return False
            elif u.id != ctx.author.id:
                return False
            return True

        try:
            react, user = await ctx.bot.wait_for(
                "reaction_add", check=check, timeout=self.timeout
            )
            place_task.cancel()
        except asyncio.TimeoutError:
            place_task.cancel()
            await self.stop_controller(base)
            return "nochoice"

        try:
            control = self.entries[self.emojis.index(str(react))]
        except IndexError:
            await self.stop_controller(base)
            if str(react) == "\U000021a9":
                return "undo"
            elif str(react) == "\U00002139":
                return "current"

        await self.stop_controller(base)
        if not self.return_index:
            return control
        else:
            return self.emojis.index(str(react))

    async def stop_controller(self, message):
        try:
            if self.delete:
                await message.delete()
            else:
                pass
        except discord.HTTPException:
            pass
