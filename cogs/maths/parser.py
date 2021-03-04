"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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
import math

from sly import Parser

from .exceptions import Overflow, ParsingError, Reserved, UndefinedVariable
from .lexer import CalcLexer


class CalcParser(Parser):
    tokens = CalcLexer.tokens

    precedence = (
        ("left", "+", "-"),
        ("left", "*", "/", "%"),
        ("left", "^"),
        ("left", "!"),
        ("right", UMINUS),
    )

    functions = {
        "round": round,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": lambda i: i.sqrt(),
        "abs": lambda i: i.copy_abs(),
    }

    constants = {
        "pi": decimal.Decimal(math.pi),
        "π": decimal.Decimal(math.pi),
        "e": decimal.Decimal(math.e),
        "tau": decimal.Decimal(math.tau),
        "τ": decimal.Decimal(math.tau),
        "inf": decimal.Decimal(math.inf),
        "∞": decimal.Decimal(math.inf),
        "NaN": decimal.Decimal(math.nan),
        "nan": decimal.Decimal(math.nan),
    }

    @_("statement")
    @_("statements NEWLINE statement")
    def statements(self, p):
        self.result.append(p.statement)

    @_('NAME "=" expression')
    def statement(self, p):
        if p.NAME in self.functions or p.NAME in self.constants:
            raise Reserved()
        self.variables[p.NAME] = p.expression
        return f"{p.NAME} = {p.expression}"

    @_("expression")
    def statement(self, p):
        return p.expression

    @_('expression "+" expression')
    def expression(self, p):
        return p.expression0 + p.expression1

    @_('expression "-" expression')
    def expression(self, p):
        return p.expression0 - p.expression1

    @_('expression "*" expression')
    def expression(self, p):
        return p.expression0 * p.expression1

    @_('expression "/" expression')
    def expression(self, p):
        return p.expression0 / p.expression1

    @_('expression "%" expression')
    def expression(self, p):
        return p.expression0 % p.expression1

    @_('expression "^" expression')
    def expression(self, p):
        if p.expression0 > 200 or p.expression1 > 200:
            raise Overflow()
        return p.expression0 ** p.expression1

    @_('expression "!"')
    def expression(self, p):
        if p.expression > 50:
            raise Overflow()
        return decimal.Decimal(math.gamma(p.expression + decimal.Decimal("1.0")))

    @_('"-" expression %prec UMINUS')
    def expression(self, p):
        return -p.expression

    @_('"(" expression ")"')
    def expression(self, p):
        return p.expression

    @_('NAME "(" expression ")"')
    def expression(self, p):
        try:
            return decimal.Decimal(self.functions[p.NAME](p.expression))
        except KeyError:
            raise UndefinedVariable(p.NAME)

    @_("NUMBER")
    def expression(self, p):
        return p.NUMBER

    @_("NAME")
    def expression(self, p):
        try:
            try:
                return self.constants[p.NAME]
            except KeyError:
                return self.variables[p.NAME]
        except KeyError:
            raise UndefinedVariable(p.NAME)

    def error(self, p):
        raise ParsingError(getattr(p, "value", "EOF"))

    def __init__(self):
        self.variables = {}
        self.result = []
        super().__init__()

    @staticmethod
    def is_matched(expression):
        """
        Finds out how balanced an expression is.
        With a string containing only brackets.
        >>> is_matched('[]()()(((([])))')
        False
        >>> is_matched('[](){{{[]}}}')
        True
        """
        opening = tuple("({[")
        closing = tuple(")}]")
        mapping = dict(zip(opening, closing))
        queue = []

        for letter in expression:
            if letter in opening:
                queue.append(mapping[letter])
            elif letter in closing:
                if not queue or letter != queue.pop():
                    return False
        return not queue

    def parse(self, expr):
        super().parse(expr)
        return self.result
