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
from __future__ import annotations

from enum import Enum
from typing import Optional


class Hand(Enum):
    Left = "left"
    Right = "right"
    Both = "both"
    Any = "any"


# List of all item types in the game
# Values represent DB values
class ItemType(Enum):
    Sword = "Sword"
    Shield = "Shield"
    Axe = "Axe"
    Wand = "Wand"
    Dagger = "Dagger"
    Knife = "Knife"
    Spear = "Spear"
    Bow = "Bow"
    Hammer = "Hammer"
    Scythe = "Scythe"
    Howlet = "Howlet"

    @classmethod
    def from_string(cls, name: str) -> Optional[ItemType]:
        return cls.__members__.get(name, None)

    def get_hand(self) -> Hand:
        if self in TWO_HANDED_ITEM_TYPES:
            return Hand.Both
        elif self in LEFT_HANDED_ITEM_TYPES:
            return Hand.Left
        elif self in RIGHT_HANDED_ITEM_TYPES:
            return Hand.Right
        else:
            return Hand.Any


ALL_ITEM_TYPES = list(ItemType)
TWO_HANDED_ITEM_TYPES = (ItemType.Bow, ItemType.Scythe, ItemType.Howlet)
LEFT_HANDED_ITEM_TYPES = (ItemType.Shield,)
RIGHT_HANDED_ITEM_TYPES = (ItemType.Spear, ItemType.Wand)
ANY_HANDED_ITEM_TYPES = (
    ItemType.Sword,
    ItemType.Axe,
    ItemType.Dagger,
    ItemType.Knife,
    ItemType.Hammer,
)
