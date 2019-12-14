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
import datetime
import secrets

import discord
import pytz

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


class NoAlliancePermissions(commands.CheckFailure):
    """Exception raised when a user does not have permissions in the alliance to use a command."""

    pass


class NoCityOwned(commands.CheckFailure):
    """Exception raised when an alliance does not control a city."""

    pass


class WrongClass(commands.CheckFailure):
    """Exception raised when a user does not meet the class requirement."""

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


class PetGone(commands.CheckFailure):
    """Exception raised in case of the pet purgatory bug."""

    pass


class PetDied(commands.CheckFailure):
    """Exception raised when the pet died."""

    pass


class PetRanAway(commands.CheckFailure):
    """Exception raised when the pet ran away."""

    pass


class AlreadyRaiding(commands.CheckFailure):
    """Exception raised when a user tries starting a raid while another is ongoing."""

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


def is_alliance_leader():
    """Checks for a user to be the leader of an alliance."""

    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            ctx.character_data = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', ctx.author.id
            )
            leading_guild = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
        if (
            leading_guild == ctx.character_data["guild"]
            and ctx.character_data["guildrank"] == "Leader"
        ):
            return True
        raise NoAlliancePermissions()

    return commands.check(predicate)


def owns_city():
    """"Checks whether an alliance owns a city."""

    async def predicate(ctx):
        async with ctx.bot.pool.acquire() as conn:
            alliance = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1', ctx.character_data["guild"]
            )
            owned_city = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1', alliance
            )
            if not owned_city:
                raise NoCityOwned()
            ctx.city = owned_city
            return True

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
        if not check:
            raise WrongClass(class_)
        return True

    return commands.check(predicate)


def is_nothing(ctx):
    """Checks for a user to be human and not taken cv yet."""
    if ctx.character_data["race"] == "Human" and ctx.character_data["cv"] == -1:
        return True
    return False


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


def has_no_god(ctx):
    """Checks for a user to have no god."""
    if not ctx.character_data["god"]:
        return True
    return False


def update_pet():
    async def predicate(ctx):
        if not ctx.pet_data:
            raise PetGone()
        diff = (
            (now := datetime.datetime.now(pytz.utc)) - ctx.pet_data["last_update"]
        ) // datetime.timedelta(hours=2)
        if diff >= 1:
            # Pets loose 2 food, 4 drinks, 1 joy and 1 love
            async with ctx.bot.pool.acquire() as conn:
                data = await conn.fetchrow(
                    'UPDATE pets SET "food"="food"-$1, "drink"="drink"-$2, "joy"=CASE WHEN "joy"-$3>=0 THEN "joy"-$3 ELSE 0 END, "love"=CASE WHEN "love"-$4>=0 THEN "love"-$4 ELSE 0 END, "last_update"=$5 WHERE "user"=$6 RETURNING *;',
                    diff * 2,
                    diff * 4,
                    diff,
                    diff,
                    now,
                    ctx.author.id,
                )
                ctx.pet_data = data
                classes = ctx.character_data["class"]
                for evolve in ["Caretaker"] + ctx.bot.get_class_evolves()["Ranger"]:
                    if evolve in classes:
                        idx = classes.index(evolve)
                        break
                if data["food"] < 0 or data["drink"] < 0:
                    classes[idx] = "No Class"
                    await conn.execute(
                        'DELETE FROM pets WHERE "user"=$1;', ctx.author.id
                    )
                    await conn.execute(
                        'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                        classes,
                        ctx.author.id,
                    )
                    raise PetDied()
                elif data["love"] < 75 and secrets.randbelow(100) > data["love"]:
                    classes[idx] = "No Class"
                    await conn.execute(
                        'DELETE FROM pets WHERE "user"=$1;', ctx.author.id
                    )
                    await conn.execute(
                        'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                        classes,
                        ctx.author.id,
                    )
                    raise PetRanAway()
        return True

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
        res = await conn.fetchval(
            'SELECT money FROM profile WHERE "user"=$1 AND "money">=$2;', userid, money
        )
        return isinstance(res, int)


async def guild_has_money(bot, guildid, money):
    async with bot.pool.acquire() as conn:
        res = await conn.fetchval(
            'SELECT money FROM guild WHERE "id"=$1 and "money">=$2;', guildid, money
        )
        return isinstance(res, int)


def is_admin():
    async def predicate(ctx):
        return ctx.author.id in ctx.bot.config.admins

    return commands.check(predicate)


def is_patron(role="Donators"):
    async def predicate(ctx):
        response = await ctx.bot.cogs["Sharding"].handler(
            "user_is_patreon", 1, args={"member_id": ctx.author.id, "role": role}
        )
        if any(response):
            return True
        raise NoPatron()

    return commands.check(predicate)


async def user_is_patron(bot, user, role="Donators"):
    response = await bot.cogs["Sharding"].handler(
        "user_is_patreon", 1, args={"member_id": user.id, "role": role}
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
