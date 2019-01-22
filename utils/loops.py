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
        except Exception as error:
            print_exc()
