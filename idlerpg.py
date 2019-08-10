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
import asyncio
import sys
import tracemalloc
from json import loads

from classes.bot import Bot

tracemalloc.start()

if sys.platform == "linux":  # uvloop requires linux
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

bot = Bot(
    case_insensitive=True,
    description="The one and only IdleRPG bot for discord",
    shard_ids=loads(sys.argv[1]),
    shard_count=int(sys.argv[2]),
)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.connect_all())
