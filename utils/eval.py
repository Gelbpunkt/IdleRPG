"""
Original was written by Rapptz
Modified by the IdleRPG Project

The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.

The MIT License (MIT)
Copyright (c) 2015 Rapptz
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from io import StringIO
from contextlib import redirect_stdout
from traceback import format_exc
from textwrap import indent


async def evaluate(bot, body):
    env = {"bot": bot}
    env.update(globals())
    stdout = StringIO()
    to_compile = f'async def func():\n{indent(body, "  ")}'
    try:
        exec(to_compile, env)
    except Exception as e:
        return f"```py\n{e.__class__.__name__}: {e}\n```"

    func = env["func"]
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        return f"```py\n{value}{format_exc()}\n```"
    else:
        value = stdout.getvalue()
        try:
            await ctx.message.add_reaction("\u2705")
        except:
            pass

        if ret is None:
            if value:
                return f"```py\n{value}\n```"
        else:
            return f"```py\n{value}{ret}\n```"
