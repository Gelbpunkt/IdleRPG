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
        self._task_count = 0
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
                self._task_count -= 1
            else:
                self._next = None
                self._task_count = 0

    def schedule(self, coro, when):
        if when < datetime.utcnow():
            raise ValueError("May only be in the future.")
        self._task_count += 1
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


class Manager:
    """
    A manager for multiple Schedulers
    to balance load.
    Can run up to ~20 schedulers
    and ~1-10 million jobs just fine,
    depending on the concurrent finishing
    jobs.
    """

    def __init__(self, tasks=1):
        self._schedulers = []
        for i in range(tasks):
            self._schedulers.append(Scheduler())

    def run(self):
        for sched in self._schedulers:
            sched.run()

    def schedule(self, *args, **kwargs):
        # Find the scheduler with less load
        sorted_by_load = sorted(self._schedulers, key=lambda x: x._task_count)
        sorted_by_load[0].schedule(*args, **kwargs)


if __name__ == "__main__":
    import random

    import uvloop

    uvloop.install()

    async def demo():
        sched = Manager(20)
        sched.run()

        async def test(x, t):
            print(f"Task #{x} finished with {t}")

        start = datetime.utcnow()

        for i in range(10000000):
            t = random.randint(120, 600000)
            sched.schedule(test(i, t), start + timedelta(seconds=t))
        print("done sched")
        await asyncio.sleep(600)

    asyncio.run(demo())
