from __future__ import annotations

from enum import Enum

from discord.flags import BaseFlags, fill_with_flags, flag_value


class EffectFlags(Enum):
    # Deals 30% less damage
    weakened = 1
    # Has a 50% chance to fail spells
    blind = 2
    # Cannot cast spells
    dazed = 4
    # Takes some damage over time
    bleeding = 8
    # Same as bleeding but more severe
    poisoned = 16
    # Healing is 80% less efficient on this target
    marked = 32
    # Armor is 50% less effective
    shattered_armor = 64


@fill_with_flags()
class Effects(BaseFlags):
    __slots__ = ()

    @flag_value
    def weakened(self):
        return EffectFlags.weakened.value

    @flag_value
    def blind(self):
        return EffectFlags.blind.value

    @flag_value
    def dazed(self):
        return EffectFlags.dazed.value

    @flag_value
    def bleeding(self):
        return EffectFlags.bleeding.value

    @flag_value
    def poisoned(self):
        return EffectFlags.poisoned.value

    @flag_value
    def marked(self):
        return EffectFlags.marked.value

    @flag_value
    def shattered_armor(self):
        return EffectFlags.shattered_armor.value

    def all(self):
        return [effect for effect in EffectFlags if self._has_flag(effect.value)]

    def merge_with(self, other: Effects) -> None:
        for effect in EffectFlags:
            if other._has_flag(effect.value):
                self._set_flag(effect.value, True)

    def substract(self, other: Effects) -> None:
        for effect in EffectFlags:
            if other._has_flag(effect.value):
                self._set_flag(effect.value, False)
