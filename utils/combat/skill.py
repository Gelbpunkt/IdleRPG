from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .effect import Effects


class Target(Enum):
    Friendly = 0
    Hostile = 1
    Any = 2


class SkillType(Enum):
    SpecialAttack = 0
    Spell = 1


@dataclass
class BaseSkill:
    skill_type: SkillType
    damage: float
    healing: float
    causes_effects: Effects
    removes_effects: Effects
    effects_duration: int
    target: Target
    name: str
    recharge: int

    @property
    def is_available(self) -> bool:
        raise NotImplementedError("last used tracking needs to be done")


# Some really dumb example
devouring_slash = BaseSkill(
    skill_type=SkillType.SpecialAttack,
    damage=100,
    healing=0,
    causes_effects=Effects(bleeding=2),
    removes_effects=Effects(),
    effects_duration=3,
    target=Target.Hostile,
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
