"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
from discord.ext import commands

from utils import i18n


class Locale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.locale_cache = {}

    async def set_locale(self, user, locale):
        """Sets the locale for a user."""
        await self.bot.pool.execute('INSERT INTO user_settings ("user", "locale") VALUES ($1, $2) ON CONFLICT DO UPDATE SET "locale"=$2 WHERE "user"=$1;', user.id, locale)
        self.bot.locale_cache[user.id] = locale 

    async def get_locale(self, user):
        """Gets the locale for a user from DB."""
        return await self.bot.pool.fetchval('SELECT "locale" FROM user_settings WHERE "user"=$1;', user.id)

    async def locale(self, message):
        user = message.author
        lang = self.bot.locale_cache.get(user.id, None)
        if lang:
            return lang
        lang = await self.get_locale(user)
        self.bot.locale_cache[user.id] = lang
        return lang

    @commands.group(invoke_without_command=True, aliases=["locale", "lang"])
    async def language(self, ctx):
        _("""Change the bot language or view possible options.""")
        await ctx.send(", ".join(i18n.locales))

    @language.command(name="set")
    async def set_(self, ctx, *, locale: str):
        _("""Sets the language.""")
        if locale not in i18n.locales:
            return await ctx.send(_("Not a valid language."))
        await self.set_locale(ctx.author, locale)
        await ctx.message.add_reaction("\U00002705")

def setup(bot):
    bot.add_cog(Locale(bot))
