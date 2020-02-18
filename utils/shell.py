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
import re
import time

from asyncio.subprocess import DEVNULL, PIPE

from utils.paginator import TextPaginator


async def get_out(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip()


async def run(cmd, ctx):
    pager = TextPaginator(ctx, prefix="```sh\n", suffix="```")
    await pager.add_line(f"$ {cmd}\n")
    await pager.send()
    process = await asyncio.create_subprocess_shell(
        cmd, stdin=DEVNULL, stdout=PIPE, stderr=PIPE
    )
    tasks = {
        asyncio.Task(process.stdout.readline()): process.stdout,
        asyncio.Task(process.stderr.readline()): process.stderr,
    }
    buf = []
    time_since_last_update = time.perf_counter()
    written = False
    while (
        process.returncode is None
        or not process.stdout.at_eof()
        or not process.stderr.at_eof()
    ):
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        assert done
        for future in done:
            stream = tasks.pop(future)
            line = future.result().decode("utf-8")
            line = re.sub(r"\x1b[^m]*m", "", line).replace("``", "`\u200b`").strip("\n")
            if line:  # not EOF
                buf.append(line)
                right_now = time.perf_counter()
                if right_now > time_since_last_update + 0.5 or written is False:
                    await pager.add_line(buf)
                    time_since_last_update = time.perf_counter()
                    buf = []
                    written = True
            tasks[asyncio.Task(stream.readline())] = stream

    if buf:  # send buffer
        await pager.add_line(buf)
    await pager.add_line(f"\n[Exit code: {process.returncode}]")
