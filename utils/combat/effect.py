from __future__ import annotations

ALL_EFFECTS = (
    "weakened",
    "blind",
    "dazed",
    "bleeding",
    "poisoned",
    "marked",
    "shattered_armor",
)


class Effects:
    __slots__ = ALL_EFFECTS

    def __init__(
        self,
        weakened: int = 0,
        blind: int = 0,
        dazed: int = 0,
        bleeding: int = 0,
        poisoned: int = 0,
        marked: int = 0,
        shattered_armor: int = 0,
    ) -> None:
        # Deals 30% less damage
        self.weakened = weakened
        # Has a 50% chance to fail spells
        self.blind = blind
        # Cannot cast spells
        self.dazed = dazed
        # Takes 15 damage per tick
        self.bleeding = bleeding
        # Takes 30 damage per tick
        self.poisoned = poisoned
        # Healing is 80% less efficient on this target
        self.marked = marked
        # Armor is 50% less effective
        self.shattered_armor = shattered_armor

    def all(self):
        return [effect for effect in ALL_EFFECTS if getattr(self, effect) > 0]

    def merge_with(self, other: Effects) -> None:
        for effect in ALL_EFFECTS:
            setattr(self, effect, getattr(other, effect) + getattr(self, effect))

    def substract(self, other: Effects) -> None:
        for effect in ALL_EFFECTS:
            setattr(self, effect, getattr(self, effect) - getattr(other, effect))

    def tick(self) -> None:
        for effect in ALL_EFFECTS:
            setattr(self, effect, getattr(self, effect) - 1)
