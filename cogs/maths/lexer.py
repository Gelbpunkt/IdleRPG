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
import decimal

from sly import Lexer

from .exceptions import ParsingError


class CalcLexer(Lexer):
    tokens = (
        NUMBER,
        NAME,
        NEWLINE,
    )

    ignore = " \t"
    literals = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "!",
        "^",
        "=",
        "(",
        ")",
    }

    # Tokens
    NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"

    @_(r"(\d+(?:\.\d+)?)")
    def NUMBER(self, t):
        t.value = decimal.Decimal(t.value)
        return t

    @_(r"\n+|;+")
    def NEWLINE(self, t):
        self.lineno = t.value.count("\n") + t.value.count(";")
        return t

    def error(self, t):
        raise ParsingError(t.value[0])
