"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

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

from typing import TYPE_CHECKING

import discord
import pytz

from discord.ext import commands

from classes.context import Context
from classes.enums import DonatorRank
from utils import random

if TYPE_CHECKING:
    from discord.ext.commands.core import _CheckDecorator

    from classes.bot import Bot


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


class CityOwned(commands.CheckFailure):
    """Exception raised when an alliance controls a city."""

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

    def __init__(self, tier: DonatorRank) -> None:
        self.tier = tier


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


class NoOpenHelpRequest(commands.CheckFailure):
    """Exception raised when a user tries to edit/remove an open help request but none exists."""

    pass


def has_char() -> "_CheckDecorator":
    """Checks for a user to have a character."""

    async def predicate(ctx: Context) -> bool:
        ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if ctx.character_data:
            return True
        raise NoCharacter()

    return commands.check(predicate)


def has_no_char() -> "_CheckDecorator":
    """Checks for a user to have no character."""

    async def predicate(ctx: Context) -> bool:
        if await ctx.bot.cache.get_profile(ctx.author.id):
            raise NeedsNoCharacter()
        return True

    return commands.check(predicate)


def has_adventure() -> "_CheckDecorator":
    """Checks for a user to be on an adventure."""

    async def predicate(ctx: Context) -> bool:
        ctx.adventure_data = await ctx.bot.get_adventure(ctx.author)
        if ctx.adventure_data:
            return True
        raise NeedsAdventure()

    return commands.check(predicate)


def has_no_adventure() -> "_CheckDecorator":
    """Checks for a user to be on no adventure."""

    async def predicate(ctx: Context) -> bool:
        if not await ctx.bot.get_adventure(ctx.author):
            return True
        raise NeedsNoAdventure()

    return commands.check(predicate)


def has_no_guild() -> "_CheckDecorator":
    """Checks for a user to be in no guild."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if not ctx.character_data["guild"]:
            return True
        raise NeedsNoGuild()

    return commands.check(predicate)


def has_guild() -> "_CheckDecorator":
    """Checks for a user to be in a guild."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if ctx.character_data["guild"]:
            return True
        raise NoGuild()

    return commands.check(predicate)


def is_guild_officer() -> "_CheckDecorator":
    """Checks for a user to be guild officer or leader."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if (
            ctx.character_data["guildrank"] == "Leader"
            or ctx.character_data["guildrank"] == "Officer"
        ):
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_guild_leader() -> "_CheckDecorator":
    """Checks for a user to be guild leader."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if ctx.character_data["guildrank"] == "Leader":
            return True
        raise NoGuildPermissions()

    return commands.check(predicate)


def is_no_guild_leader() -> "_CheckDecorator":
    """Checks for a user not to be guild leader."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if ctx.character_data["guildrank"] != "Leader":
            return True
        raise NeedsNoGuildLeader()

    return commands.check(predicate)


def is_alliance_leader() -> "_CheckDecorator":
    """Checks for a user to be the leader of an alliance."""

    async def predicate(ctx: Context) -> bool:

        async with ctx.bot.pool.acquire() as conn:
            if not hasattr(ctx, "character_data"):
                ctx.character_data = await ctx.bot.cache.get_profile(
                    ctx.author.id, conn=conn
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


def owns_city() -> "_CheckDecorator":
    """"Checks whether an alliance owns a city."""

    async def predicate(ctx: Context) -> bool:
        async with ctx.bot.pool.acquire() as conn:
            if not hasattr(ctx, "character_data"):
                ctx.character_data = await ctx.bot.cache.get_profile(
                    ctx.author.id, conn=conn
                )
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


def owns_no_city() -> "_CheckDecorator":
    """"Checks whether an alliance owns no city."""

    async def predicate(ctx: Context) -> bool:
        async with ctx.bot.pool.acquire() as conn:
            if not hasattr(ctx, "character_data"):
                ctx.character_data = await ctx.bot.cache.get_profile(
                    ctx.author.id, conn=conn
                )
            alliance = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1', ctx.character_data["guild"]
            )
            owned_city = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1', alliance
            )
            if owned_city:
                raise CityOwned()
            return True

    return commands.check(predicate)


