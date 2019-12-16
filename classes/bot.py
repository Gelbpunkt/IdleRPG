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
import base64
import datetime
import io
import os
import random
import sys
import traceback

from decimal import Decimal

import aiohttp
import aioredis
import asyncpg
import discord
import fantasy_names as fn

from discord.ext import commands

import config

from classes.context import Context
from utils import i18n, paginator
from utils.checks import user_is_patron


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        self.cluster_name = kwargs.pop("cluster_name")
        super().__init__(
            command_prefix=config.global_prefix, **kwargs
        )  # we overwrite the prefix when it is connected

        # setup stuff
        self.queue = asyncio.Queue(loop=self.loop)  # global queue for ordered tasks
        self.config = config
        self.version = config.version
        self.paginator = paginator
        self.BASE_URL = config.base_url
        self.bans = config.bans
        self.remove_command("help")
        self.linecount = 0
        self.make_linecount()
        self.all_prefixes = {}
        # self.verified = []
        self.activity = discord.Game(
            name=f"IdleRPG v{config.version}" if config.is_beta else config.base_url
        )

        # global cooldown
        self.add_check(self.global_cooldown, call_once=True)

        self.launch_time = (
            datetime.datetime.now()
        )  # we assume the bot is created for use right now
        self.eligible_for_cooldown_reduce = set()  # caching
        self.not_eligible_for_cooldown_reduce = set()  # caching

    async def global_cooldown(self, ctx: commands.Context):
        if ctx.author.id in self.not_eligible_for_cooldown_reduce:
            bucket = self.config.cooldown.get_bucket(ctx.message)
        elif ctx.author.id in self.eligible_for_cooldown_reduce:
            bucket = self.config.donator_cooldown.get_bucket(ctx.message)
        else:
            if await user_is_patron(self, ctx.author, "Bronze Donators"):
                self.eligible_for_cooldown_reduce.add(ctx.author.id)
                bucket = self.config.donator_cooldown.get_bucket(ctx.message)
            else:
                self.not_eligible_for_cooldown_reduce.add(ctx.author.id)
                bucket = self.config.cooldown.get_bucket(ctx.message)

        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        else:
            return True

    def make_linecount(self):
        for root, dirs, files in os.walk(os.getcwd()):
            for file_ in files:
                if file_.endswith(".py"):
                    with open(f"{root}/{file_}") as f:
                        self.linecount += len(f.readlines())

    async def connect_all(self):
        self.session = aiohttp.ClientSession(trust_env=True)
        self.trusted_session = aiohttp.ClientSession()
        self.redis = await aioredis.create_pool(
            "redis://localhost", minsize=5, maxsize=10, loop=self.loop, db=0
        )
        self.pool = await asyncpg.create_pool(
            **self.config.database, max_size=20, command_timeout=60.0
        )

        for extension in self.config.initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()
        # self.loop.create_task(self.reset_verified())
        await self.start(self.config.token)

    async def reset_verified(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(random.randint(60 * 30, 60 * 120))
            self.verified = []

    def matches_prefix(self, message):
        prefixes = self._get_prefix(self, message)
        if type(prefixes) == str:
            return message.content.startswith(prefixes)
        return message.content.startswith(tuple(prefixes))

    async def on_message(self, message):
        if message.author.bot or message.author.id in self.bans:
            return
        locale = await self.get_cog("Locale").locale(message)
        i18n.current_locale.set(locale)
        # if message.author.id in self.verified:
        #    await self.process_commands(message)
        # elif self.matches_prefix(message):
        #    await self.create_captcha(message.author, message.channel)
        await self.process_commands(message)

    async def create_captcha(self, user, channel):
        async with self.session.get("https://captcha.travitia.xyz/v2") as r:
            data = await r.json()
        reactions = [data["solution"]] + data["others"]
        self.bans.append(user.id)  # prevent double captchas
        msg = await channel.send(
            _(
                "{user}, we have to verify you're not a bot. Please react with the emoji you see. You have 15 seconds and one attempt."
            ).format(user=user.mention),
            file=discord.File(
                filename="captcha.png",
                fp=io.BytesIO(base64.b64decode(data["image"][22:])),
            ),
        )
        random.shuffle(reactions)
        for reaction in reactions:
            await msg.add_reaction(reaction)

        def check(r, u):
            return r.emoji in reactions and r.message.id == msg.id and u == user

        try:
            r, u = await self.wait_for("reaction_add", check=check, timeout=15)
        except asyncio.TimeoutError:
            return await channel.send(
                _("{user}, you took too long and were banned.").format(
                    user=user.mention
                )
            )
        if r.emoji == data["solution"]:
            await channel.send(
                _("{user}, you have been verified!").format(user=user.mention)
            )
            self.bans.remove(user.id)
            self.verified.append(user.id)
        else:
            await channel.send(
                _("{user}, that was wrong! I have banned you.").format(
                    user=user.mention
                )
            )

    @property
    def uptime(self):
        return datetime.datetime.now() - self.launch_time

    async def get_ranks_for(self, thing):
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        async with self.pool.acquire() as conn:
            xp = await conn.fetchval(
                "SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.xp DESC) AS position FROM profile) s WHERE s.user = $1 LIMIT 1;",
                v,
            )
            money = await conn.fetchval(
                "SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.money DESC) AS position FROM profile) s WHERE s.user = $1 LIMIT 1;",
                v,
            )
        return money, xp

    async def get_raidstats(
        self,
        thing,
        atkmultiply=None,
        defmultiply=None,
        classes=None,
        race=None,
        guild=None,
        conn=None,
    ):
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        sword, shield = await self.get_equipped_items_for(v, conn=conn)
        if (
            atkmultiply is None
            or defmultiply is None
            or classes is None
            or guild is None
        ):
            atkmultiply, defmultiply, classes, race, guild = await conn.fetchval(
                'SELECT (atkmultiply, defmultiply, class, race, guild) FROM profile WHERE "user"=$1;',
                v,
            )
        if (buildings := await self.get_city_buildings(guild)) :
            atkmultiply += buildings["raid_building"] * 0.1
            defmultiply += buildings["raid_building"] * 0.1
        if self.in_class_line(classes, "Raider"):
            atkmultiply = atkmultiply + Decimal("0.1") * self.get_class_grade_from(
                classes, "Raider"
            )
        dmg = sword["damage"] * atkmultiply if sword else 0
        if self.in_class_line(classes, "Raider"):
            defmultiply = defmultiply + Decimal("0.1") * self.get_class_grade_from(
                classes, "Raider"
            )
        deff = shield["armor"] * defmultiply if shield else 0
        if local:
            await conn.close()
        return await self.generate_stats(v, dmg, deff, classes=classes, race=race)

    async def get_equipped_items_for(self, thing, conn=None):
        v = thing.id if isinstance(thing, (discord.Member, discord.User)) else thing
        local = False
        if conn is None:
            conn = await self.pool.acquire()
            local = True
        sword = await conn.fetchrow(
            "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
            v,
        )
        shield = await conn.fetchrow(
            "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
            v,
        )
        if local:
            await conn.close()
        return sword, shield

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    def _get_prefix(self, bot, message):
        if not message.guild:
            return self.config.global_prefix  # Use global prefix in DMs
        try:
            return commands.when_mentioned_or(self.all_prefixes[message.guild.id])(
                self, message
            )
        except KeyError:
            return commands.when_mentioned_or(self.config.global_prefix)(self, message)

    async def wait_for_dms(self, event, check, timeout=30):
        try:
            data = (
                await self.cogs["Sharding"].handler(
                    action="wait_for_dms",
                    args={"event": event, "check": check, "timeout": timeout},
                    expected_count=1,
                    _timeout=timeout,
                )
            )[0]
        except IndexError:
            raise asyncio.TimeoutError()
        if event == "message":
            channel_id = int(data["channel_id"])
            channel = (
                self.get_channel(channel_id)
                or self.get_user(int(data["author"]["id"])).dm_channel
            )
            return discord.Message(state=self._connection, channel=channel, data=data)
        elif event == "reaction_add":
            emoji = discord.PartialEmoji(
                name=data["emoji"]["name"],
                id=int(id_) if (id_ := data["emoji"]["id"]) else id_,
                animated=data["emoji"].get("animated", False),
            )
            message = discord.utils.get(
                self._connection._messages, id=int(data["message_id"])
            )
            reaction = discord.Reaction(
                message=message, emoji=emoji, data={"me": False}
            )
            return reaction, await self.get_user_global(int(data["user_id"]))

    async def get_user_global(self, user_id: int):
        user = self.get_user(user_id)
        if user:
            return user
        data = await self.cogs["Sharding"].handler("get_user", 1, {"user_id": user_id})
        if not data:
            return None
        data = data[0]
        data["username"] = data["name"]
        user = discord.User(state=self._connection, data=data)
        self.users.append(user)
        return user

    async def reset_cooldown(self, ctx):
        await self.redis.execute(
            "DEL", f"cd:{ctx.author.id}:{ctx.command.qualified_name}"
        )

    async def reset_guild_cooldown(self, ctx):
        await self.redis.execute(
            "DEL", f"guildcd:{ctx.character_data['guild']}:{ctx.command.qualified_name}"
        )

    async def activate_booster(self, user, type_):
        if type_ not in ["time", "luck", "money"]:
            raise ValueError("Not a valid booster type.")
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute("SET", f"booster:{user}:{type_}", 1, "EX", 86400)

    async def get_booster(self, user, type_):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        val = await self.redis.execute("TTL", f"booster:{user}:{type_}")
        return datetime.timedelta(seconds=val) if val != -2 else None

    async def start_adventure(self, user, number, time):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute(
            "SET", f"adv:{user}", number, "EX", int(time.total_seconds()) + 259_200
        )  # +3 days

    async def get_adventure(self, user):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        ttl = await self.redis.execute("TTL", f"adv:{user}")
        if ttl == -2:
            return
        num = await self.redis.execute("GET", f"adv:{user}")
        ttl = ttl - 259_200
        done = ttl <= 0
        time = datetime.timedelta(seconds=ttl)
        return int(num.decode("ascii")), time, done

    async def delete_adventure(self, user):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        await self.redis.execute("DEL", f"adv:{user}")

    async def has_money(self, user, money, conn=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn:
            return (
                await conn.fetchval('SELECT money FROM profile WHERE "user"=$1;', user)
                >= money
            )
        else:
            return (
                await self.pool.fetchval(
                    'SELECT money FROM profile WHERE "user"=$1;', user
                )
                >= money
            )

    async def has_crates(self, user, crates, rarity, conn=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if conn:
            return (
                await conn.fetchval(
                    f'SELECT "crates_{rarity}" FROM profile WHERE "user"=$1;', user
                )
                >= crates
            )
        else:
            return (
                await self.pool.fetchval(
                    f'SELECT "crates_{rarity}" FROM profile WHERE "user"=$1;', user
                )
                >= crates
            )

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
        await self.redis.execute(
            "SET",
            f"guildadv:{guild}",
            difficulty,
            "EX",
            int(time.total_seconds()) + 259_200,
        )  # +3 days

    async def get_guild_adventure(self, guild):
        ttl = await self.redis.execute("TTL", f"guildadv:{guild}")
        if ttl == -2:
            return
        num = await self.redis.execute("GET", f"guildadv:{guild}")
        ttl = ttl - 259_200
        done = ttl <= 0
        time = datetime.timedelta(seconds=ttl)
        return int(num.decode("ascii")), time, done

    async def delete_guild_adventure(self, guild):
        await self.redis.execute("DEL", f"guildadv:{guild}")

    async def create_item(
        self, name, value, type_, damage, armor, owner, equipped=False
    ):
        owner = owner.id if isinstance(owner, (discord.User, discord.Member)) else owner
        async with self.pool.acquire() as conn:
            item = await conn.fetchrow(
                'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                owner,
                name,
                value,
                type_,
                damage,
                armor,
            )
            await conn.execute(
                'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                item["id"],
                equipped,
            )
        return item

    async def create_random_item(
        self, minstat, maxstat, minvalue, maxvalue, owner, insert=True
    ):
        owner = owner.id if isinstance(owner, (discord.User, discord.Member)) else owner
        item = {}
        item["owner"] = owner
        type_ = random.choice(["Sword", "Shield"])
        item["type_"] = type_
        item["damage"] = random.randint(minstat, maxstat) if type_ == "Sword" else 0
        item["armor"] = random.randint(minstat, maxstat) if type_ == "Shield" else 0
        item["value"] = random.randint(minvalue, maxvalue)
        item["name"] = fn.weapon_name(type_)
        if insert:
            return await self.create_item(**item)
        return item

    async def process_levelup(self, ctx, new_level):
        if (reward := random.choice(["crates", "money", "item"])) == "crates":
            if new_level < 6:
                column = "crates_common"
                amount = new_level
                reward_text = f"**{amount}** <:CrateCommon:598094865666015232>"
            elif new_level < 10:
                column = "crates_uncommon"
                amount = round(new_level / 2)
                reward_text = f"**{amount}** <:CrateUncommon:598094865397579797>"
            elif new_level < 15:
                column = "crates_rare"
                amount = 2
                reward_text = "**2** <:CrateRare:598094865485791233>"
            elif new_level < 20:
                column = "crates_rare"
                amount = 3
                reward_text = "**3** <:CrateRare:598094865485791233>"
            else:
                column = "crates_magic"
                amount = 1
                reward_text = "**1** <:CrateMagic:598094865611358209>"
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
            )
            item["name"] = _("Level {new_level} Memorial").format(new_level=new_level)
            reward_text = _("a special weapon")
            await self.create_item(**item)
        elif reward == "money":
            money = new_level * 1000
            await self.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            reward_text = f"**${money}**"

        await ctx.send(
            _(
                "You reached a new level: **{new_level}** :star:! You received {reward} as a reward :tada:!"
            ).format(new_level=new_level, reward=reward_text)
        )

    def in_class_line(self, classes, line):
        return any([self.get_class_line(c) == line for c in classes])

    def get_class_grade_from(self, classes, line):
        for class_ in classes:
            if self.get_class_line(class_) == line:
                return self.get_class_grade(class_)
        return None

    def get_class_line(self, class_):
        if class_ in ["Mage", "Wizard", "Pyromancer", "Elementalist", "Dark Caster"]:
            return "Mage"
        elif class_ in ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"]:
            return "Warrior"
        elif class_ in ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"]:
            return "Thief"
        elif class_ in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
            return "Ranger"
        elif class_ in ["Novice", "Proficient", "Artisan", "Master", "Paragon"]:
            return "Paragon"
        elif class_ in ["Stabber", "Fighter", "Hero", "Dragonslayer", "Raider"]:
            return "Raider"
        elif class_ in ["Priest", "Mysticist", "Summoner", "Seer", "Ritualist"]:
            return "Ritualist"
        else:
            return "None"

    def get_class_evolves(self):
        return {
            "Mage": ["Wizard", "Pyromancer", "Elementalist", "Dark Caster"],
            "Thief": ["Rogue", "Chunin", "Renegade", "Assassin"],
            "Warrior": ["Swordsman", "Knight", "Warlord", "Berserker"],
            "Paragon": ["Proficient", "Artisan", "Master", "Paragon"],
            "Ranger": ["Trainer", "Bowman", "Hunter", "Ranger"],
            "Raider": ["Fighter", "Hero", "Dragonslayer", "Raider"],
            "Ritualist": ["Mysticist", "Summoner", "Seer", "Ritualist"],
        }

    def get_class_grade(self, class_):
        if class_ in ["Mage", "Wizard", "Pyromancer", "Elementalist", "Dark Caster"]:
            return [
                "Mage",
                "Wizard",
                "Pyromancer",
                "Elementalist",
                "Dark Caster",
            ].index(class_) + 1
        elif class_ in ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"]:
            return ["Warrior", "Swordsman", "Knight", "Warlord", "Berserker"].index(
                class_
            ) + 1
        elif class_ in ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"]:
            return ["Thief", "Rogue", "Chunin", "Renegade", "Assassin"].index(
                class_
            ) + 1
        elif class_ in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
            return ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"].index(
                class_
            ) + 1
        elif class_ in ["Novice", "Proficient", "Artisan", "Master", "Paragon"]:
            return ["Novice", "Proficient", "Artisan", "Master", "Paragon"].index(
                class_
            ) + 1
        elif class_ in ["Stabber", "Fighter", "Hero", "Dragonslayer", "Raider"]:
            return ["Stabber", "Fighter", "Hero", "Dragonslayer", "Raider"].index(
                class_
            ) + 1
        elif class_ in ["Priest", "Mysticist", "Summoner", "Seer", "Ritualist"]:
            return ["Priest", "Mysticist", "Summoner", "Seer", "Ritualist"].index(
                class_
            ) + 1
        else:
            return 0

    async def generate_stats(self, user, damage, armor, classes=None, race=None):
        user = user.id if isinstance(user, (discord.User, discord.Member)) else user
        if not classes or not race:
            classes, race = await self.pool.fetchval(
                'SELECT ("class"::text[], "race"::text) FROM profile WHERE "user"=$1;',
                user,
            )
        lines = [self.get_class_line(class_) for class_ in classes]
        grades = [self.get_class_grade(class_) for class_ in classes]
        for line, grade in zip(lines, grades):
            if line == "Mage":
                damage += grade
            elif line == "Warrior":
                armor += grade
            elif line == "Paragon":
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

    async def log_transaction(self, ctx, from_, to, subject, data):
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
        ]
        if isinstance(data, int):
            description = f"""\
{ctx.channel} in {ctx.guild or 'DMs'}
From: {(self.get_user(from_) or 'Unknown User') if from_ != 0 else 'Guild Bank'}
To:   {(self.get_user(to) or 'Unknown User') if to != 0 else 'Guild Bank'}
Subject: {subject}
Amount: {data}"""
        elif isinstance(data, list):
            description = f"""\
{ctx.channel} in {ctx.guild or 'DMs'}
From: {(self.get_user(from_) or 'Unknown User')}
To:   {(self.get_user(to) or 'Unknown User')}
Subject: {subject}
Amount: {data[0]}
Rarity: {data[1]}"""
        else:
            description = f"""\
{ctx.channel} in {ctx.guild or 'DMs'}
From: {self.get_user(from_) or 'Unknown User'}
To:   {self.get_user(to) or 'Unknown User'}
Subject: {subject} (Item)
Name: {data['name']}
Value: {data['value']}
ID: {data['id']}
Type: {data['type']}
Damage: {data['damage']}
Armor: {data['armor']}"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO transactions ("from", "to", "subject", "info", "timestamp") VALUES ($1, $2, $3, $4, $5);',
                from_,
                to,
                subject,
                description,
                timestamp,
            )
            if subject == "shop":
                await conn.execute(
                    'INSERT INTO market_history ("item", "name", "value", "type", "damage", "armor", "signature", "price", "offer") VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);',
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

    async def public_log(self, event: str):
        await self.http.send_message(self.config.bot_event_channel, event)

    async def get_city_buildings(self, guild_id):
        if not guild_id:  # also catches guild_id = 0
            return False
        res = await self.pool.fetchrow(
            'SELECT c.* FROM city c JOIN guild g ON c."owner"=g."id" WHERE g."id"=(SELECT alliance FROM guild WHERE "id"=$1);',
            guild_id,
        )
        if not res:
            return False

        return res
