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
import math

from discord.ext import commands
from ply.lex import lex
from ply.yacc import yacc


class Overflow(Exception):
    pass


class Reserved(Exception):
    pass


class ParsingError(Exception):
    def __init__(self, text):
        self.text = text


class BracketError(Exception):
    pass


class BracketError2(Exception):
    pass


class UndefinedVariable(Exception):
    def __init__(self, var):
        self.text = _("Variable {var} referenced before assignment.").format(var=var)


class Maths(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_parser()

    def setup_parser(self):
        tokens = (
            "NUMBER",
            "NAME",
            "PLUS",
            "MINUS",
            "TIMES",
            "DIVIDE",
            "MODULO",
            "SQUARE",
            "FACTORIAL",
            "EQUALS",
            "ROUND",
            "SIN",
            "COS",
            "SQRT",
            "TAN",
            "ABS",
            "LPAREN",
            "RPAREN",
            "NEWLINE",
        )

        # Tokens

        t_PLUS = r"\+"
        t_MINUS = r"-"
        t_TIMES = r"\*"
        t_DIVIDE = r"/"
        t_MODULO = r"\%"
        t_FACTORIAL = r"\!"
        t_SQUARE = r"\^"
        t_EQUALS = r"="
        t_LPAREN = r"\("
        t_RPAREN = r"\)"
        t_NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"

        def t_NUMBER(t):
            r"(\d+(?:\.\d+)?)"
            t.value = decimal.Decimal(t.value)
            return t

        def t_NEWLINE(t):
            r"""\n+|;+"""
            t.lexer.lineno = t.value.count("\n") + t.value.count(";")
            return t

        # first functions parsed, then longest regex string, means name is always first :/

        def t_ROUND(t):
            r"round"
            return t

        def t_SIN(t):
            r"sin"
            return t

        def t_COS(t):
            r"cos"
            return t

        def t_SQRT(t):
            r"sqrt"
            return t

        def t_TAN(t):
            r"tan"
            return t

        def t_ABS(t):
            r"abs"
            return t

        # Ignored characters
        t_ignore = " \t"

        def t_error(t):
            raise ParsingError(
                _("Illegal character '{character}'").format(character=t.value[0])
            )

        self.lexer = lex()

        # Precedence rules for the arithmetic operators
        precedence = (
            ("left", "PLUS", "MINUS"),
            ("left", "TIMES", "DIVIDE", "MODULO"),
            ("left", "SQUARE"),
            ("left", "FACTORIAL"),
            ("right", "UMINUS"),
        )

        def p_statements(p):
            """statements : statement
            | statements NEWLINE statement"""
            if len(p) == 2:
                new_thing = p[1]
            else:
                new_thing = p[3]
            if new_thing is None:
                return
            p.parser.TEMP[p.parser.current]["result"].append(new_thing)

        def p_statement_assign(p):
            "statement : NAME EQUALS expression"
            if (
                p[1].startswith(("cos", "sin", "round", "sqrt", "tan"))
                or p[1] in p.parser.keywords
            ):
                raise Reserved()
            p.parser.TEMP[p.parser.current]["vars"][p[1]] = p[3]
            p.parser.TEMP[p.parser.current]["result"].append(
                _("{variable} set to {value}").format(variable=p[1], value=p[3])
            )

        def p_statement_expr(p):
            "statement : expression"
            p[0] = p[1]

        def p_expression_binop(p):
            """expression : expression PLUS expression
            | expression MINUS expression
            | expression TIMES expression
            | expression DIVIDE expression
            | expression MODULO expression
            | expression SQUARE expression
            | expression FACTORIAL"""
            if p[2] == "+":
                p[0] = p[1] + p[3]
            elif p[2] == "-":
                p[0] = p[1] - p[3]
            elif p[2] == "*":
                p[0] = p[1] * p[3]
            elif p[2] == "/":
                p[0] = p[1] / p[3]
            elif p[2] == "%":
                p[0] = p[1] % p[3]
            elif p[2] == "^":
                if p[1] > 200 or p[3] > 200:
                    raise Overflow()
                p[0] = p[1] ** p[3]
            elif p[2] == "!":
                if p[1] > 50:
                    raise Overflow()
                p[0] = decimal.Decimal(math.gamma(p[1] + decimal.Decimal("1.0")))

        def p_expression_uminus(p):
            "expression : MINUS expression %prec UMINUS"
            p[0] = -p[2]

        def p_expression_group(p):
            "expression : LPAREN expression RPAREN"
            p[0] = p[2]

        def p_expression_number(p):
            "expression : NUMBER"
            p[0] = p[1]

        def p_round(p):
            "expression : ROUND LPAREN expression RPAREN"
            p[0] = decimal.Decimal(round(p[3]))

        def p_sin(p):
            "expression : SIN LPAREN expression RPAREN"
            p[0] = decimal.Decimal(math.sin(p[3]))

        def p_cos(p):
            "expression : COS LPAREN expression RPAREN"
            p[0] = decimal.Decimal(math.cos(p[3]))

        def p_sqrt(p):
            "expression : SQRT LPAREN expression RPAREN"
            p[0] = p[3].sqrt()

        def p_tan(p):
            "expression : TAN LPAREN expression RPAREN"
            p[0] = decimal.Decimal(math.tan(p[3]))

        def p_abs(p):
            "expression : ABS LPAREN expression RPAREN"
            p[0] = p[3].copy_abs()

        def p_expression_name(p):
            "expression : NAME"
            try:
                p[0] = p.parser.TEMP[p.parser.current]["vars"][p[1]]
            except LookupError:
                raise UndefinedVariable(p[1])

        def p_error(p):
            raise ParsingError(
                _("Syntax error at '{character}'").format(character=p.value)
            )

        self.parser = yacc()
        self.parser.TEMP = {}

    def is_matched(self, expression):
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

    def parse(self, expr: str, id: int):
        if not self.is_matched("".join([c for c in expr if c in "()"])):
            raise BracketError
        for i in range(len(expr) - 1):
            if expr[i] == "(" and expr[i + 1] == ")":
                raise BracketError2
        vars = {
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
        self.parser.TEMP[id] = {"vars": vars, "result": []}
        self.parser.current = id
        self.parser.keywords = list(vars.keys())
        # return self.parser.parse(expr)
        self.parser.parse(expr)
        res = self.parser.TEMP[id]
        del self.parser.TEMP[id]
        return res

    @commands.command(aliases=["calculate", "math", "maths"])
    @locale_doc
    async def calc(self, ctx, *, expr: str):
        _(
            """Calculates something. pi is pi, tau is tau and e is math.e
        Supports round(), sin(), cos(), sqrt(), tan() and infinity (inf) and NaN (nan).
        Works with variable assignment and multiline-statements."""
        )
        try:
            ret = await self.bot.loop.run_in_executor(
                None, self.parse, expr, ctx.author.id
            )
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
                return await ctx.send(
                    _("The variable name starts with a reserved keyword.")
                )
            return await ctx.send(_("Unknown Error Occured"))
        vars = ret["vars"]
        ret = ret["result"]
        ret = "\n".join([str(i) for i in ret])
        await ctx.send(f"```\n{ret}\n```")


def setup(bot):
    bot.add_cog(Maths(bot))
