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

Almost everything here is copied from
https://github.com/EmoteCollector/bot/blob/master/emote_collector/utils/i18n.py
Thanks to lambda and Scragly for precious help!
"""
import ast
import contextvars
import gettext
import inspect
import os.path

from glob import glob
from os import getcwd
from typing import Any, Callable

BASE_DIR = getcwd()
default_locale = "en_US"
locale_dir = "locales"

# https://github.com/python/mypy/issues/1317
locales: frozenset[str] = frozenset(
    map(
        os.path.basename,
        filter(os.path.isdir, glob(os.path.join(BASE_DIR, locale_dir, "*"))),
    )
)

gettext_translations = {
    locale: gettext.translation(
        "idlerpg", languages=(locale,), localedir=os.path.join(BASE_DIR, locale_dir)
    )
    for locale in locales
}

# source code is already in en_US.
# we don't use default_locale as the key here
# because the default locale for this installation may not be en_US
gettext_translations["en_US"] = gettext.NullTranslations()
locales = locales | {"en_US"}


def use_current_gettext(*args: Any, **kwargs: Any) -> str:
    if not gettext_translations:
        return gettext.gettext(*args, **kwargs)

    locale = current_locale.get()
    return gettext_translations.get(
        locale, gettext_translations[default_locale]
    ).gettext(*args, **kwargs)


def i18n_docstring(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    src = inspect.getsource(func)
    # We heavily rely on the content of the function to be correct
    try:
        parsed_tree = ast.parse(src)
    except IndentationError:
        parsed_tree = ast.parse("class Foo:\n" + src)
        assert isinstance(parsed_tree.body[0], ast.ClassDef)
        function_body: ast.ClassDef = parsed_tree.body[0]
        assert isinstance(function_body.body[0], ast.AsyncFunctionDef)
        tree: ast.AsyncFunctionDef = function_body.body[0]
    else:
        assert isinstance(parsed_tree.body[0], ast.AsyncFunctionDef)
        tree = parsed_tree.body[0]

    if not isinstance(tree.body[0], ast.Expr):
        return func

    gettext_call = tree.body[0].value
    if not isinstance(gettext_call, ast.Call):
        return func

    if not isinstance(gettext_call.func, ast.Name) or gettext_call.func.id != "_":
        return func

    assert len(gettext_call.args) == 1
    assert isinstance(gettext_call.args[0], ast.Str)

    func.__doc__ = gettext_call.args[0].s
    return func


current_locale: contextvars.ContextVar[str] = contextvars.ContextVar("i18n")
_ = use_current_gettext
locale_doc = i18n_docstring

current_locale.set(default_locale)
