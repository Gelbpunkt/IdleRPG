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
from utils.i18n import _


class Overflow(Exception):
    pass


class Reserved(Exception):
    pass


class ParsingError(Exception):
    def __init__(self, character):
        self.text = _("Illegal character '{character}'").format(character=character)


class BracketError(Exception):
    pass


class BracketError2(Exception):
    pass


class UndefinedVariable(Exception):
    def __init__(self, var):
        self.text = _("Variable {var} referenced before assignment.").format(var=var)
