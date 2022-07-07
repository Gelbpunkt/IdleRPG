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
from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from discord.ext import commands

from utils import i18n
from utils.i18n import _, locale_doc


class Locale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.locale_cache = {}

    async def set_locale(self, user, locale):
        """Sets the locale for a user."""
        async with self.bot.pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO user_settings ("user", "locale") VALUES ($1, $2);',
                    user.id,
                    locale,
                )
            except UniqueViolationError:
                await conn.execute(
                    'UPDATE user_settings SET "locale"=$1 WHERE "user"=$2;',
                    locale,
                    user.id,
                )
        self.bot.locale_cache[user.id] = locale

    async def get_locale(self, user):
        """Gets the locale for a user from DB."""
        return await self.bot.pool.fetchval(
            'SELECT "locale" FROM user_settings WHERE "user"=$1;', user
        )

    async def locale(self, user):
        lang = self.bot.locale_cache.get(user, None)
        if lang:
            return lang
        lang = await self.get_locale(user)
        self.bot.locale_cache[user] = lang
        return lang

    @commands.group(
        invoke_without_command=True,
        aliases=["locale", "lang"],
        brief=_("Check the available languages"),
    )
    @locale_doc
    async def language(self, ctx):
        _(
            """View all available languages' locale codes. You can check if your language is available by comparing against [this list](https://saimana.com/list-of-country-locale-code/)

            Some of these languages, like xtreme-owo or unplayable are no real languages but serve as a way to spice up the english text.
            If something is not yet translated, the english original text is used."""
        )
        all_locales = ", ".join(i18n.locales)
        current_locale = (
            self.bot.locale_cache.get(ctx.author.id, None) or i18n.default_locale
        )
        await ctx.send(
            _(
                "Your current language is **{current_locale}**. Available options:"
                " {all_locales}\n\nPlease use `{prefix}locale set language_code` to"
                " choose one."
            ).format(
                current_locale=current_locale,
                all_locales=all_locales,
                prefix=ctx.prefix,
            )
        )

    @language.command(name="set", brief=_("Set your language"))
    @locale_doc
    async def set_(self, ctx, *, locale: str):
        _(
            """`<locale>` - The locale code of the language you want to use; full list can be found in `{prefix}language`

            Changes the language the bot replies for you."""
        )
        if locale not in i18n.locales:
            return await ctx.send(_("Not a valid language."))
        try:
            await self.set_locale(ctx.author, locale)
        except ForeignKeyViolationError:
            i18n.current_locale.set(locale)
            self.bot.locale_cache[ctx.author.id] = locale
            await ctx.send(
                _(
                    "To permanently choose a language, please create a character and"
                    " enter this command again. I set it to {language} temporarily."
                ).format(language=locale)
            )
        await ctx.message.add_reaction("\U00002705")


async def setup(bot):
    await bot.add_cog(Locale(bot))
