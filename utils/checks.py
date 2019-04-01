"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
from discord.ext import commands


class NoCharacter(commands.CheckFailure):
    pass


class NoGuild(commands.CheckFailure):
    pass


class Guild(commands.CheckFailure):
    pass


class NoRank(commands.CheckFailure):
    pass


class Leader(commands.CheckFailure):
    pass


def has_char():
    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            test = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if test:
            return True
        raise NoCharacter()

    return commands.check(predicate)


def has_adventure():
    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            return await conn.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
            )

    return commands.check(predicate)


def has_no_adventure():
    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            return not await conn.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', ctx.author.id
            )

    return commands.check(predicate)


def has_no_guild():
    async def predicate(ctx):
        if not await ctx.bot.pool.fetchval(
            'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
        ):
            return True
        raise Guild()

    return commands.check(predicate)


def has_guild():
    async def predicate(ctx):
        if await ctx.bot.pool.fetchval(
            'SELECT guild FROM profile WHERE "user"=$1;', ctx.author.id
        ):
            return True
        raise NoGuild()

    return commands.check(predicate)


def is_guild_officer():
    async def predicate(ctx):
        rank = await ctx.bot.pool.fetchval(
            'SELECT guildrank FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if rank == "Leader" or rank == "Officer":
            return True
        raise NoRank()

    return commands.check(predicate)


def is_guild_leader():
    async def predicate(ctx):
        rank = await ctx.bot.pool.fetchval(
            'SELECT guildrank FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if rank == "Leader":
            return True
        raise NoRank()

    return commands.check(predicate)


def is_no_guild_leader():
    async def predicate(ctx):
        rank = await ctx.bot.pool.fetchval(
            'SELECT guildrank FROM profile WHERE "user"=$1;', ctx.author.id
        )
        if rank != "Leader":
            return True
        raise Leader()

    return commands.check(predicate)


def is_support_server():
    async def predicate(ctx):
        if ctx.channel.id == ctx.bot.config.support_server_id:
            return True
        return False

    return commands.check(predicate)


async def has_guild_(bot, userid):
    return await bot.pool.fetchval('SELECT guild FROM profile WHERE "user"=$1;', userid)


async def is_member_of_author_guild(ctx, userid):
    usrs = await ctx.bot.pool.fetch(
        'SELECT guild FROM profile WHERE "user"=$1 OR "user"=$2;', ctx.author.id, userid
    )
    if len(usrs) != 2:
        return False
    return usrs[0]["guild"] == usrs[1]["guild"]


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
    def predicate(ctx):
        return any(await ctx.bot.cogs["Sharding"].handler("user_is_patreon", 1, args={"member_id": ctx.author.id}))

    return commands.check(predicate)


def user_is_patron(bot, user_id):
    return any(await bot.cogs["Sharding"].handler("user_is_patreon", 1, args={"member_id": user_id}))

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
