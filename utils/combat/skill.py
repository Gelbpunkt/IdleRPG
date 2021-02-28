from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .effect import Effects


class Target(Enum):
    Self = 0
    Friendly = 1
    Hostile = 2
    Any = 3


class SkillType(Enum):
    SpecialAttack = 0
    Spell = 1


@dataclass
class Action:
    target: Target
    damage: float
    healing: float
    causes_effects: Effects
    removes_effects: Effects


@dataclass
class BaseSkill:
    skill_type: SkillType
    actions: list[Action]
    name: str
    recharge: int


# Some really dumb example
devouring_slash = BaseSkill(
    skill_type=SkillType.SpecialAttack,
    actions=[
        Action(
            target=Target.Hostile,
            damage=100,
            healing=0,
            causes_effects=Effects(bleeding=2),
            removes_effects=Effects(),
        )
    ],
    name="Devouring Slash",
    recharge=2,
)


class SkillDeck:
    def __init__(self, skills: list[BaseSkill]) -> None:
        self.skills = {skill: 0 for skill in skills}

    def use(self, skill: BaseSkill) -> None:
        self.skills[skill] = skill.recharge

    def available(self, skill: BaseSkill) -> bool:
        return self.skills.get(skill, -1) == 0

    def tick(self) -> None:
        self.skills = {(k, v - 1) if v != 0 else (k, 0) for k, v in self.skills.items()}

    @classmethod
    def empty(self) -> SkillDeck:
        return SkillDeck([])
