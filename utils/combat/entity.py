from __future__ import annotations

from enum import Enum

from classes.classes import (
    GameClass,
    Mage,
    Paragon,
    Raider,
    Ranger,
    Ritualist,
    Thief,
    Warrior,
)
from classes.items import ItemType
from utils.random import randint

from .effect import Effects
from .item import Item
from .skill import Action, BaseSkill, SkillDeck, SkillType, Target


class Race(Enum):
    Jikill = 0
    Dwarf = 1
    Human = 2
    Elf = 3
    Orc = 4


class Faction(Enum):
    # Just a unique identifier for each side
    # so they can know who is friendly
    One = 0
    Two = 1


class Entity:
    def __init__(
        self,
        hp: float,
        faction: Faction,
        is_player: bool = False,
        deck: SkillDeck = SkillDeck.empty(),
        equipped_items: list[Item] = [],
        classes: list[GameClass] = [],
        race: Race | None = None,
    ):
        self.hp = hp
        self.faction = faction
        self.is_player = is_player
        self.equipped_items = equipped_items
        self.classes = classes
        self.race = race
        self.effects = Effects()
        self.deck = deck

    def can_attack(self, other: Entity) -> bool:
        return self.faction != other.faction

    def damage_against(self, other: Entity) -> float:
        damage = 0

        is_paragon = any(c.in_class_line(Paragon) for c in self.classes)
        is_ranger = any(c.in_class_line(Ranger) for c in self.classes)
        is_warrior = any(c.in_class_line(Warrior) for c in self.classes)
        is_thief = any(c.in_class_line(Thief) for c in self.classes)
        is_raider = any(c.in_class_line(Raider) for c in self.classes)
        is_caster = any(
            c.in_class_line(Mage) or c.in_class_line(Ritualist) for c in self.classes
        )

        for item in self.equipped_items:
            damage += item.damage

            if item.item_type == ItemType.Spear and is_paragon:
                damage += 5
            elif (
                item.item_type == ItemType.Dagger or item.item_type == ItemType.Knife
            ) and is_thief:
                damage += 5
            elif item.item_type == ItemType.Sword and is_warrior:
                damage += 5
            elif item.item_type == ItemType.Bow and is_ranger:
                damage += 10
            elif item.item_type == ItemType.Wand and is_caster:
                damage += 5
            elif item.item_type == ItemType.Axe and is_raider:
                damage += 5

        lines = [class_.get_class_line() for class_ in self.classes]
        grades = [class_.class_grade() for class_ in self.classes]
        for line, grade in zip(lines, grades):
            if line == Mage or line == Paragon:
                damage += grade

        if self.race == Race.Human:
            damage += 2
        elif self.race == Race.Dwarf:
            damage += 1
        elif self.race == Race.Elf:
            damage += 3
        elif self.race == Race.Jikill:
            damage += 4

        if self.effects.weakened:
            damage *= 0.7

        return damage

    def get_armor(self) -> float:
        armor = sum(i.armor for i in self.equipped_items)

        lines = [class_.get_class_line() for class_ in self.classes]
        grades = [class_.class_grade() for class_ in self.classes]
        for line, grade in zip(lines, grades):
            if line == Warrior or line == Paragon:
                armor += grade
        if self.race == Race.Human:
            armor += 2
        elif self.race == Race.Dwarf:
            armor += 3
        elif self.race == Race.Elf:
            armor += 1
        elif self.race == Race.Orc:
            armor += 4
        return armor

    def apply_damage_reducible(self, damage: float) -> None:
        armor = self.get_armor()
        if self.effects.shattered_armor:
            armor *= 0.5
        real_damage = damage - armor
        if real_damage < 0:
            return
        self.hp -= real_damage

    def apply_healing_reducible(self, healing: float) -> None:
        if self.effects.marked:
            healing *= 0.2
        self.hp += healing

    def attack(self, other: Entity) -> None:
        other.apply_damage_reducible(self.damage_against(other))

    def apply_action(self, action: Action) -> None:
        self.apply_damage_reducible(action.damage)
        self.apply_healing_reducible(action.healing)
        self.effects.merge_with(action.causes_effects)
        self.effects.substract(action.removes_effects)

    def use_skill(self, skill: BaseSkill, target: Entity) -> None:
        if skill.skill_type == SkillType.Spell and (
            self.effects.dazed or (self.effects.blind and randint(0, 1) == 0)
        ):
            return

        if not self.deck.available(skill):
            return
        self.deck.use(skill)
        for action in skill.actions:
            if (skill.target == Target.Friendly and self.faction != target.faction) or (
                skill.target == Target.Hostile and self.faction == target.faction
            ):
                continue
            if action.target == Target.Self:
                self.apply_action(action)
            else:
                target.apply_action(action)

    def tick(self) -> None:
        if self.effects.bleeding:
            self.hp -= 15
        if self.effects.poisoned:
            self.hp -= 30
        self.deck.tick()
        self.effects.tick()
