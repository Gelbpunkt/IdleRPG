"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
from asyncpg.exceptions import UniqueViolationError
from discord.ext import commands

from utils import i18n


class Locale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.locale_cache = {}

    async def set_locale(self, user, locale):
        """Sets the locale for a user."""
        if locale == i18n.default_locale:
            await self.bot.pool.execute(
                'DELETE FROM user_settings WHERE "user"=$1;', user.id
            )
            locale = None
        else:
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
            'SELECT "locale" FROM user_settings WHERE "user"=$1;', user.id
        )

    async def locale(self, message):
        user = message.author
        lang = self.bot.locale_cache.get(user.id, None)
        if lang:
            return lang
        lang = await self.get_locale(user)
        self.bot.locale_cache[user.id] = lang
        return lang

    @commands.group(invoke_without_command=True, aliases=["locale", "lang"])
    @locale_doc
    async def language(self, ctx):
        _("""Change the bot language or view possible options.""")
        all_locales = ", ".join(i18n.locales)
        current_locale = (
            self.bot.locale_cache.get(ctx.author.id, None) or i18n.default_locale
        )
        await ctx.send(
            _(
                "Your current language is **{current_locale}**. Available options: {all_locales}"
            ).format(current_locale=current_locale, all_locales=all_locales)
        )

    @language.command(name="set")
    @locale_doc
    async def set_(self, ctx, *, locale: str):
        _("""Sets the language.""")
        if locale not in i18n.locales:
            return await ctx.send(_("Not a valid language."))
        await self.set_locale(ctx.author, locale)
        await ctx.message.add_reaction("\U00002705")


def setup(bot):
    bot.add_cog(Locale(bot))
