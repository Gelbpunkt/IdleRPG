"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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
import datetime
import logging
import os
import sys
import traceback

from decimal import Decimal

import aiohttp
import aioredis
import asyncpg
import discord
import fantasy_names as fn

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from classes.bucket_cooldown import Cooldown, CooldownMapping
from classes.classes import Mage, Paragon, Raider, Ranger, Ritualist, Thief, Warrior
from classes.classes import from_string as class_from_string
from classes.context import Context
from classes.enums import DonatorRank
from classes.exceptions import GlobalCooldown
from classes.http import ProxiedClientSession
from classes.items import ALL_ITEM_TYPES, Hand, ItemType
from utils import i18n, paginator, random
from utils.cache import cache
from utils.checks import user_is_patron
from utils.config import ConfigLoader
from utils.i18n import _


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        self.cluster_name = kwargs.pop("cluster_name")
        self.cluster_id = kwargs.pop("cluster_id")
        self.cluster_count = kwargs.pop("cluster_count")
        self.config = ConfigLoader("config.toml")
        mentions = AllowedMentions.none()
        mentions.users = True
        super().__init__(
            allowed_mentions=mentions,
            command_prefix=self.command_prefix,
            **kwargs,
        )  # we overwrite the prefix when it is connected

        # setup stuff
        self.version = self.config.bot.version
        self.paginator = paginator
        self.BASE_URL = self.config.external.base_url
        self.bans = set()
        self.support_server_id = self.config.game.support_server_id
        self.linecount = 0
        self.make_linecount()
        self.all_prefixes = {}
        self.activity = discord.Game(
            name=f"IdleRPG v{self.version}"
            if self.config.bot.is_beta
            else self.BASE_URL
        )
        self.logger = logging.getLogger()

        # global cooldown
        self.add_check(self.global_cooldown, call_once=True)

        # we assume the bot is created for use right now
        self.launch_time = datetime.datetime.now()
        self.eligible_for_cooldown_reduce = set()  # caching
        self.not_eligible_for_cooldown_reduce = set()  # caching

        self.normal_cooldown = CooldownMapping(
            Cooldown(3, 3, 1, 3, commands.BucketType.user)
        )
        self.donator_cooldown = CooldownMapping(
            Cooldown(3, 3, 1, 2, commands.BucketType.user)
        )

    def __repr__(self):
        return "<Bot>"

    async def global_cooldown(self, ctx: commands.Context):
        """
        A function that enables a global per-user cooldown
        and raises a special exception based on CommandOnCooldown
        """
        if ctx.author.id in self.not_eligible_for_cooldown_reduce:
            bucket = self.normal_cooldown.get_bucket(ctx.message)
        elif ctx.author.id in self.eligible_for_cooldown_reduce:
            bucket = self.donator_cooldown.get_bucket(ctx.message)
        else:
            if await user_is_patron(self, ctx.author, "bronze"):
                self.eligible_for_cooldown_reduce.add(ctx.author.id)
                bucket = self.donator_cooldown.get_bucket(ctx.message)
            else:
                self.not_eligible_for_cooldown_reduce.add(ctx.author.id)
                bucket = self.normal_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise GlobalCooldown(bucket, retry_after, BucketType.user)
        else:
            return True

    def make_linecount(self):
        """Generates a total linecount of all python files"""
        for root, _dirs, files in os.walk(os.getcwd()):
            root_parts = root.split(os.sep)
            if len(root_parts) > 2 and root_parts[2].startswith("."):
                continue
            for file_ in files:
                if file_.endswith(".py"):
                    with open(os.sep.join([root, file_]), encoding="utf-8") as f:
                        self.linecount += len(f.readlines())

    async def connect_all(self):
        """Connects all databases and initializes sessions"""
        proxy_auth = self.config.external.proxy_auth
        proxy_url = self.config.external.proxy_url
        if proxy_auth is None or proxy_url is None:
            self.session = aiohttp.ClientSession()
        else:
            self.session = ProxiedClientSession(
                authorization=proxy_auth, proxy_url=proxy_url
            )
        self.trusted_session = aiohttp.ClientSession()
        pool = aioredis.ConnectionPool.from_url(
            "redis://localhost",
            max_connections=20,
        )
        self.redis = aioredis.Redis(connection_pool=pool)
        database_creds = {
            "database": self.config.database.postgres_name,
            "user": self.config.database.postgres_user,
            "password": self.config.database.postgres_password,
            "host": self.config.database.postgres_host,
            "port": self.config.database.postgres_port,
        }
        self.pool = await asyncpg.create_pool(
            **database_creds, min_size=10, max_size=20, command_timeout=60.0
        )

        for extension in self.config.bot.initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()
        self.redis_version = await self.get_redis_version()
        await self.load_bans()
        await self.start(self.config.bot.token)

    async def get_redis_version(self):
        """Parses the Redis version out of the INFO command"""
        info = await self.redis.execute_command("INFO")
        return info["redis_version"]

    # https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/bot.py#L131
    def dispatch(self, event_name, *args, **kwargs):
        """Overriden version of Bot.dispatch to ignore reactions by banned users"""
        if (event_name == "raw_reaction_add" and args[0].user_id in self.bans) or (
            event_name == "message"
            and (args[0].author.id in self.bans or args[0].author.bot)
        ):  # args[1] is user
            return
        super().dispatch(event_name, *args, **kwargs)

    async def on_message_edit(self, before, after):
        """Handler for edited messages, re-executes commands"""
        if before.content != after.content and after.author.id not in self.bans:
            await self.on_message(after)

    async def invoke(self, ctx):
        """Handler for i18n, executes before any other commands or checks run"""
        locale = await self.get_cog("Locale").locale(ctx.message.author.id)
        i18n.current_locale.set(locale)
        await super().invoke(ctx)

    @property
    def uptime(self):
        """Returns the current uptime of the bot"""
        return datetime.datetime.now() - self.launch_time

    async def get_ranks_for(self, thing, conn=None):
        """Returns the rank in money and xp for a user"""
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False

        xp = await conn.fetchval(
            'SELECT COUNT(*) FROM profile WHERE "xp">=(SELECT "xp" FROM profile WHERE "user"=$1);',
            v,
        )
        money = await conn.fetchval(
            'SELECT COUNT(*) FROM profile WHERE "money">=(SELECT "money" FROM profile WHERE "user"=$1);',
            v,
        )
        if local:
            await self.pool.release(conn)
        return money, xp

    async def get_raidstats(
        self,
        thing,
        atkmultiply=None,
        defmultiply=None,
        classes=None,
        race=None,
        guild=None,
        god=None,
        conn=None,
    ):
        """Generates the raidstats for a user"""
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        if (
            atkmultiply is None
            or defmultiply is None
            or classes is None
            or guild is None
        ):
            row = await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', v)
            atkmultiply, defmultiply, classes, race, guild, user_god = (
                row["atkmultiply"],
                row["defmultiply"],
                row["class"],
                row["race"],
                row["guild"],
                row["god"],
            )
            if god is not None and god != user_god:
                raise ValueError()
        damage, armor = await self.get_damage_armor_for(
            v, classes=classes, race=race, conn=conn
        )
        if buildings := await self.get_city_buildings(guild, conn=conn):
            atkmultiply += buildings["raid_building"] * Decimal("0.1")
            defmultiply += buildings["raid_building"] * Decimal("0.1")
        classes = [class_from_string(c) for c in classes]
        for c in classes:
            if c and c.in_class_line(Raider):
                grade = c.class_grade()
                atkmultiply = atkmultiply + Decimal("0.1") * grade
                defmultiply = defmultiply + Decimal("0.1") * grade
        dmg = damage * atkmultiply
        deff = armor * defmultiply
        if local:
            await self.pool.release(conn)
        return dmg, deff

    async def get_equipped_items_for(self, thing, conn=None):
        """Fetches a list of equipped items of a user from the database"""
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        items = await conn.fetch(
            "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN"
            " inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1;",
            v,
        )
        if local:
            await self.pool.release(conn)
        return items

    async def get_context(self, message, *, cls=None):
        """Overrides the default Context with a custom Context"""
        return await super().get_context(message, cls=Context)

    async def command_prefix(self, bot, message):
        """
        Returns the prefix for a message
        Will be the global_prefix in DMs,
        in guilds it will use a custom set one
        or the global_prefix
        """
        if not message.guild or self.config.bot.is_beta:
            return commands.when_mentioned_or(self.config.bot.global_prefix)(
                self, message
            )  # Use global prefix in DMs
        pref = self.all_prefixes.get(message.guild.id)
        if pref is None:
            pref = (
                await self.pool.fetchval(
                    'SELECT "prefix" FROM server WHERE "id"=$1;', message.guild.id
                )
                or self.config.bot.global_prefix
            )
            self.all_prefixes[message.guild.id] = pref
        return commands.when_mentioned_or(pref)(self, message)

    async def wait_for_dms(self, check, timeout=30):
        """
        Cross-process DM event handling, check is a dictionary
        """
        try:
            data = (
                await self.cogs["Sharding"].handler(
                    action="wait_for_dms",
                    args={"check": check, "timeout": timeout},
                    expected_count=1,
                    _timeout=timeout,
                )
            )[0]
        except IndexError:
            raise asyncio.TimeoutError()
        channel_id = int(data["channel_id"])
        return discord.Message(
            state=self._connection, channel=discord.Object(channel_id), data=data
        )

    @cache(maxsize=8096)
    async def get_user_global(self, user_id: int):
        """Fetches Discord user data across multiple processes"""
        if user := self.get_user(user_id):
            return user

        try:
            return await self.fetch_user(user_id)
        except discord.NotFound:
            return None

    async def reset_cooldown(self, ctx):
        """Resets someone's cooldown for a Context"""
        await self.redis.execute_command(
            "DEL", f"cd:{ctx.author.id}:{ctx.command.qualified_name}"
        )

    async def reset_guild_cooldown(self, ctx):
        """Resets a guild's cooldown for a Context"""
        await self.redis.execute_command(
            "DEL", f"guildcd:{ctx.character_data['guild']}:{ctx.command.qualified_name}"
        )

    async def reset_alliance_cooldown(self, ctx):
        """Resets an alliance cooldown for a Context"""
        alliance = await self.pool.fetchval(
            'SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"]
        )
        await self.redis.execute_command(
            "DEL", f"alliancecd:{alliance}:{ctx.command.qualified_name}"
        )

    async def set_cooldown(
        self, ctx_or_user_id: Context | int, cooldown: int, identifier: str = None
    ):
        """Sets someone's cooldown or overwrite it if the cd already exists"""
        if identifier is None:
            cmd_id = ctx_or_user_id.command.qualified_name
        else:
            cmd_id = identifier
        if isinstance(ctx_or_user_id, Context):
            user_id = ctx_or_user_id.author.id
        else:
            user_id = ctx_or_user_id

        await self.redis.execute_command(
            "SET",
            f"cd:{user_id}:{cmd_id}",
            cmd_id,
            "EX",
            cooldown,
        )

    async def activate_booster(self, user, type_):
        """Activates a boost of type_ for a user"""
        if type_ not in ["time", "luck", "money"]:
            raise ValueError("Not a valid booster type.")
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute_command(
            "SET", f"booster:{user}:{type_}", 1, "EX", 86400
        )

    async def get_booster(self, user, type_):
        """Returns how longer a user has a booster running"""
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        val = await self.redis.execute_command("TTL", f"booster:{user}:{type_}")
        return datetime.timedelta(seconds=val) if val != -2 else None

    async def start_adventure(self, user, number, time):
        """Sends a user on an adventure"""
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute_command(
            "SET", f"adv:{user}", number, "EX", int(time.total_seconds()) + 259_200
        )  # +3 days

    async def get_adventure(self, user):
        """Returns a user's adventure"""
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        ttl = await self.redis.execute_command("TTL", f"adv:{user}")
        if ttl == -2:
            return
        num = await self.redis.execute_command("GET", f"adv:{user}")
        ttl = ttl - 259_200
        done = ttl <= 0
        time = datetime.timedelta(seconds=ttl)
        return int(num.decode("ascii")), time, done

    async def delete_adventure(self, user):
        """Deletes a user's adventure"""
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute_command("DEL", f"adv:{user}")

    async def has_money(self, user, money, conn=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        val = (
            await conn.fetchval('SELECT money FROM profile WHERE "user"=$1;', user)
            >= money
        )
        if local:
            await self.pool.release(conn)
        return val

    async def has_crates(self, user, crates, rarity, conn=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        cur_crates = await conn.fetchval(
            f'SELECT crates_{rarity} FROM profile WHERE "user"=$1;', user
        )
        if local:
            await self.pool.release(conn)
        return cur_crates is not None and cur_crates >= crates

    async def has_item(self, user, item, conn=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn:
            return await conn.fetchrow(
                'SELECT * FROM allitems WHERE "owner"=$1 AND "id"=$2;', user, item
            )
        else:
            return await self.pool.fetchrow(
                'SELECT * FROM allitems WHERE "owner"=$1 AND "id"=$2;', user, item
            )

    async def start_guild_adventure(self, guild, difficulty, time):
        await self.redis.execute_command(
            "SET",
            f"guildadv:{guild}",
            difficulty,
            "EX",
            int(time.total_seconds()) + 259_200,
        )  # +3 days

    async def get_guild_adventure(self, guild):
        ttl = await self.redis.execute_command("TTL", f"guildadv:{guild}")
        if ttl == -2:
            return
        num = await self.redis.execute_command("GET", f"guildadv:{guild}")
        ttl = ttl - 259_200
        done = ttl <= 0
        time = datetime.timedelta(seconds=ttl)
        return int(num.decode("ascii")), time, done

    async def delete_guild_adventure(self, guild):
        await self.redis.execute_command("DEL", f"guildadv:{guild}")

    async def create_item(
        self, name, value, type_, damage, armor, owner, hand, equipped=False, conn=None
    ):
        owner = owner.id if isinstance(owner, (discord.User, discord.Member)) else owner
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        item = await conn.fetchrow(
            'INSERT INTO allitems ("owner", "name", "value", "type", "damage",'
            ' "armor", "hand") VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *;',
            owner,
            name,
            value,
            type_,
            damage,
            armor,
            hand,
        )
        await conn.execute(
            'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
            item["id"],
            equipped,
        )
        if local:
            await self.pool.release(conn)
        return item

    async def create_random_item(
        self, minstat, maxstat, minvalue, maxvalue, owner, insert=True, conn=None
    ):
        owner = owner.id if isinstance(owner, (discord.User, discord.Member)) else owner
        item = {}
        item["owner"] = owner
        type_ = random.choice(ALL_ITEM_TYPES)
        hand = type_.get_hand()
        item["hand"] = hand.value
        item["type_"] = type_.value
        item["damage"] = (
            random.randint(minstat, maxstat) if type_ != ItemType.Shield else 0
        )
        item["armor"] = (
            random.randint(minstat, maxstat) if type_ == ItemType.Shield else 0
        )
        item["value"] = random.randint(minvalue, maxvalue)
        item["name"] = fn.weapon_name(type_.value)
        if hand == Hand.Both:
            item["damage"] = round(
                item["damage"] * 2
            )  # both hands = higher damage, else they would be worse
            # The issue with multiplying by 2
            # is that everything will be even
            # so we have to force uneven ones
            if random.randint(1, 2) == 1:
                item["damage"] -= 1
        if insert:
            return await self.create_item(**item, conn=conn)
        return item

    async def process_levelup(self, ctx, new_level, old_level, conn=None):
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        if (reward := random.choice(["crates", "money", "item"])) == "crates":
            if new_level < 6:
                column = "crates_common"
                amount = new_level
                reward_text = f"**{amount}** {self.cogs['Crates'].emotes.common}"
            elif new_level < 10:
                column = "crates_uncommon"
                amount = round(new_level / 2)
                reward_text = f"**{amount}** {self.cogs['Crates'].emotes.uncommon}"
            elif new_level < 18:
                column = "crates_rare"
                amount = 2
                reward_text = f"**2** {self.cogs['Crates'].emotes.rare}"
            elif new_level < 27:
                column = "crates_rare"
                amount = 3
                reward_text = f"**3** {self.cogs['Crates'].emotes.rare}"
            else:
                column = "crates_magic"
                amount = 1
                reward_text = f"**1** {self.cogs['Crates'].emotes.magic}"
            await self.log_transaction(
                ctx,
                from_=0,
                to=ctx.author.id,
                subject="crates",
                data={"Rarity": column.split("_")[1], "Amount": amount},
            )
            await self.pool.execute(
                f'UPDATE profile SET {column}={column}+$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
        elif reward == "item":
            stat = round(new_level * 1.5)
            item = await self.create_random_item(
                minstat=stat,
                maxstat=stat,
                minvalue=1000,
                maxvalue=1000,
                owner=ctx.author,
                insert=False,
                conn=conn,
            )
            item["name"] = _("Level {new_level} Memorial").format(new_level=new_level)
            reward_text = _("a special weapon")
            await self.create_item(**item)
            await self.log_transaction(
                ctx,
                from_=1,
                to=ctx.author.id,
                subject="item",
                data={"Name": item["name"], "Value": 1000},
                conn=conn,
            )
        elif reward == "money":
            money = new_level * 1000
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            await self.log_transaction(
                ctx,
                from_=1,
                to=ctx.author.id,
                subject="money",
                data={"Amount": money},
                conn=conn,
            )
            reward_text = f"**${money}**"

        additional = (
            _("You can now choose your second class using `{prefix}class`!").format(
                prefix=ctx.prefix
            )
            if old_level < 12 and new_level >= 12
            else ""
        )

        if local:
            await self.pool.release(conn)

        await ctx.send(
            _(
                "You reached a new level: **{new_level}** :star:! You received {reward}"
                " as a reward :tada:! {additional}"
            ).format(new_level=new_level, reward=reward_text, additional=additional)
        )

    async def clear_donator_cache(self, user):
        user = user if isinstance(user, int) else user.id
        await self.cogs["Sharding"].handler(
            "clear_donator_cache", 0, args={"user_id": user}
        )

    async def load_bans(self):
        bans = await self.pool.fetch('SELECT "user" FROM bans;')
        self.bans = {ban["user"] for ban in bans}
        self.logger.info(f"Loaded {len(self.bans)} bans")

    async def reload_bans(self):
        await self.cogs["Sharding"].handler("reload_bans", 0)

    @cache(maxsize=8096)
    async def get_donator_rank(self, user_id):
        if self.config.bot.is_beta or self.config.bot.is_custom:
            return DonatorRank.diamond

        if self.support_server_id is None:
            return False
        try:
            member = await self.http.get_member(self.support_server_id, user_id)
        except discord.NotFound:
            return False
        top_donator_role = None
        member_roles = [int(i) for i in member.get("roles", [])]
        for role in self.config.external.donator_roles:
            if role.id in member_roles:
                top_donator_role = role.tier
        return getattr(DonatorRank, top_donator_role) if top_donator_role else None

    async def get_damage_armor_for(
        self, user, items=None, classes=None, race=None, conn=None
    ):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        if items is None:
            items = await self.get_equipped_items_for(user, conn=conn)
        if not classes or not race:
            row = await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', user)
            classes, race = row["class"], row["race"]

        if local:
            await self.pool.release(conn)

        damage = 0
        armor = 0

        classes = [i for c in classes if (i := class_from_string(c))]
        is_paragon = any(c.in_class_line(Paragon) for c in classes)
        is_ranger = any(c.in_class_line(Ranger) for c in classes)
        is_warrior = any(c.in_class_line(Warrior) for c in classes)
        is_thief = any(c.in_class_line(Thief) for c in classes)
        is_raider = any(c.in_class_line(Raider) for c in classes)
        is_caster = any(
            c.in_class_line(Mage) or c.in_class_line(Ritualist) for c in classes
        )

        for item in items:
            damage += item["damage"]
            armor += item["armor"]

            type_ = ItemType.from_string(item["type"])
            if type_ == ItemType.Spear and is_paragon:
                damage += 5
            elif (type_ == ItemType.Dagger or type_ == ItemType.Knife) and is_thief:
                damage += 5
            elif type_ == ItemType.Sword and is_warrior:
                damage += 5
            elif type_ == ItemType.Bow and is_ranger:
                damage += 10
            elif type_ == ItemType.Wand and is_caster:
                damage += 5
            elif type_ == ItemType.Axe and is_raider:
                damage += 5

        lines = [class_.get_class_line() for class_ in classes]
        grades = [class_.class_grade() for class_ in classes]
        for line, grade in zip(lines, grades):
            if line == Mage:
                damage += grade
            elif line == Warrior:
                armor += grade
            elif line == Paragon:
                damage += grade
                armor += grade
        if race == "Human":
            damage += 2
            armor += 2
        elif race == "Dwarf":
            damage += 1
            armor += 3
        elif race == "Elf":
            damage += 3
            armor += 1
        elif race == "Orc":
            armor += 4
        elif race == "Jikill":
            damage += 4
        return damage, armor

    async def log_transaction(self, ctx, from_, to, subject, data, conn=None):
        """Logs a transaction."""
        from_ = from_.id if isinstance(from_, (discord.Member, discord.User)) else from_
        to = to.id if isinstance(to, (discord.Member, discord.User)) else to
        timestamp = datetime.datetime.now()
        assert subject in [
            "crates",
            "money",
            "shop",
            "offer",
            "guild invest",
            "guild pay",
            "gambling",
            "bid",
            "item",
            "adventure",
            "merch",
            "sacrifice",
            "exchange",
            "trade",
            "alliance",
            "raid",
        ]

        id_map = {
            0: "Guild Bank",
            1: "Bot (added to player)",
            2: "Bot (removed from player)",
        }
        from_readable = from_ if from_ not in id_map else id_map[from_]
        to_readable = to if to not in id_map else id_map[to]
        data_ = "\n".join(
            [f"{name}: {content}" for name, content in data.items()]
        )  # data is expected to be a dict

        description = f"""\
From: {from_readable}
To: {to_readable}
Subject: {subject}
Command: {ctx.command.qualified_name}
{data_}"""

        if conn is None:
            conn = await self.pool.acquire()
            local = True
        else:
            local = False
        await conn.execute(
            'INSERT INTO transactions ("from", "to", "subject", "info",'
            ' "timestamp") VALUES ($1, $2, $3, $4, $5);',
            from_,
            to,
            subject,
            description,
            timestamp,
        )
        if subject == "shop":
            await conn.execute(
                'INSERT INTO market_history ("item", "name", "value", "type",'
                ' "damage", "armor", "signature", "price", "offer") VALUES ($1, $2,'
                " $3, $4, $5, $6, $7, $8, $9);",
                data["id"],
                data["name"],
                data["value"],
                data["type"],
                data["damage"],
                data["armor"],
                data["signature"],
                data["price"],
                data["offer"],
            )
        if local:
            await self.pool.release(conn)

    async def public_log(self, event: str):
        await self.http.send_message(self.config.game.bot_event_channel, event)

    async def get_city_buildings(self, guild_id, conn=None):
        if not guild_id:  # also catches guild_id = 0
            return False
        obj = conn or self.pool
        res = await obj.fetchrow(
            'SELECT c.* FROM city c JOIN guild g ON c."owner"=g."id" WHERE'
            ' g."id"=(SELECT alliance FROM guild WHERE "id"=$1);',
            guild_id,
        )
        if not res:
            return False

        return res

    async def delete_profile(self, user: int, conn=None):
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        items = await conn.fetch('SELECT id FROM allitems WHERE "owner"=$1;', user)
        items = [i["id"] for i in items]
        await self.delete_items(items, conn=conn)
        await conn.execute('DELETE FROM pets WHERE "user"=$1;', user)
        await conn.execute('DELETE FROM user_settings WHERE "user"=$1;', user)
        await conn.execute('DELETE FROM loot WHERE "user"=$1;', user)
        await conn.execute('DELETE FROM profile WHERE "user"=$1;', user)
        if local:
            await self.pool.release(conn)

    async def delete_items(self, items, conn=None):
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        await conn.execute('DELETE FROM inventory WHERE "item"=ANY($1);', items)
        await conn.execute('DELETE FROM market WHERE "item"=ANY($1);', items)
        await conn.execute('DELETE FROM allitems WHERE "id"=ANY($1);', items)
        if local:
            await self.pool.release(conn)
