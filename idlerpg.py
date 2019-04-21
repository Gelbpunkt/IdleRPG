"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import sys
from json import loads

from classes.bot import Bot

if sys.platform == "linux" and sys.version_info >= (
    3,
    5,
):  # uvloop requires linux and min 3.5 Python
    # import uvloop
    # asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    pass

bot = Bot(
    case_insensitive=True,
    description="The one and only IdleRPG bot for discord",
    shard_ids=loads(sys.argv[1]),
    shard_count=int(sys.argv[2]),
)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.connect_all())