def is_class(class_: str) -> "_CheckDecorator":
    """Checks for a user to be in a class line."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if class_ == "Ranger" and (
            check := ctx.bot.in_class_line(ctx.character_data["class"], class_)
        ):
            ctx.pet_data = await ctx.bot.pool.fetchrow(
                'SELECT * FROM pets WHERE "user"=$1;', ctx.author.id
            )
        if not check:
            raise WrongClass(class_)
        return True

    return commands.check(predicate)


def is_nothing(ctx: Context) -> bool:
    """Checks for a user to be human and not taken cv yet."""
    if ctx.character_data["race"] == "Human" and ctx.character_data["cv"] == -1:
        return True
    return False


def has_god() -> "_CheckDecorator":
    """Checks for a user to have a god."""

    async def predicate(ctx: Context) -> bool:
        if not hasattr(ctx, "character_data"):
            ctx.character_data = await ctx.bot.cache.get_profile(ctx.author.id)
        if ctx.character_data["god"]:
            return True
        raise NeedsGod()

    return commands.check(predicate)


def has_no_god(ctx: Context) -> bool:
    """Checks for a user to have no god."""
    if not ctx.character_data["god"]:
        return True
    return False


def update_pet() -> "_CheckDecorator":
    async def predicate(ctx: Context) -> bool:
        if not ctx.pet_data:
            raise PetGone()
        diff = (
            (now := datetime.datetime.now(pytz.utc)) - ctx.pet_data["last_update"]
        ) // datetime.timedelta(hours=2)
        if diff >= 1:
            # Pets loose 2 food, 4 drinks, 1 joy and 1 love
            async with ctx.bot.pool.acquire() as conn:
                data = await conn.fetchrow(
                    'UPDATE pets SET "food"="food"-$1, "drink"="drink"-$2, "joy"=CASE'
                    ' WHEN "joy"-$3>=0 THEN "joy"-$3 ELSE 0 END, "love"=CASE WHEN'
                    ' "love"-$4>=0 THEN "love"-$4 ELSE 0 END, "last_update"=$5 WHERE'
                    ' "user"=$6 RETURNING *;',
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
                    await ctx.bot.cache.wipe_profile(ctx.author.id)
                    raise PetDied()
                elif data["love"] < 75 and random.randint(0, 99) > data["love"]:
                    classes[idx] = "No Class"
                    await conn.execute(
                        'DELETE FROM pets WHERE "user"=$1;', ctx.author.id
                    )
                    await conn.execute(
                        'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                        classes,
                        ctx.author.id,
                    )
                    await ctx.bot.cache.wipe_profile(ctx.author.id)
                    raise PetRanAway()
        return True

    return commands.check(predicate)


def is_god() -> "_CheckDecorator":
    """Checks for a user to be a god."""

    def predicate(ctx: Context) -> bool:
        return ctx.author.id in ctx.bot.gods

    return commands.check(predicate)


# TODO: Pass context here and assign there?


async def has_guild_(bot: "Bot", userid: int) -> bool:
    return bool(await bot.cache.get_profile_col(userid, "guild"))


async def is_member_of_author_guild(ctx: Context, userid: int) -> bool:
    user_1 = await ctx.bot.cache.get_profile_col(ctx.author.id, "guild")
    user_2 = await ctx.bot.cache.get_profile_col(userid, "guild")
    return user_1 == user_2


async def user_has_char(bot: "Bot", userid: int) -> bool:
    return bool(await bot.cache.get_profile(userid))


async def has_money(bot: "Bot", userid: int, money: int) -> bool:
    return await bot.cache.get_profile_col(userid, "money") >= money


async def guild_has_money(bot: "Bot", guildid: int, money: int) -> bool:
    res = await bot.pool.fetchval('SELECT money FROM guild WHERE "id"=$1;', guildid)
    return res >= money


def is_gm() -> "_CheckDecorator":
    async def predicate(ctx: Context) -> bool:
        return ctx.author.id in ctx.bot.config.game_masters

    return commands.check(predicate)


def is_patron(role: str = "basic") -> "_CheckDecorator":
    async def predicate(ctx: Context) -> bool:
        if await user_is_patron(ctx.bot, ctx.author, role):
            return True
        else:
            raise NoPatron(getattr(DonatorRank, role))

    return commands.check(predicate)


async def user_is_patron(bot: "Bot", user: discord.User, role: str = "basic") -> bool:
    actual_role = getattr(DonatorRank, role)
    rank = await bot.get_donator_rank(user.id)
    if rank and rank >= actual_role:
        return True
    return False


def is_supporter() -> "_CheckDecorator":
    async def predicate(ctx: Context) -> bool:
        try:
            member = await ctx.bot.http.get_member(
                ctx.bot.config.support_server_id, ctx.author.id
            )
        except discord.NotFound:
            return False
        member_roles = [int(i) for i in member.get("roles", [])]
        return ctx.bot.config.support_team_role in member_roles

    return commands.check(predicate)


def has_open_help_request() -> "_CheckDecorator":
    async def predicate(ctx: Context) -> bool:
        response = await ctx.bot.redis.execute("GET", f"helpme:{ctx.guild.id}")
        if not response:
            raise NoOpenHelpRequest()
        ctx.helpme = response.decode()
        return True

    return commands.check(predicate)
