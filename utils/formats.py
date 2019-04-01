"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import functools
import re

from more_itertools import one


def pluralize(**thing):
    name, value = one(thing.items())
    if name.endswith("y") and name[-2] not in "aeiou":
        name = f"{name[:-1]}ies" if value != 1 else name
        return f"{value} {name}"
    return f'{value} {name}{"s" * (value != 1)}'


def human_join(iterable, delim=", ", *, final="and"):
    """Joins an iterable in a human-readable way.

    The items are joined such that the last two items will be joined with a
    different delimiter than the rest.
    """
    seq = tuple(iterable)
    if not seq:
        return ""

    return f"{delim.join(seq[:-1])} {final} {seq[-1]}" if len(seq) != 1 else seq[0]


def multi_replace(string, replacements):
    substrs = sorted(replacements, key=len, reverse=True)
    pattern = re.compile("|".join(map(re.escape, substrs)))
    return pattern.sub(lambda m: replacements[m.group(0)], string)


_markdown_replacements = {c: f"\\{c}" for c in ("*", "`", "_", "~", "\\")}
escape_markdown = functools.partial(multi_replace, replacements=_markdown_replacements)
del _markdown_replacements


def truncate(s, length, placeholder):
    return (s[:length] + placeholder) if len(s) > length + len(placeholder) else s


def bold_name(thing, predicate):
    name = str(thing)
    return f"**{escape_markdown(name)}**" if predicate(thing) else name
