from dataclasses import dataclass

from classes.items import ItemType


@dataclass
class Item:
    damage: float
    armor: float
    item_type: ItemType
    name: str
