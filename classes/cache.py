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
import decimal

import orjson

DECIMAL_COLUMNS = ("atkmultiply", "defmultiply", "luck")
BIGINT_COLUMNS = ("marriage", "user")
RECORD_COLUMNS = ("colour",)


def preprocess(obj):
    for key in obj:
        if key in DECIMAL_COLUMNS or key in BIGINT_COLUMNS:
            obj[key] = str(obj[key])
        elif key in RECORD_COLUMNS:
            obj[key] = dict(obj[key])
    return obj


def fix(json):
    for col in DECIMAL_COLUMNS:
        json[col] = decimal.Decimal(json[col])
    for col in BIGINT_COLUMNS:
        json[col] = int(json[col])
    return json


class FakeRecord(object):
    """
    Object to mimic asyncpg.Record behavior.
    """

    def __init__(self, data):
        data = fix(data)
        self.__data = data
        self.__indices = list(data.keys())

    def __getattr__(self, name):
        try:
            return self.__data[name]
        except KeyError:
            raise AttributeError from None

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.__data[key]
        elif isinstance(key, int):
            return self.__data[self.__indices[key]]
        raise ValueError


class RedisCache:
    """
    Read-only cache forwarder to Redis.
    It is mainly responsible for profile data for now.
    """

    def __init__(self, bot):
        self.redis = bot.redis
        self.postgres = bot.pool

    async def get_profile(self, user_id, conn=None):
        """
        Gets the profile database entry for a user, preferably from Redis.
        If it is not in Redis, it gets the data from Postgres and inserts to Redis.
        """
        row = await self.redis.execute("GET", f"profilecache:{user_id}")
        if row is None:
            if conn is None:
                conn = await self.postgres.acquire()
                local = True
            else:
                local = False

            row = await conn.fetchrow('SELECT * FROM profile WHERE "user"=$1;', user_id)

            if local:
                await self.postgres.release(conn)

            if row is None:
                return None
            await self.redis.execute(
                "SET", f"profilecache:{user_id}", orjson.dumps(preprocess(dict(row))),
            )
            return row
        loaded = orjson.loads(row)
        return FakeRecord(loaded)

    async def update_profile_cols_rel(self, user_id, **vals):
        """
        Updates profile columns in the cache by a relative difference.
        """
        row = await self.redis.execute("GET", f"profilecache:{user_id}")
        if row is None:
            return None
        row = fix(orjson.loads(row))
        for key, val in vals.items():
            key = key.rstrip("_")
            if isinstance(val, (int, float, decimal.Decimal)):
                new_val = row[key] + val
            else:
                new_val = val
            row[key] = new_val
        await self.redis.execute(
            "SET", f"profilecache:{user_id}", orjson.dumps(preprocess(dict(row))),
        )

    async def update_profile_cols_abs(self, user_id, **vals):
        """
        Updates profile columns in the cache by an absolute value.
        """
        row = await self.redis.execute("GET", f"profilecache:{user_id}")
        if row is None:
            return None
        row = orjson.loads(row)
        for key, val in vals.items():
            row[key.rstrip("_")] = val
        await self.redis.execute(
            "SET", f"profilecache:{user_id}", orjson.dumps(preprocess(dict(row))),
        )

    async def wipe_profile(self, *user_ids):
        """
        Deletes the Redis cache for a profile.
        """
        user_ids = [f"profilecache:{i}" for i in user_ids]
        await self.redis.execute("DEL", *user_ids)

    async def get_profile_col(self, user_id, column_name, conn=None):
        """
        Gets a specific column from a user's profile utilizing the cache.
        """
        profile = await self.get_profile(user_id, conn=conn)
        if profile is None:
            return None
        return profile[column_name]
