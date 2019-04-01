"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
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
