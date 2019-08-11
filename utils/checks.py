"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

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
import discord
from discord.ext import commands


class NoCharacter(commands.CheckFailure):
    """Exception raised when a user has no character."""

    pass


class NeedsNoCharacter(commands.CheckFailure):
    """Exception raised when a command requires you to have no character."""

    pass


class NoGuild(commands.CheckFailure):
    """Exception raised when a user has no guild."""

    pass


class NeedsNoGuild(commands.CheckFailure):
    """Exception raised when a user needs to be in no guild."""

    pass


class NoGuildPermissions(commands.CheckFailure):
    """Exception raised when a user does not have permissions because he is missing roles."""

    pass


class NeedsNoGuildLeader(commands.CheckFailure):
    """Exception raised when a user is guild leader and can't use the command therefore."""

    pass


class NeedsNoAdventure(commands.CheckFailure):
    """Exception raised when a user needs to be on no adventure."""

    pass


class NeedsAdventure(commands.CheckFailure):
    """Exception raised when a user needs to be on an adventure."""

    pass


class NoPatron(commands.CheckFailure):
    """Exception raised when you need to donate to use a command."""

    pass


class NeedsGod(commands.CheckFailure):
    """Exception raised when you need to have a god to use a command."""

    pass


class NeedsNoGod(commands.CheckFailure):
    """Exception raised when you need to have no god to use a command."""

    pass


def has_char():
    """Checks for a user to have a character."""

    async def predicate(ctx):
        ctx.character_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.character_data:
            return True
        raise NoCharacter()

    return commands.check(predicate)


def has_no_char():
    """Checks for a user to have no character."""

    async def predicate(ctx):
        if await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        ):
            raise NeedsNoCharacter()
        return True

    return commands.check(predicate)


def has_adventure():
    """Checks for a user to be on an adventure."""

    async def predicate(ctx):
        ctx.adventure_data = await ctx.bot.get_adventure(ctx.author)
        if ctx.adventure_data:
            return True
        raise NeedsAdventure()

    return commands.check(predicate)


def has_no_adventure():
    """Checks for a user to be on no adventure."""

    async def predicate(ctx):
        if not await ctx.bot.get_adventure(ctx.author):
            return True
        raise NeedsNoAdventure()

    return commands.check(predicate)


def has_no_guild():
    """Checks for a user to be in no guild."""

    async def predicate(ctx):
        if not await ctx.bot.pool.fetchval(
            'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
        ):
            return True
        raise NeedsNoGuild()

    return commands.check(predicate)


def has_guild():
    """Checks for a user to be in a guild."""

    async def predicate(ctx):
        ctx.character_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.character_data["guild"]:
            return True
        raise NoGuild()

    return commands.check(predicate)


def is_guild_officer():
    """Checks for a user to be guild officer or leader."""

    async def predicate(ctx):
        ctx.character_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if (
            ctx.character_data["guildrank"] == "Leader"
            or ctx.character_data["guildrank"] == "Officer"
        ):
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_guild_leader():
    """Checks for a user to be guild leader."""

    async def predicate(ctx):
        ctx.character_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.character_data["guildrank"] == "Leader":
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_no_guild_leader():
    """Checks for a user not to be guild leader."""

    async def predicate(ctx):
        ctx.character_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.character_data["guildrank"] != "Leader":
            return True
        raise NeedsNoGuildLeader()

    return commands.check(predicate)


def is_class(class_):
    """Checks for a user to be in a class line."""

    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            ret = await conn.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if (check := ctx.bot.in_class_line(ret, class_)) and class_ == "Ranger":
                ctx.pet_data = await conn.fetchrow(
                    'SELECT * FROM pets WHERE "user"=$1;', ctx.author.id
                )
        return check

    return commands.check(predicate)


def has_god():
    """Checks for a user to have a god."""

    async def predicate(ctx):
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.pool.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if ctx.character_data["god"]:
            return True
        raise NeedsGod()

    return commands.check(predicate)


def has_no_god():
    """Checks for a user to have no god."""

    async def predicate(ctx):
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.pool.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if not ctx.character_data["god"]:
            return True
        raise NeedsNoGod()

    return commands.check(predicate)


def is_god():
    """Checks for a user to be a god."""

    def predicate(ctx):
        return ctx.author.id in ctx.bot.gods

    return commands.check(predicate)


# TODO: Pass context here and assign there?


async def has_guild_(bot, userid):
    return await bot.pool.fetchval('SELECT guild FROM profile WHERE "user"=$1;', userid)


async def is_member_of_author_guild(ctx, userid):
    users = await ctx.bot.pool.fetch(
        'SELECT guild FROM profile WHERE "user"=$1 OR "user"=$2;', ctx.author.id, userid
    )
    if len(users) != 2:
        return False
    return users[0]["guild"] == users[1]["guild"]


async def user_has_char(bot, userid):
    async with bot.pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', userid)


async def has_money(bot, userid, money):
    async with bot.pool.acquire() as conn:
        return await conn.fetchval(
            'SELECT money FROM profile WHERE "user"=$1 AND "money">=$2;', userid, money
        )


def is_admin():
    async def predicate(ctx):
        return ctx.author.id in ctx.bot.config.admins

    return commands.check(predicate)


def is_patron():
    async def predicate(ctx):
        response = await ctx.bot.cogs["Sharding"].handler(
            "user_is_patreon", 1, args={"member_id": ctx.author.id}
        )
        if any(response):
            return True
        raise NoPatron()

    return commands.check(predicate)


async def user_is_patron(bot, user):
    response = await bot.cogs["Sharding"].handler(
        "user_is_patreon", 1, args={"member_id": user.id}
    )
    return any(response)


def is_supporter():
    async def predicate(ctx):
        response = await ctx.bot.cogs["Sharding"].handler(
            "user_is_helper", 1, args={"member_id": ctx.author.id}
        )
        return any(response)

    return commands.check(predicate)


def is_hypesquad(ctx):
    member = ctx.bot.get_guild(ctx.bot.config.support_server_id).get_member(
        ctx.author.id
    )  # cross server stuff
    if not member:
        return False
    return (
        discord.utils.get(member.roles, name="Hypesquad") is not None
        or discord.utils.get(member.roles, name="Administrators") is not None
    )
