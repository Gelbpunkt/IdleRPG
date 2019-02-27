"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


from discord.ext import commands
from classes.context import Context


class BotBase(commands.AutoShardedBot):
    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)
