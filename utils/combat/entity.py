from __future__ import annotations

from classes.classes import GameClass

from .effect import Effects
from .item import Item
from .skill import BaseSkill


class Entity:
    def __init__(
        self,
        hp: float,
        is_player: bool = False,
        equipped_items: list[Item] = [],
        classes: list[GameClass] = [],
    ):
        self.hp = hp
        self.is_player = is_player
        self.equipped_items = equipped_items
        self.classes = classes
        self.effects = Effects()

    def can_attack(self, other: Entity) -> bool:
        raise NotImplementedError

    def damage_against(self, other: Entity) -> float:
        raise NotImplementedError

    def apply_damage_reducible(self, damage: float) -> None:
        self.hp -= damage
        raise NotImplementedError("needs to have effects taken into account")

    def apply_healing_reducible(self, healing: float) -> None:
        self.hp += healing
        raise NotImplementedError("needs to have effects taken into account")

    def attack(self, other: Entity) -> None:
        other.apply_damage_reducible(self.damage_against(other))

    def apply_skill(self, skill: BaseSkill) -> None:
        self.apply_damage_reducible(skill.damage)
        self.apply_healing_reducible(skill.healing)
        self.effects.merge_with(skill.causes_effects)
        self.effects.substract(skill.removes_effects)
