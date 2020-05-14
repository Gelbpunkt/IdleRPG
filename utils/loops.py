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

from datetime import datetime, timedelta
from traceback import print_exc

from classes.bot import Bot


async def queue_manager(bot: Bot, queue: asyncio.Queue[asyncio.Task]) -> None:
    """Basic loop to run things in order (async hack)"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        task = await queue.get()
        try:
            await task
        except Exception:
            print_exc()


class Scheduler:
    def __init__(self):
        self._tasks = []
        self._task = None
        self._next = None

    def run(self):
        self._task = asyncio.create_task(self.loop())

    async def loop(self):
        while True:
            if self._next is None:
                # Wait for a task
                while self._next is None:
                    await asyncio.sleep(0.1)
            # Sleep until task will be executed
            await asyncio.sleep((self._next[1] - datetime.now()).total_seconds())
            # Run it
            asyncio.create_task(self._next[0])
            # Get the next task
            next_tasks = sorted(list(enumerate(self._tasks)), key=lambda x: x[1][1])
            if next_tasks:
                self._next = next_tasks[0][1]
                del self._tasks[next_tasks[0][0]]
            else:
                self._next = None

    def schedule(self, coro, when):
        if when < datetime.now():
            raise ValueError("May only be in the future.")
        if self._next:
            if when < self._next[1]:
                self._tasks.append(self._next)
                self._next = coro, when
                self._task.cancel()
                self._task = asyncio.create_task(self.loop())
            else:
                self._tasks.append((coro, when))
        else:
            self._next = coro, when


if __name__ == "__main__":

    async def test():
        sched = Scheduler()
        sched.run()

        async def test(x):
            print(x)

        sched.schedule(test(1), datetime.now() + timedelta(seconds=5))
        sched.schedule(test(2), datetime.now() + timedelta(seconds=10))
        await asyncio.sleep(6)
        sched.schedule(test(3), datetime.now() + timedelta(seconds=1))
        await asyncio.sleep(30)

    asyncio.run(test())
