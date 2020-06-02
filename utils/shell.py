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

ARM_CPUS = {
    "0x810": "ARM810",
    "0x920": "ARM920",
    "0x922": "ARM922",
    "0x926": "ARM926",
    "0x940": "ARM940",
    "0x946": "ARM946",
    "0x966": "ARM966",
    "0xa20": "ARM1020",
    "0xa22": "ARM1022",
    "0xa26": "ARM1026",
    "0xb02": "ARM11 MPCore",
    "0xb36": "ARM1136",
    "0xb56": "ARM1156",
    "0xb76": "ARM1176",
    "0xc05": "Cortex-A5",
    "0xc07": "Cortex-A7",
    "0xc08": "Cortex-A8",
    "0xc09": "Cortex-A9",
    "0xc0d": "Cortex-A17",  # Originally A12
    "0xc0f": "Cortex-A15",
    "0xc0e": "Cortex-A17",
    "0xc14": "Cortex-R4",
    "0xc15": "Cortex-R5",
    "0xc17": "Cortex-R7",
    "0xc18": "Cortex-R8",
    "0xc20": "Cortex-M0",
    "0xc21": "Cortex-M1",
    "0xc23": "Cortex-M3",
    "0xc24": "Cortex-M4",
    "0xc27": "Cortex-M7",
    "0xc60": "Cortex-M0+",
    "0xd01": "Cortex-A32",
    "0xd03": "Cortex-A53",
    "0xd04": "Cortex-A35",
    "0xd05": "Cortex-A55",
    "0xd07": "Cortex-A57",
    "0xd08": "Cortex-A72",
    "0xd09": "Cortex-A73",
    "0xd0a": "Cortex-A75",
    "0xd0b": "Cortex-A76",
    "0xd0c": "Neoverse-N1",
    "0xd13": "Cortex-R52",
    "0xd20": "Cortex-M23",
    "0xd21": "Cortex-M33",
    "0xd4a": "Neoverse-E1",
}


async def get_out(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip()


async def get_cpu_name():
    stdout, stderr = await get_out("cat /proc/cpuinfo")
    lines = {
        (j := i.split(":"))[0].strip(): j[1].strip() for i in stdout.split("\n") if i
    }
    if (model_name := lines.get("model name", None)) :
        # any normal x86_64 CPU
        return model_name
    elif (cpu_part := lines.get("CPU part", None)) :
        # it's ARM
        # https://github.com/karelzak/util-linux/blob/master/sys-utils/lscpu-arm.c#L33
        return ARM_CPUS.get(cpu_part, "NaN")
    else:
        return "NaN"


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
