"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.

Almost everything here is copied from
https://github.com/EmoteCollector/bot/blob/master/emote_collector/utils/i18n.py
Thanks to lambda and Scragly for precious help!
"""
import ast
import builtins
import gettext
import inspect
import os.path
from glob import glob
from os import getcwd

import aiocontextvars

BASE_DIR = getcwd()
default_locale = "en_US"
locale_dir = "locales"

locales = frozenset(
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


def use_current_gettext(*args, **kwargs):
    if not gettext_translations:
        return gettext.gettext(*args, **kwargs)

    locale = current_locale.get()
    return gettext_translations.get(
        locale, gettext_translations[default_locale]
    ).gettext(*args, **kwargs)


def i18n_docstring(func):
    src = inspect.getsource(func)
    try:
        tree = ast.parse(src)
    except IndentationError:
        tree = ast.parse('class Foo:\n' + src)
        tree = tree.body[0].body[0]  # ClassDef -> FunctionDef
    else:
        tree = tree.body[0]  # FunctionDef

    if not isinstance(tree.body[0], ast.Expr):
        return func

    tree = tree.body[0].value
    if not isinstance(tree, ast.Call):
        return func

    if not isinstance(tree.func, ast.Name) or tree.func.id != '_':
        return func

    assert len(tree.args) == 1
    assert isinstance(tree.args[0], ast.Str)

    func.__doc__ = tree.args[0].s
    return func


current_locale = aiocontextvars.ContextVar("i18n")
builtins._ = use_current_gettext
builtins.locale_doc = i18n_docstring

current_locale.set(default_locale)

# only for <3.7
# setup = aiocontextvars.enable_inherit
