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

from discord.ext import commands

from utils.i18n import _, locale_doc

from .exceptions import (
    BracketError,
    BracketError2,
    Overflow,
    ParsingError,
    Reserved,
    UndefinedVariable,
)
from .lexer import CalcLexer
from .parser import CalcParser


class Maths(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lexer = CalcLexer()

    @commands.command(aliases=["calculate", "math", "maths"], brief=_("Do some maths"))
    @locale_doc
    async def calc(self, ctx, *, expr: str):
        _(
            """`<expr>` - The mathematical expression to calculate

            Calculates something. pi is pi, tau is tau and e is math.e
            Supports round(), sin(), cos(), sqrt(), tan() and infinity (inf) and NaN (nan).
            Works with variable assignment and multiline-statements."""
        )
        parser = CalcParser()

        try:
            if not parser.is_matched("".join([c for c in expr if c in "()"])):
                raise BracketError()
            for i in range(len(expr) - 1):
                if expr[i] == "(" and expr[i + 1] == ")":
                    raise BracketError2()
            result = parser.parse(self.lexer.tokenize(expr))
        except Exception as e:
            if isinstance(e, Overflow):
                return await ctx.send(
                    _("Overflow! Try a smaller number for your power or factorial.")
                )
            if isinstance(e, ParsingError):
                return await ctx.send(e.text)
            if isinstance(e, UndefinedVariable):
                return await ctx.send(e.text)
            if isinstance(e, BracketError):
                return await ctx.send(_("Your expression contains left open brackets."))
            if isinstance(e, BracketError2):
                return await ctx.send(_("Your expression contains empty brackets."))
            if isinstance(e, decimal.InvalidOperation):
                return await ctx.send(_("Invalid operation on these numbers."))
            if isinstance(e, ZeroDivisionError):
                return await ctx.send(_("Can't divide by Zero."))
            if isinstance(e, Reserved):
                return await ctx.send(_("The variable name is a reserved keyword."))
            return await ctx.send(_("An unknown error occured."))
        ret = "\n".join([str(i) for i in result])
        await ctx.send(f"```\n{ret}\n```")


def setup(bot):
    bot.add_cog(Maths(bot))
