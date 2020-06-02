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
import asyncio

from datetime import timedelta
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
from utils.i18n import _, locale_doc


class Alliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=_("Shows cities and owners."))
    @locale_doc
    async def cities(self, ctx):
        _(
            """Show all cities, their tiers, owners, available buildings and current defense."""
        )
        cities = await self.bot.pool.fetch(
            'SELECT c.*, g."name" AS "gname", COALESCE(SUM(d."defense"), 0) AS'
            ' "defense" FROM city c JOIN guild g ON c."owner"=g."id" LEFT JOIN defenses'
            ' d ON c."name"=d."city" GROUP BY c."owner", c."name", g."name";'
        )
        em = discord.Embed(
            title=_("Cities"), colour=self.bot.config.primary_colour
        ).set_image(url="https://idlerpg.xyz/city.png")
        for city in sorted(
            cities, key=lambda x: -len(self.bot.config.cities[x["name"]])
        ):
            em.add_field(
                name=_("{name} (Tier {tier})").format(
                    name=city["name"], tier=len(self.bot.config.cities[city["name"]])
                ),
                value=_(
                    "Owned by {alliance}'s alliance\nBuildings: {buildings}\nTotal"
                    " defense: {defense}"
                ).format(
                    alliance=city["gname"],
                    buildings=", ".join(self.bot.config.cities[city["name"]]),
                    defense=city["defense"],
                ),
            )
        await ctx.send(embed=em)

    @has_char()
    @has_guild()
    @commands.group(
        invoke_without_command=True, brief=_("Interact with your alliance.")
    )
    @locale_doc
    async def alliance(self, ctx):
        _(
            """Alliances are groups of guilds. Just like a guild requires at least one member, an alliance requires at least one guild and is considered a single-guild alliance.
            Alliances can occupy cities for passive bonuses given by the buildings.

            If this command is used without subcommand, it shows your allied guilds.
            See `{prefix}help alliance` for a list of commands to interact with your alliance!"""
        )
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
                    "You are not in an alliance. You are alone and may still use all"
                    " other alliance commands or invite a guild to create a bigger"
                    " alliance."
                )
            )
        alliance_embed = discord.Embed(
            title=_("Your allied guilds"), color=self.bot.config.primary_colour
        ).set_thumbnail(url="https://idlerpg.xyz/alliance_banner.png")
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
                "{prefix}alliance buildings | {prefix}alliance defenses |"
                " {prefix}alliance attack | {prefix}alliance occupy"
            ).format(prefix=ctx.prefix)
        )

        await ctx.send(embed=alliance_embed)

    @alliance_cooldown(300)
    @is_alliance_leader()
    @has_char()
    @alliance.command(brief=_("Invite a guild to your alliance."))
    @locale_doc
    async def invite(self, ctx, newleader: MemberWithCharacter):
        _(
            """`<newleader>` - A user with a character who leads a guild.

            Invite a guild to your alliance. All allied guilds will benefit from your city's buildings. Once you’re allied with another guild, it will be shown in {prefix}alliance.
            The other guild can't be allied with another alliance or own a city in order to be invited.

            Only the alliance leader can use this command.
            (This command has a cooldown of 5 minutes.)"""
        )
        if not ctx.user_data["guild"]:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("That member is not in a guild."))
        newguild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1', ctx.user_data["guild"]
        )
        if newleader.id != newguild["leader"]:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("That member is not the leader of their guild."))
        elif (
            newguild["alliance"] == ctx.character_data["guild"]
        ):  # already part of your alliance
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(
                _("This member's guild is already part of your alliance.")
            )

        async with self.bot.pool.acquire() as conn:
            if newguild["alliance"] != newguild["id"]:
                await self.bot.reset_alliance_cooldown(ctx)
                return await ctx.send(_("This guild is already in an alliance."))
            else:
                alliance_members = await conn.fetch(
                    'SELECT * FROM guild WHERE "alliance"=$1;', newguild["alliance"]
                )
                if len(alliance_members) > 1:
                    await self.bot.reset_alliance_cooldown(ctx)
                    return await ctx.send(
                        _("This guild is the leader of another alliance.")
                    )

            if not await ctx.confirm(
                _(
                    "{newleader}, {author} invites you to join their alliance. React to"
                    " join now."
                ).format(newleader=newleader.mention, author=ctx.author.mention),
                user=newleader,
            ):
                return

            if (
                await conn.fetchval(
                    'SELECT COUNT(*) FROM guild WHERE "alliance"=$1;',
                    ctx.character_data["guild"],
                )
            ) == 3:
                await self.bot.reset_alliance_cooldown(ctx)
                return await ctx.send(_("Your alliance is full."))
            if await conn.fetchrow(
                'SELECT * FROM city WHERE "owner"=$1;', ctx.user_data["guild"]
            ):
                await self.bot.reset_alliance_cooldown(ctx)
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
    @alliance.command(brief=_("Leave your alliance"))
    @locale_doc
    async def leave(self, ctx):
        _(
            """Leave your alliance. Once you left your alliance, you will no longer benefit from an owned city's buildings.

            If you lead an alliance, you cannot leave it (consider `{prefix}alliance kick`).
            Only guild leaders can use this command."""
        )
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
    @alliance.command(brief=_("Kick a guild from your alliance"))
    @locale_doc
    async def kick(self, ctx, *, guild_to_kick: Union[int, str]):
        _(
            """`<guild_to_kick>` -  A guild's name or ID

            Remove a guild from your alliance. Once the guild was kicked, it will no longer benefit from an owned city's buildings.

            Only the alliance leader can use this command."""
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
                    "Cannot find guild `{guild_to_kick}`. Are you sure that's the right"
                    " name/ID?"
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

    @alliance.group(invoke_without_command=True, brief=_("Build buildings or defenses"))
    @locale_doc
    async def build(self, ctx):
        _(
            """Build buildings `{prefix}alliance build building` or defenses `{prefix}alliance build defense`."""
        )
        subcommands = "```" + "\n".join(self.list_subcommands(ctx)) + "```"
        await ctx.send(_("Please use one of these subcommands:\n\n") + subcommands)

    @alliance_cooldown(300)
    @owns_city()
    @is_alliance_leader()
    @has_char()
    @build.command(brief=_("Upgrade a building in your city."))
    @locale_doc
    async def building(self, ctx, name: str.lower):
        _(
            """`<name>` - The name of the building to upgrade.

            Upgrade one of your city's buildings, granting better passive bonuses. The maximum level of any building is 10.
            Depending on the city's available buildings, `<name>` is either Thief, Raid, Trade, or Adventure. Use `{prefix}alliance buildings` to see which are available.

            The upgrade price depends on the building's next level and is calculated as next_level * $100,000.
            The upgrade price will be removed from the Alliance Leader's guild bank.

            This command requires your alliance to own a city.
            Only the alliance leader can use this command.
            (This command has a cooldown of 5 minutes)"""
        )
        city = await self.bot.pool.fetchrow(
            'SELECT * FROM city WHERE "owner"=$1;',
            ctx.character_data[
                "guild"
            ],  # can only be done by the leading g:uild so this works here
        )
        if name not in self.bot.config.cities[city["name"]]:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(
                _(
                    "Invalid building. Please use `{prefix}{cmd}"
                    " [thief/raid/trade/adventure]` or check the possible buildings in"
                    " your city."
                ).format(prefix=ctx.prefix, cmd=ctx.command.qualified_name)
            )
        cur_level = city[f"{name}_building"]
        if cur_level == 10:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("This building is fully upgraded."))
        up_price = self.get_upgrade_price(cur_level)
        if not await ctx.confirm(
            _(
                "Are you sure you want to upgrade the **{name} building** to level"
                " {new_level}? This will cost $**{price}**."
            ).format(name=name, new_level=cur_level + 1, price=up_price)
        ):
            return
        if not await guild_has_money(self.bot, ctx.character_data["guild"], up_price):
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(
                _(
                    "Your guild doesn't have enough money to upgrade the city's {name}"
                    " building."
                ).format(name=name)
            )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                f'UPDATE city SET "{name}_building"="{name}_building"+1 WHERE'
                ' "owner"=$1;',
                ctx.character_data["guild"],
            )
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                up_price,
                ctx.character_data["guild"],
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="alliance",
                data={"Amount": up_price, "Building": name},
            )

        await ctx.send(
            _(
                "Successfully upgraded the city's {name} building to level"
                " **{new_level}**"
            ).format(name=name, new_level=cur_level + 1)
        )

    @alliance_cooldown(60)
    @owns_city()
    @is_alliance_leader()
    @has_char()
    @build.command(brief=_("Build a defense in your city."))
    @locale_doc
    async def defense(self, ctx, *, name: str.lower):
        _(
            """Build some defensive buildings or place troops in your cities. The following are available:

            Cannons: 250HP, 60 defense for $200,000
            Archers: 500HP, 50 defemse for $100,000
            Outer Wall: 20,000HP, 0 defense for $500,000
            Inner Wall: 10,000HP, 0 defense for $200,000
            Moat: 5,000HP, 25 defense for $150,000
            Tower: 1,000HP, 50 defense for $200,000
            Ballista: 250HP, 30 defense for $100,000

            Any city can have a maximum of 10 defenses. When attacked, the buildings with the most HP are targeted first.
            You may not build defenses while your city is under attack. The price of the defense is removed from the leading guild's bank.

            This command requires your alliance to own a city.
            Only the alliance leader can use this command.
            (This command has a cooldown of 1 minutes)"""
        )
        building_list = {
            "cannons": {"hp": 250, "def": 60, "cost": 200000},
            "archers": {"hp": 500, "def": 50, "cost": 100000},
            "outer wall": {"hp": 20000, "def": 0, "cost": 500000},
            "inner wall": {"hp": 10000, "def": 0, "cost": 200000},
            "moat": {"hp": 5000, "def": 25, "cost": 150000},
            "tower": {"hp": 1000, "def": 50, "cost": 200000},
            "ballista": {"hp": 250, "def": 30, "cost": 100000},
        }
        if name not in building_list:
            await self.bot.reset_alliance_cooldown(ctx)
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
                await self.bot.reset_alliance_cooldown(ctx)
                return await ctx.send(
                    _("Your city is under attack. Defenses cannot be built.")
                )
            cur_count = await conn.fetchval(
                'SELECT COUNT(*) FROM defenses WHERE "city"=$1;', city_name
            )
            if cur_count >= 10:
                await self.bot.reset_alliance_cooldown(ctx)
                return await ctx.send(_("You may only build up to 10 defenses."))
            if not await ctx.confirm(
                _(
                    "Are you sure you want to build a **{defense}**? This will cost"
                    " $**{price}**."
                ).format(defense=name, price=building["cost"])
            ):
                return
            if not await guild_has_money(
                self.bot, ctx.character_data["guild"], building["cost"]
            ):
                await self.bot.reset_alliance_cooldown(ctx)
                return await ctx.send(
                    _(
                        "Your guild doesn't have enough money to build a {defense}."
                    ).format(defense=name)
                )

            await conn.execute(
                'INSERT INTO defenses ("city", "name", "hp", "defense") VALUES ($1, $2,'
                " $3, $4);",
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
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="alliance",
                data={"Amount": building["cost"], "Defense": name},
            )

        await ctx.send(_("Successfully built a {defense}.").format(defense=name))

    @has_char()
    @alliance.command(brief=_("Lists your city's buildings."))
    @locale_doc
    async def buildings(self, ctx):
        _(
            """Lists all buildings in your city, along with their level. These buildings give passive rewards to all alliance members:

            Thief buildings increase your chance to steal money as a thief, for every level, this increases your chance by 10%
            Raid buildings increase a user's raidstats by 0.1 per level
            Trade buildings remove the need to pay the 5% tax when selling or buying items when it reached at least Level 1. It also increases the amount of money you get from `{prefix}merch` and `{prefix}merchall` increasing the reward by 50% for each level
            Adventure buildings shorten the adventure time by 1% per level and increase your succes chances by 1% per level.

            Your alliance must own a city to use this command."""
        )
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
        ).set_image(url="https://idlerpg.xyz/market.png")
        for i in self.bot.config.cities[buildings["name"]]:
            embed.add_field(
                name=f"{i.capitalize()} building",
                value=_("Level {level}").format(level=buildings[f"{i}_building"]),
                inline=True,
            )
        await ctx.send(embed=embed)

    @has_char()
    @alliance.command(brief=_("Lists your city's defenses."))
    @locale_doc
    async def defenses(self, ctx):
        _(
            """Lists your city’s defenses and view the HP left for each.

            Your alliance must own a city to use this command."""
        )
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
        ).set_thumbnail(url="https://idlerpg.xyz/fortress.png")
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
    @alliance.command(brief=_("Abandon your city"))
    @locale_doc
    async def abandon(self, ctx):
        _(
            """Abandoning your city will immediately make all alliance members lose all passive bonuses offered by the city's buildings and the city ownership will be given back to the System Guild Alliance.

            Your alliance must own a city to use this command.
            Only the alliance leader can use this command."""
        )
        if not await ctx.confirm(
            _("Are you sure you want to give up control of your city?")
        ):
            return
        name = await self.bot.pool.fetchval(
            'UPDATE city SET "owner"=1 WHERE "owner"=$1 RETURNING "name";',
            ctx.character_data["guild"],
        )
        await self.bot.redis.execute("DEL", f"city:{name}:occ")
        await ctx.send(_("{city} was abandoned.").format(city=name))
        await self.bot.public_log(f"**{ctx.author}** abandoned **{name}**.")

    @owns_no_city()
    @is_alliance_leader()
    @has_char()
    @alliance.command(brief=_("Take over a city."))
    @locale_doc
    async def occupy(self, ctx, *, city: str.title):
        _(
            """`<city>` - The name of a city. You can check the city names with `{prefix}alliance cities`

            Occupy a city. Your alliance will then own that city and will be able to build defenses and level up buildings.
            You can only occupy a city of it has zero defenses left.

            Occupying a city sets it on a cooldown of 10 minutes, during which time it cannot be occupied by another alliance.
            Occupying a city also sets all of its buildings back to level 0.

            You cannot occupy a city if your alliance already owns one.
            Only the alliance leader can use this command."""
        )
        if city not in self.bot.config.cities:
            return await ctx.send(_("Invalid city name."))
        async with self.bot.pool.acquire() as conn:
            num_units = await conn.fetchval(
                'SELECT COUNT(*) FROM defenses WHERE "city"=$1;', city
            )
            occ_ttl = await self.bot.redis.execute("TTL", f"city:{city}:occ")
            if num_units != 0:
                return await ctx.send(
                    _(
                        "The city is occupied by **{amount}** defensive fortifications."
                    ).format(amount=num_units)
                )
            if occ_ttl != -2:
                return await ctx.send(
                    _("{city} was just occupied and stands under protection.").format(
                        city=city
                    )
                )
            await conn.execute(
                'UPDATE city SET "owner"=$1, "raid_building"=0, "thief_building"=0,'
                ' "trade_building"=0, "adventure_building"=0 WHERE "name"=$2;',
                ctx.character_data["guild"],
                city,
            )
        await ctx.send(
            _(
                "Your alliance now rules **{city}**. You should immediately buy"
                " defenses. You have **15 minutes** to build defenses before others can"
                " occupy the city!"
            ).format(city=city)
        )
        await self.bot.redis.execute(
            "SET", f"city:{city}:occ", ctx.character_data["guild"], "EX", 600
        )
        await self.bot.public_log(
            f"**{city}** was occupied by {ctx.author}'s alliance."
        )

    @alliance_cooldown(7200)
    @is_guild_leader()
    @alliance.command(brief=_("Attack a city"))
    @locale_doc
    async def attack(self, ctx, *, city: str.title):
        _(
            """`<city>` - The name of a city. You can check the city names with `{prefix}alliance cities`

            Attack a city, reducing its defenses to potentially take it over.
            Attacking a city will activate a grace period of 10 minutes, during which time it cannot be attacked again.

            When using this command, the bot will send a link used to join the attack. Each member of the alliance can join.
            Ten minutes after the link was sent, the users who joined will be gathered, their attack and defense depending on their equipped items, class and raid bonuses and their raidstats, and start the attack.

            During the attack, the highest HP defenses will be attacked first. All attackers' damage will be summed up.
            The defenses' damage sum up and damage either the attacker with the lowest HP or the attacker with the highest damage.

            If a defense reaches zero HP, it will be removed from the city, it will not regenerate HP after the attack is over.
            Attackers reaching zero HP will be removed from the attack as well.

            If a city's defenses were destroyed, your alliance can take occupy the city right away (`{prefix}alliance occupy`)

            Only the alliance leader can use this command.
            (This command has a cooldown of 2 hours.)"""
        )
        if city not in self.bot.config.cities:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("Invalid city."))

        if (y := await self.bot.redis.execute("GET", f"city:{city}")) :
            y = y.decode()
            if y == "cooldown":
                text = _("**{city}** has just been attacked. Have some mercy!").format(
                    city=city
                )
            elif y == "under attack":
                text = _("**{city}** is already under attack.").format(city=city)
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(text)

        async with self.bot.pool.acquire() as conn:
            alliance_id = await conn.fetchval(
                'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
            )
            alliance_name = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', alliance_id
            )

        # Get all defenses
        defenses = [
            dict(i)
            for i in await self.bot.pool.fetch(
                'SELECT * FROM defenses WHERE "city"=$1;', city
            )
        ]

        if not defenses:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("The city is without defenses already."))

        if (y := await self.bot.redis.execute("GET", f"city:{city}")) :
            y = y.decode()
            if y == "cooldown":
                text = _("**{city}** has just been attacked. Have some mercy!").format(
                    city=city
                )
            elif y == "under attack":
                text = _("**{city}** is already under attack.").format(city=city)
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(text)

        # Gather the fighters
        attackers = []
        attacking_users = []

        id_ = await self.bot.start_joins()

        await ctx.send(
            _(
                "**{user}** wants to attack **{city}** with **{alliance_name}**'s"
                " alliance. Head to https://join.idlerpg.xyz/{id_} to join the attack!"
            ).format(user=ctx.author, city=city, alliance_name=alliance_name, id_=id_)
        )

        await asyncio.sleep(60 * 10)

        a_users = await self.bot.get_joins(id_)

        async with self.bot.pool.acquire() as conn:
            for u in a_users:
                profile = await conn.fetchrow(
                    'SELECT * FROM profile WHERE "user"=$1;', u.id
                )
                if not profile:
                    continue  # not a player
                user_alliance = await conn.fetchval(
                    'SELECT alliance FROM guild WHERE "id"=$1;', profile["guild"]
                )
                if user_alliance != alliance_id:
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

        if not attackers:
            await self.bot.reset_alliance_cooldown(ctx)
            return await ctx.send(_("Noone joined."))

        # Set city as under attack
        await self.bot.redis.execute("SET", f"city:{city}", "under attack", "EX", 7200)

        await ctx.send(
            _("Attack on **{city}** starting with **{amount}** attackers!").format(
                city=city, amount=len(attacking_users)
            )
        )
        await self.bot.public_log(
            f"**{alliance_name}** is attacking **{city}** with {len(attackers)}"
            " attackers!"
        )

        while len(defenses) > 0 and len(attackers) > 0:
            # choose the highest HP defense
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
                            "**{alliance_name}** hit a {defense} in {city} for {damage}"
                            " damage! (Now {hp} HP)"
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
            if len({i["hp"] for i in attackers}) == 1:
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
                            "**{user}** got hit in {city} for {damage} damage! (Now"
                            " {hp} HP)"
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

    @has_char()
    @alliance.command(
        aliases=["cooldowns", "t", "cds"], brief=_("Lists alliance-specific cooldowns")
    )
    @locale_doc
    async def timers(self, ctx):
        _(
            """Lists alliance-specific cooldowns, meaning all alliance members have these cooldowns and cannot use the commands."""
        )
        alliance = await self.bot.pool.fetchval(
            'SELECT alliance FROM guild WHERE "id"=(SELECT guild FROM profile WHERE'
            ' "user"=$1);',
            ctx.author.id,
        )
        cooldowns = await self.bot.redis.execute("KEYS", f"alliancecd:{alliance}:*")
        if not cooldowns:
            return await ctx.send(
                _("Your alliance does not have any active cooldown at the moment.")
            )
        timers = _("Commands on cooldown:")
        for key in cooldowns:
            key = key.decode()
            cooldown = await self.bot.redis.execute("TTL", key)
            cmd = key.replace(f"alliancecd:{alliance}:", "")
            text = _("{cmd} is on cooldown and will be available after {time}").format(
                cmd=cmd, time=timedelta(seconds=int(cooldown))
            )
            timers = f"{timers}\n{text}"
        await ctx.send(f"```{timers}```")


def setup(bot):
    bot.add_cog(Alliance(bot))
