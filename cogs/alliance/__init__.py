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
import asyncio

from typing import Union

import discord

from discord.ext import commands

from classes.converters import MemberWithCharacter
from cogs.shard_communication import alliance_on_cooldown as alliance_cooldown
from utils import misc as rpgtools
from utils.checks import (
    guild_has_money,
    has_char,
    has_guild,
    is_alliance_leader,
    is_guild_leader,
    owns_city,
    owns_no_city,
)


class Alliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @locale_doc
    async def cities(self, ctx):
        _("""Shows cities and owners.""")
        cities = await self.bot.pool.fetch(
            'SELECT c.*, g."name" AS "gname", COALESCE(SUM(d."defense"), 0) AS "defense" FROM city c JOIN guild g ON c."owner"=g."id" LEFT JOIN defenses d ON c."name"=d."city" GROUP BY c."owner", c."name", g."name";'
        )
        em = discord.Embed(title=_("Cities"), colour=self.bot.config.primary_colour)
        for city in sorted(
            cities, key=lambda x: -len(self.bot.config.cities[x["name"]])
        ):
            em.add_field(
                name=_("{name} (Tier {tier})").format(
                    name=city["name"], tier=len(self.bot.config.cities[city["name"]])
                ),
                value=_(
                    "Owned by {alliance}'s alliance\nBuildings: {buildings}\nTotal defense: {defense}"
                ).format(
                    alliance=city["gname"],
                    buildings=", ".join(self.bot.config.cities[city["name"]]),
                    defense=city["defense"],
                ),
            )
        await ctx.send(embed=em)

    @has_char()
    @has_guild()
    @commands.group(invoke_without_command=True)
    @locale_doc
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
            return await ctx.send(
                _(
                    "You are not in an alliance. You are alone and may still use all other alliance commands or invite a guild to create a bigger alliance."
                )
            )
        alliance_embed = discord.Embed(
            title=_("Your allied guilds"), color=self.bot.config.primary_colour
        )
        for guild in allied_guilds:
            alliance_embed.add_field(
                name=guild[1],
                value=_("Led by {leader}").format(
                    leader=await rpgtools.lookup(self.bot, guild["leader"])
                ),
                inline=False,
            )
        alliance_embed.set_footer(
            text=_(
                "{prefix}alliance buildings | {prefix}alliance defenses | {prefix}alliance attack | {prefix}alliance occupy"
            ).format(prefix=ctx.prefix)
        )

        await ctx.send(embed=alliance_embed)

    @alliance_cooldown(300)
    @is_alliance_leader()
    @has_char()
    @alliance.command()
    @locale_doc
    async def invite(self, ctx, newleader: MemberWithCharacter):
        _("""[Alliance Leader only] Invite a guild leader to the alliance.""")
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
            if (
                await conn.fetchval(
                    'SELECT COUNT(*) FROM guild WHERE "alliance"=$1;',
                    ctx.character_data["guild"],
                )
            ) == 3:
                return await ctx.send(_("Your alliance is full."))
            if await conn.fetchrow(
                'SELECT * FROM city WHERE "owner"=$1;', ctx.user_data["guild"]
            ):
                return await ctx.send(
                    _(
                        "**{user}'s guild is a single-guild alliance and owns a city."
                    ).format(user=newleader)
                )
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
    @locale_doc
    async def leave(self, ctx):
        _("""[Guild Leader only] Leave your alliance.""")
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
    @has_char()
    @alliance.command()
    @locale_doc
    async def kick(self, ctx, *, guild_to_kick: Union[int, str]):
        _(
            """[Alliance Leader only] Kick a guild from your alliance.\n Use either the guild name or ID for guild_to_kick."""
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
        return (current + 1) * 100000

    @alliance.group(invoke_without_command=True)
    @locale_doc
    async def build(self, ctx):
        _("""This command contains all alliance-building-related commands.""")
        subcommands = "```" + "\n".join(self.list_subcommands(ctx)) + "```"
        await ctx.send(_("Please use one of these subcommands:\n\n") + subcommands)

    @alliance_cooldown(300)
    @owns_city()
    @is_alliance_leader()
    @has_char()
    @build.command()
    @locale_doc
    async def building(self, ctx, name: str.lower):
        _("""[Alliance Leader only] Upgrade a city beneficial building.""")
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
                ).format(prefix=ctx.prefix, cmd=ctx.command.qualified_name)
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

    @alliance_cooldown(60)
    @owns_city()
    @is_alliance_leader()
    @has_char()
    @build.command()
    @locale_doc
    async def defense(self, ctx, *, name: str.lower):
        _(
            """[Alliance Leader only] Build a defensive building or buy troops for the city."""
        )
        building_list = {
            "cannons": {"hp": 50, "def": 50, "cost": 180000},
            "archers": {"hp": 150, "def": 40, "cost": 150000},
            "outer wall": {"hp": 1000, "def": 0, "cost": 180000},
            "inner wall": {"hp": 900, "def": 0, "cost": 150000},
            "moat": {"hp": 400, "def": 20, "cost": 150000},
            "tower": {"hp": 200, "def": 40, "cost": 180000},
        }
        if name not in building_list:
            return await ctx.send(
                _("Invalid defense. Please use `{prefix}{cmd} [{buildings}]`.").format(
                    prefix=ctx.prefix,
                    cmd=ctx.command.qualified_name,
                    buildings="/".join(building_list.keys()),
                )
            )
        building = building_list[name]
        async with self.bot.pool.acquire() as conn:
            city_name = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1;', ctx.character_data["guild"]
            )
            if (
                await self.bot.redis.execute("GET", f"city:{city_name}")
            ) == b"under attack":
                return await ctx.send(
                    _("Your city is under attack. Defenses cannot be built.")
                )
            cur_count = await conn.fetchval(
                'SELECT COUNT(*) FROM defenses WHERE "city"=$1;', city_name
            )
            if cur_count >= 10:
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
    @locale_doc
    async def buildings(self, ctx):
        _("""Lists buildings in your city.""")
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
                value=_("Level {level}").format(level=buildings[f"{i}_building"]),
                inline=True,
            )
        await ctx.send(embed=embed)

    @has_char()
    @alliance.command()
    @locale_doc
    async def defenses(self, ctx):
        _("""Lists defenses in your city.""")
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
        i = None
        for i in defenses:
            embed.add_field(
                name=i["name"].title(),
                value=_("HP: {hp}, Defense: {defense}").format(
                    hp=i["hp"], defense=i["defense"]
                ),
                inline=True,
            )
        if i is None:
            embed.add_field(
                name=_("None built"),
                value=_("Use {prefix}alliance build defense [name]").format(
                    prefix=ctx.prefix
                ),
            )
        await ctx.send(embed=embed)

    @owns_city()
    @is_alliance_leader()
    @has_char()
    @alliance.command()
    @locale_doc
    async def abandon(self, ctx):
        _("""[Alliance Leader only] Give up your city.""")
        if not await ctx.confirm(
            _("Are you sure you want to give up control of your city?")
        ):
            return
        name = await self.bot.pool.fetchval(
            'UPDATE city SET "owner"=1 WHERE "owner"=$1 RETURNING "name";',
            ctx.character_data["guild"],
        )
        await ctx.send(_("{city} was abandoned.").format(city=name))
        await self.bot.public_log(f"**{ctx.author}** abandoned **{name}**.")

    @owns_no_city()
    @is_alliance_leader()
    @has_char()
    @alliance.command()
    @locale_doc
    async def occupy(self, ctx, *, city: str.title):
        _("""[Alliance Leader only] Take control of an empty city.""")
        if city not in self.bot.config.cities:
            return await ctx.send(_("Invalid city name."))
        async with self.bot.pool.acquire() as conn:
            num_units = await conn.fetchval(
                'SELECT COUNT(*) FROM defenses WHERE "city"=$1;', city
            )
            if num_units != 0:
                return await ctx.send(
                    _(
                        "The city is occupied by **{amount}** defensive fortifications."
                    ).format(amount=num_units)
                )
            await conn.execute(
                'UPDATE city SET "owner"=$1, "raid_building"=0, "thief_building"=0, "trade_building"=0, "adventure_building"=0 WHERE "name"=$2;',
                ctx.character_data["guild"],
                city,
            )
        await ctx.send(
            _(
                "Your alliance now rules **{city}**. You should immediately buy defenses."
            ).format(city=city)
        )
        await self.bot.public_log(
            f"**{city}** was occupied by {ctx.author}'s alliance."
        )

    @alliance_cooldown(7200)
    @is_guild_leader()
    @alliance.command()
    @locale_doc
    async def attack(self, ctx, *, city: str.title):
        _("""[Guild Leader only] Attack a city.""")
        if city not in self.bot.config.cities:
            return await ctx.send(_("Invalid city."))

        if await self.bot.redis.execute("GET", f"city:{city}"):
            return await ctx.send(
                _("**{city}** is already under attack.").format(city=city)
            )

        async with self.bot.pool.acquire() as conn:
            alliance_id = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            alliance_name = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', alliance_id
            )

        # Gather the fighters
        attackers = []
        attacking_users = []
        msg = await ctx.send(
            _(
                "**{user}** wants to attack **{city}** with **{alliance_name}**'s alliance. React with ⚔ to join the attack!"
            ).format(user=ctx.author, city=city, alliance_name=alliance_name)
        )
        await msg.add_reaction("\U00002694")

        while True:  # we leave on timeout
            try:
                r, u = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: u not in attacking_users
                    and str(r.emoji) == "\U00002694"
                    and r.message.id == msg.id,
                    timeout=300,
                )
            except asyncio.TimeoutError:
                break  # no more joins
            async with self.bot.pool.acquire() as conn:
                profile = await conn.fetchrow(
                    'SELECT * FROM profile WHERE "user"=$1;', u.id
                )
                if not profile:
                    continue  # not a player
                user_alliance = await conn.fetchval(
                    'SELECT alliance FROM guild WHERE "id"=$1;', profile["guild"]
                )
                if user_alliance != alliance_id:
                    await ctx.send(
                        _(
                            "You are not a member of **{alliance_name}'s alliance**, {user}."
                        ).format(alliance_name=alliance_name, user=u)
                    )
                    continue
                damage, defense = await self.bot.get_raidstats(
                    u,
                    atkmultiply=profile["atkmultiply"],
                    defmultiply=profile["defmultiply"],
                    classes=profile["class"],
                    race=profile["race"],
                    guild=profile["guild"],
                    conn=conn,
                )
                if u not in attacking_users:
                    attacking_users.append(u)
                    attackers.append(
                        {"user": u, "damage": damage, "defense": defense, "hp": 250}
                    )
                    await ctx.send(_("{user} has joined the attack.").format(user=u))

        if not attackers:
            return await ctx.send(_("Noone joined."))

        if await self.bot.redis.execute("GET", f"city:{city}"):
            return await ctx.send(_("**{city}** is already under attack."))

        # Set city as under attack
        await self.bot.redis.execute("SET", f"city:{city}", "under attack", "EX", 7200)

        # Get all defenses
        defenses = [
            dict(i)
            for i in await self.bot.pool.fetch(
                'SELECT * FROM defenses WHERE "city"=$1;', city
            )
        ]

        if not defenses:
            return await ctx.send(_("The city is without defenses already."))

        await ctx.send(
            _("Attack on **{city}** starting with **{amount}** attackers!").format(
                city=city, amount=len(attacking_users)
            )
        )
        await self.bot.public_log(
            f"**{alliance_name}** is attacking **{city}** with {len(attackers)} attackers!"
        )

        while len(defenses) > 0 and len(attackers) > 0:
            # choose the lowest HP defense
            target = sorted(defenses, key=lambda x: x["hp"])[-1]
            damage = sum(i["damage"] for i in attackers)
            if target["hp"] - damage <= 0:
                defenses.remove(target)
                await self.bot.pool.execute(
                    'DELETE FROM defenses WHERE "id"=$1;', target["id"]
                )
                await ctx.send(
                    embed=discord.Embed(
                        title=_("Alliance Wars"),
                        description=_(
                            "**{alliance_name}** destroyed a {defense} in {city}!"
                        ).format(
                            alliance_name=alliance_name,
                            defense=target["name"],
                            city=city,
                        ),
                        colour=self.bot.config.primary_colour,
                    )
                )
            else:
                target["hp"] -= damage
                await self.bot.pool.execute(
                    'UPDATE defenses SET "hp"="hp"-$1 WHERE "id"=$2;',
                    damage,
                    target["id"],
                )
                await ctx.send(
                    embed=discord.Embed(
                        title=_("Alliance Wars"),
                        description=_(
                            "**{alliance_name}** hit a {defense} in {city} for {damage} damage! (Now {hp} HP)"
                        ).format(
                            alliance_name=alliance_name,
                            defense=target["name"],
                            city=city,
                            damage=damage,
                            hp=target["hp"],
                        ),
                        colour=self.bot.config.primary_colour,
                    )
                )
            if not defenses:  # gone
                break

            await asyncio.sleep(5)

            damage = sum(i["defense"] for i in defenses)
            # These are clever and attack low HP OR best damage
            if len({i["hp"] for i in attackers}) == 0:
                # all equal HP
                target = sorted(attackers, key=lambda x: x["damage"])[-1]
            else:
                # lowest HP
                target = sorted(attackers, key=lambda x: x["hp"])[0]

            damage -= target["defense"]
            damage = 0 if damage < 0 else damage

            if target["hp"] - damage <= 0:
                attackers.remove(target)
                await ctx.send(
                    embed=discord.Embed(
                        title=_("Alliance Wars"),
                        description=_("**{user}** got killed in {city}!").format(
                            user=target["user"], city=city
                        ),
                        colour=self.bot.config.primary_colour,
                    )
                )
            else:
                target["hp"] -= damage
                await ctx.send(
                    embed=discord.Embed(
                        title=_("Alliance Wars"),
                        description=_(
                            "**{user}** got hit in {city} for {damage} damage! (Now {hp} HP)"
                        ).format(
                            user=target["user"],
                            city=city,
                            damage=damage,
                            hp=target["hp"],
                        ),
                        colour=self.bot.config.primary_colour,
                    )
                )

            await asyncio.sleep(5)

        await self.bot.redis.execute(
            "SET", f"city:{city}", "cooldown", "EX", 600
        )  # 10min attack cooldown

        # it's over
        if not defenses:
            await ctx.send(
                _("**{alliance_name}** destroyed defenses in **{city}**!").format(
                    alliance_name=alliance_name, city=city
                )
            )
            await self.bot.public_log(
                f"**{alliance_name}** destroyed defenses in **{city}**!"
            )
        else:
            await ctx.send(
                _(
                    "**{alliance_name}** failed to destroy defenses in **{city}**!"
                ).format(alliance_name=alliance_name, city=city)
            )
            await self.bot.public_log(
                f"**{alliance_name}** failed to destroy defenses in **{city}**!"
            )


def setup(bot):
    bot.add_cog(Alliance(bot))
