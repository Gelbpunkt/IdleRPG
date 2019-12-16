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
from typing import Union

import discord

from discord.ext import commands

from classes.converters import MemberWithCharacter
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import (
    guild_has_money,
    has_char,
    has_guild,
    is_alliance_leader,
    is_guild_leader,
    owns_city,
)


class Alliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def cities(self, ctx):
        _("""Shows cities and owners.""")
        cities = await self.bot.pool.fetch(
            'SELECT c.*, g."name" AS "gname" FROM city c JOIN guild g ON c."owner"=g."id";'
        )
        em = discord.Embed(title=_("Cities"), colour=self.bot.config.primary_colour)
        for city in cities:
            em.add_field(
                name=city["name"],
                value=_("Owned by {alliance}'s alliance").format(
                    alliance=city["gname"]
                ),
            )
        await ctx.send(embed=em)

    @has_char()
    @has_guild()
    @commands.group(invoke_without_command=True)
    async def alliance(self, ctx):
        _("""This command contains all alliance-related commands.""")
        async with self.bot.pool.acquire() as conn:
            alliance_id = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            allied_guilds = await conn.fetch(
                'SELECT * FROM guild WHERE "alliance"=$1;', alliance_id
            )
        if (
            len(allied_guilds) <= 1
        ):  # your guild is the only one OR error and query returns zero guilds
            return await ctx.send(_("You are not in an alliance."))
        alliance_embed = discord.Embed(
            title=_("Your allied guilds"), color=self.bot.config.primary_colour
        )
        for guild in allied_guilds:
            alliance_embed.add_field(
                name=guild[1],
                value=_("Lead by {leader}").format(
                    leader=await rpgtools.lookup(self.bot, guild["leader"])
                ),
                inline=False,
            )
        alliance_embed.set_footer(
            text=_(
                "{prefix}alliance buildings | {prefix}alliance defenses | {prefix}alliance attack"
            ).format(prefix=ctx.prefix)
        )

        await ctx.send(embed=alliance_embed)

    @is_alliance_leader()
    @alliance.command()
    async def invite(self, ctx, newleader: MemberWithCharacter):
        if not ctx.user_data["guild"]:
            return await ctx.send(_("That member is not in a guild."))
        newguild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1', ctx.user_data["guild"]
        )
        if newleader.id != newguild["leader"]:
            return await ctx.send(_("That member is not the leader of their guild."))
        elif (
            newguild["alliance"] == ctx.character_data["guild"]
        ):  # already part of your alliance
            return await ctx.send(
                _("This member's guild is already part of your alliance.")
            )

        if not await ctx.confirm(
            _(
                "{newleader}, {author} invites you to join their alliance. React to join now."
            ).format(newleader=newleader.mention, author=ctx.author.mention),
            user=newleader,
        ):
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE guild SET "alliance"=$1 WHERE "id"=$2;',
                ctx.character_data["guild"],
                ctx.user_data["guild"],
            )

        await ctx.send(
            _("**{newguild}** is now part of your alliance, {user}!").format(
                newguild=newguild["name"], user=ctx.author.mention
            )
        )

    @is_guild_leader()
    @alliance.command()
    async def leave(self, ctx):
        async with self.bot.pool.acquire() as conn:
            alliance = await conn.fetchval(
                'SELECT alliance from guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            if alliance == ctx.character_data["guild"]:
                return await ctx.send(
                    _("You are the alliance's leading guild and cannot leave it!")
                )
            await conn.execute(
                'UPDATE guild SET "alliance"="id" WHERE "id"=$1;',
                ctx.character_data["guild"],
            )
        await ctx.send(_("Your guild left the alliance."))

    @is_alliance_leader()
    @alliance.command()
    async def kick(self, ctx, *, guild_to_kick: Union[int, str]):
        _(
            """Kick a guild from your alliance.\n Use either the guild name or ID for guild_to_kick."""
        )
        if isinstance(guild_to_kick, str):
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "name"=$1;', guild_to_kick
            )
        else:
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', guild_to_kick
            )

        if not guild:
            return await ctx.send(
                _(
                    "Cannot find guild `{guild_to_kick}`. Are you sure that's the right name/ID?"
                ).format(guild_to_kick=guild_to_kick)
            )
        if guild["id"] == ctx.character_data["guild"]:
            return await ctx.send(_("That won't work."))

        if guild["alliance"] != ctx.character_data["guild"]:
            return await ctx.send(_("This guild is not in your alliance."))

        if not await ctx.confirm(
            _("Do you really want to kick **{guild}** from your alliance?").format(
                guild=guild["name"]
            )
        ):
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE guild SET "alliance"=$1 WHERE "id"=$1;', guild["id"]
            )

        await ctx.send(
            _("**{guild}** is no longer part of your alliance.").format(
                guild=guild["name"]
            )
        )

    def list_subcommands(self, ctx):
        if not ctx.command.commands:
            return "None"
        return [ctx.prefix + x.qualified_name for x in ctx.command.commands]

    def get_upgrade_price(self, current):
        # let's just make the price 1 until we have a sufficient formula
        return 1

    @alliance.group(invoke_without_command=True)
    async def build(self, ctx):
        _("""This command contains all alliance-building-related commands.""")
        subcommands = "```" + "\n".join(self.list_subcommands(ctx)) + "```"
        await ctx.send(_("Please use one of these subcommands:\n\n") + subcommands)

    @user_cooldown(300)
    @owns_city()
    @is_alliance_leader()
    @build.command()
    async def building(self, ctx, name: str.lower):
        city = await self.bot.pool.fetchrow(
            'SELECT * FROM city WHERE "owner"=$1;',
            ctx.character_data[
                "guild"
            ],  # can only be done by the leading g:uild so this works here
        )
        if name not in self.bot.config.cities[city["name"]]:
            return await ctx.send(
                _(
                    "Invalid building. Please use `{prefix}{cmd} [thief/raid/trade/adventure]` or check the possible buildings in your city."
                )
            )
        cur_level = city[f"{name}_building"]
        if cur_level == 10:
            return await ctx.send(_("This building is fully upgraded."))
        up_price = self.get_upgrade_price(cur_level)
        if not await ctx.confirm(
            _(
                "Are you sure you want to upgrade the **{name} building** to level {new_level}? This will cost $**{price}**."
            ).format(name=name, new_level=cur_level + 1, price=up_price)
        ):
            return
        if not await guild_has_money(self.bot, ctx.character_data["guild"], up_price):
            return await ctx.send(
                _(
                    "Your guild doesn't have enough money to upgrade the city's {name} building."
                ).format(name=name)
            )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                f'UPDATE city SET "{name}_building"="{name}_building"+1 WHERE "owner"=$1;',
                ctx.character_data["guild"],
            )
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                up_price,
                ctx.character_data["guild"],
            )

        await ctx.send(
            _(
                "Successfully upgraded the city's {name} building to level **{new_level}**"
            ).format(name=name, new_level=cur_level + 1)
        )

    @owns_city()
    @is_alliance_leader()
    @user_cooldown(60)
    @build.command()
    async def defense(self, ctx, *, name: str.lower):
        building_list = {
            "cannons": {"hp": 150, "def": 120, "cost": 50000},
            "archers": {"hp": 300, "def": 120, "cost": 75000},
            "outer wall": {"hp": 750, "def": 50, "cost": 125000},
            "inner wall": {"hp": 500, "def": 50, "cost": 80000},
            "moat": {"hp": 250, "def": 750, "cost": 200000},
            "tower": {"hp": 300, "def": 100, "cost": 50000},
        }
        if name not in building_list:
            return await ctx.send(
                _("Invalid defense. Please use `{prefix}{cmd} [{buildings}]`.").format(
                    prefix=ctx.prefix,
                    cmd=ctx.clean_command,
                    buildings="/".join(building_list.keys()),
                )
            )
        building = building_list[name]
        async with self.bot.pool.acquire() as conn:
            city_name = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1;', ctx.character_data["guild"]
            )
            cur_count = await conn.fetchval(
                'SELECT COUNT(*) FROM defenses WHERE "city"=$1;', city_name
            )
            if cur_count > 10:
                return await ctx.send(_("You may only build up to 10 defenses."))
            if not await ctx.confirm(
                _(
                    "Are you sure you want to build a **{defense}**? This will cost $**{price}**."
                ).format(defense=name, price=building["cost"])
            ):
                return
            if not await guild_has_money(
                self.bot, ctx.character_data["guild"], building["cost"]
            ):
                return await ctx.send(
                    _(
                        "Your guild doesn't have enough money to build a {defense}."
                    ).format(defense=name)
                )

            await conn.execute(
                'INSERT INTO defenses ("city", "name", "hp", "defense") VALUES ($1, $2, $3, $4);',
                city_name,
                name,
                building["hp"],
                building["def"],
            )
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                building["cost"],
                ctx.character_data["guild"],
            )

        await ctx.send(_("Successfully built a {defense}.").format(defense=name))

    @has_char()
    @alliance.command()
    async def buildings(self, ctx):
        async with self.bot.pool.acquire() as conn:
            alliance = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            buildings = await conn.fetchrow(
                'SELECT * FROM city WHERE "owner"=$1;', alliance
            )
        if not buildings:
            return await ctx.send(_("Your alliance does not own a city."))
        embed = discord.Embed(
            title=_("{city}'s buildings").format(city=buildings["name"]),
            colour=self.bot.config.primary_colour,
        )
        for i in self.bot.config.cities[buildings["name"]]:
            embed.add_field(
                name=f"{i.capitalize()} building",
                value="LVL " + str(buildings[f"{i}_building"]),
                inline=True,
            )
        await ctx.send(embed=embed)

    @has_char()
    @alliance.command()
    async def defenses(self, ctx):
        async with self.bot.pool.acquire() as conn:
            alliance = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            city_name = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1;', alliance
            )
            defenses = (
                await conn.fetch('SELECT * FROM defenses WHERE "city"=$1;', city_name)
            ) or []
        if not city_name:
            return await ctx.send(_("Your alliance does not own a city."))
        embed = discord.Embed(
            title=_("{city}'s defenses").format(city=city_name),
            colour=self.bot.config.primary_colour,
        )
        for i in defenses:
            embed.add_field(
                name=f"{i['name']}",
                value=_("HP: {hp}, Defense: {defense}").format(
                    hp=i["hp"], defense=i["defense"]
                ),
                inline=True,
            )
        else:
            embed.add_field(
                name=_("None built"),
                value=_("Use {prefix}alliance build defense [name]").format(
                    prefix=ctx.prefix
                ),
            )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Alliance(bot))
