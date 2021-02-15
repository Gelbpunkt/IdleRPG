import time

from discord.ext.commands import BucketType


class Cooldown:
    __slots__ = (
        "initial_tokens",
        "tokens",
        "max",
        "refill_interval",
        "refill_amount",
        "_last_refill",
        "type",
    )

    def __init__(
        self,
        max: int,
        tokens: int,
        refill_amount: int,
        refill_interval: float,
        type: BucketType,
    ) -> None:
        self.initial_tokens = float(tokens)
        self.tokens = float(tokens)
        self.max = float(max)
        self.refill_interval = float(refill_interval)
        self.refill_amount = float(refill_amount)
        self._last_refill = time.time()
        self.type = type

    def update_tokens(self, current: float) -> None:
        time_passed = current - self._last_refill
        refills_since = time_passed / self.refill_interval
        self._last_refill = current
        self.tokens += refills_since * self.refill_amount
        if self.tokens > self.max:
            self.tokens = self.max

    def get_retry_after(self, current: float = None):
        current = current or time.time()
        tokens = self.get_tokens(current)

        if tokens < 1:
            tokens_needed = 1 - tokens
            refills_needed = tokens_needed / self.refill_amount
            return self.refill_interval * refills_needed
        return 0.0

    def update_rate_limit(self, current: float = None):
        current = current or time.time()
        self.update_tokens(current)

        if self.tokens >= 1:
            self.tokens -= 1
        else:
            tokens_needed = 1 - self.tokens
            refills_needed = tokens_needed / self.refill_amount
            return self.refill_interval * refills_needed

    def is_full_at(self, current: float = None):
        self.update_tokens(current)
        return self.tokens == self.max

    def reset(self):
        self.tokens = self.initial_tokens
        self._last_refill = time.time()

    def copy(self):
        return Cooldown(
            self.max,
            self.initial_tokens,
            self.refill_amount,
            self.refill_interval,
            self.type,
        )

    def __repr__(self):
        return "<Cooldown max: {0.max} initial_tokens: {0.initial_tokens} refill_amount: {0.refill_amount} refill_interval: {0.refill_interval}>".format(
            self
        )


class CooldownMapping:
    def __init__(self, original):
        self._cache = {}
        self._cooldown = original

    def copy(self):
        ret = CooldownMapping(self._cooldown)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self):
        return self._cooldown is not None

    @classmethod
    def from_cooldown(cls, rate, per, type):
        return cls(Cooldown(rate, per, type))

    def _bucket_key(self, msg):
        return self._cooldown.type.get_key(msg)

    def _verify_cache_integrity(self, current=None):
        # we want to delete all cache objects that haven't been used
        # in a cooldown window. e.g. if we have a  command that has a
        # cooldown of 60s and it has not been used in 60s then that key should be deleted
        current = current or time.time()
        dead_keys = [k for k, v in self._cache.items() if v.is_full_at(current)]
        for k in dead_keys:
            del self._cache[k]

    def get_bucket(self, message, current=None):
        if self._cooldown.type is BucketType.default:
            return self._cooldown

        self._verify_cache_integrity(current)
        key = self._bucket_key(message)
        if key not in self._cache:
            bucket = self._cooldown.copy()
            self._cache[key] = bucket
        else:
            bucket = self._cache[key]

        return bucket

    def update_rate_limit(self, message, current=None):
        bucket = self.get_bucket(message, current)
        return bucket.update_rate_limit(current)
