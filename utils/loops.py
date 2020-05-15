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
    """
    A clever scheduler for scheduling coroutine execution
    at a specific datetime within a single task
    """

    def __init__(self):
        # A list of all tasks, elements are (coro, datetime)
        self._tasks = []
        # The internal loop task
        self._task = None
        # The next task to run, (coro, datetime)
        self._next = None
        # Event fired when a initial task is added
        self._added = asyncio.Event()
        # Event fired when the loop needs to reset
        self._restart = asyncio.Event()

    def run(self):
        self._task = asyncio.create_task(self.loop())

    async def loop(self):
        while True:
            if self._next is None:
                # Wait for a task
                await self._added.wait()
            coro, time = self._next
            # Sleep until task will be executed
            done, pending = await asyncio.wait(
                [
                    asyncio.sleep((time - datetime.utcnow()).total_seconds()),
                    self._restart.wait(),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            fut = done.pop()
            if fut.result() is True:  # restart event
                continue
            # Run it
            asyncio.create_task(coro)
            # Get the next task sorted by time
            next_tasks = sorted(enumerate(self._tasks), key=lambda elem: elem[1][1])
            if next_tasks:
                idx, task = next_tasks[0]
                self._next = task
                del self._tasks[idx]
            else:
                self._next = None

    def schedule(self, coro, when):
        if when < datetime.utcnow():
            raise ValueError("May only be in the future.")
        if self._next:
            if when < self._next[1]:
                self._tasks.append(self._next)
                self._next = coro, when
                self._restart.set()
                self._restart.clear()
            else:
                self._tasks.append((coro, when))
        else:
            self._next = coro, when
            self._added.set()
            self._added.clear()


if __name__ == "__main__":

    async def demo():
        sched = Scheduler()
        sched.run()

        async def test(x):
            print(x)

        sched.schedule(test(1), datetime.utcnow() + timedelta(seconds=5))
        sched.schedule(test(2), datetime.utcnow() + timedelta(seconds=10))
        await asyncio.sleep(6)
        sched.schedule(test(3), datetime.utcnow() + timedelta(seconds=1))
        await asyncio.sleep(30)

    asyncio.run(demo())
