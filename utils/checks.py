"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import discord
from discord.ext import commands


class NoCharacter(commands.CheckFailure):
    """Exception raised when a user has no character."""

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


def has_adventure():
    """Checks for a user to be on an adventure."""

    async def predicate(ctx):
        ctx.adventure_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
        )
        if ctx.adventure_data:
            return True
        raise NeedsAdventure()

    return commands.check(predicate)


def has_no_adventure():
    """Checks for a user to be on no adventure."""

    async def predicate(ctx):
        if not await ctx.bot.pool.fetchrow(
            'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
        ):
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
        ctx.guild_data = await ctx.bot.pool.fetchval(
            'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.guild_data:
            return True
        raise NoGuild()

    return commands.check(predicate)


def is_guild_officer():
    """Checks for a user to be guild officer or leader."""

    async def predicate(ctx):
        ctx.profile_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if (
            ctx.profile_data["guildrank"] == "Leader"
            or ctx.profile_data["guildrank"] == "Officer"
        ):
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_guild_leader():
    """Checks for a user to be guild leader."""

    async def predicate(ctx):
        ctx.profile_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.profile_data["guildrank"] == "Leader":
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_no_guild_leader():
    """Checks for a user not to be guild leader."""

    async def predicate(ctx):
        ctx.profile_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if ctx.profile_data["guildrank"] != "Leader":
            return True
        raise NeedsNoGuildLeader()

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
        return any(response)

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
