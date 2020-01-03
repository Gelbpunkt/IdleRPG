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
import asyncio

from traceback import print_exc

from discord.ext import commands


async def queue_manager(bot: commands.Bot, queue: asyncio.Queue):
    """Basic loop to run things in order (async hack)"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        task = await queue.get()
        try:
            await task
        except Exception:
            print_exc()
