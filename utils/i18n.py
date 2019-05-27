"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.

Almost everything here is copied from
https://github.com/EmoteCollector/bot/blob/master/emote_collector/utils/i18n.py
Thanks to lambda and Scragly for precious help!
"""
import builtins
import gettext
from glob import glob
from os import getcwd
import os.path

import aiocontextvars


BASE_DIR = getcwd()
default_locale = "en_US"
locale_dir = "locales"

locales = frozenset(
    map(
        os.path.basename,
        filter(
            os.path.isdir,
            glob(
                os.path.join(BASE_DIR, locale_dir, "*")
            )
        )
    )
)

translations = {
    locale: gettext.translation(
        "idlerpg",
        languages=(locale,),
        localedir=os.path.join(BASE_DIR, locale_dir)
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
    return (
        gettext_translations.get(
            locale,
            gettext_translations[default_locale]
        ).gettext(*args, **kwargs)
    )

current_locale = aiocontextvars.ContextVar("i18n")
builtins._ = use_current_gettext

current_locale.set(default_locale)

setup = aiocontextvars.enable_inherit
