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
import re

from discord.utils import escape_markdown as discord_escape_markdown


def get_backticks(text):
    top = 0
    matches = re.finditer(r"(`)+", text, re.MULTILINE)
    for match in matches:
        if (g := len(match.group())) > top:
            top = g
    return top


def codeline(text: str, num: int = None):
    if not num:
        num = get_backticks(text) + 1
    return f"{num*'`'}{text}{num*'`'}"


def escape_markdown(text):
    text = discord_escape_markdown(text, as_needed=False).replace("\\", "\u200b")
    return codeline(text, 2)
