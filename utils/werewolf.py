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
# This is an implementation of Werewolf: The Pact
# The Pact includes the extensions:
# - New Moon
# - The Community
# - Characters
# I have left out the raven and the pyro from "The Community"
# the house part is not my favourite
# The "New Moon" cards are also not included, hence
# the shake and the gypsy are not here
# "Werewolf" is a game by Philippe des Pallières and Hervé Marly
# Thank you for making such an awesome game!
from __future__ import annotations

import random

from enum import Enum
from typing import List, Optional
from pprint import pprint

import discord


class Role(Enum):
    WEREWOLF = 1
    BIG_BAD_WOLF = 2

    VILLAGER = 3
    PURE_SOUL = 4
    SEER = 5
    AMOR = 6
    WITCH = 7
    HUNTER = 8
    HEALER = 9
    THE_OLD = 10
    SCAPEGOAT = 11
    FOOL = 12
    SISTER = 13
    BROTHER = 14
    FOX = 15
    JUDGE = 16
    KNIGHT = 17

    WHITE_WOLF = 18
    THIEF = 19
    MAID = 20
    WILD_CHILD = 21
    WOLFHOUND = 22

    FLUTIST = 23


class Side(Enum):
    VILLAGERS = 1
    WOLVES = 2
    WHITE_WOLF = 3
    FLUTIST = 4


class Game:
    def __init__(self, number_of_players: int) -> None:
        self.available_roles = get_roles(number_of_players)
        self.available_roles, self.extra_roles = (
            self.available_roles[:-2],
            self.available_roles[-2:],
        )
        self.players: List[Player] = [
            Player(role, self) for role in self.available_roles
        ]
        random.choice(self.players).is_sheriff = True

    @property
    def sheriff(self) -> Player:
        return discord.utils.get(self.players, is_sheriff=True)

    @property
    def alive_players(self) -> List[Player]:
        return [player for player in self.players if not player.dead]

    def get_players_with_role(self, role: Role) -> List[Player]:
        return [player for player in self.alive_players if player.role == role]

    def winner(self) -> Optional[Player]:
        objective_reached = discord.utils.get(self.alive_players, has_won=True)
        if objective_reached:
            return objective_reached
        if len(self.alive_players) < 2:
            try:
                return self.alive_players[0]
            except IndexError:
                return "Noone"

    @property
    def lovers(self) -> List[Player]:
        return [player for player in self.alive_players if player.in_love]

    def wolves(self) -> Optional[Player]:
        healer = discord.utils.get(self.alive_players, role=Role.HEALER)
        if healer:
            protected = healer.get_healer_target()
        else:
            protected = None
        wolves = [
            p
            for p in self.alive_players
            if p.side == Side.WOLVES or p.side == Side.WHITE_WOLF
        ]
        # Get target of wolves
        possible_targets = [p for p in self.alive_players if p not in wolves]
        target = random.choice(possible_targets)
        print(f"Wolves chose {target}")
        if target == protected:
            return None
        else:
            return target

    def initial_preparation(self) -> List[Player]:
        for player in self.players:
            player.send_information()
        wolfhound = self.get_players_with_role(Role.WOLFHOUND)
        if wolfhound:
            wolfhound[0].choose_role_from([Role.VILLAGER, Role.WEREWOLF])
        thieves = self.get_players_with_role(Role.THIEF)
        if thieves:
            thieves[0].choose_role_from(self.extra_roles)
        amor = self.get_players_with_role(Role.AMOR)
        if amor:
            amor[0].choose_lovers()
        seer = self.get_players_with_role(Role.SEER)
        if seer:
            seer[0].check_player_card()
        fox = self.get_players_with_role(Role.FOX)
        if fox:
            fox[0].check_3_werewolves()
        if amor:
            for player in self.lovers:
                player.send_love_msg()
        judge = self.get_players_with_role(Role.JUDGE)
        if judge:
            judge[0].get_judge_symbol()
        sisters = self.get_players_with_role(Role.SISTER)
        if sisters:
            for player in sisters:
                player.send_family_msg("sister", sisters)
        brothers = self.get_players_with_role(Role.BROTHER)
        if brothers:
            for player in brothers:
                player.send_family_msg("brother", brothers)
        wild_child = self.get_players_with_role(Role.WILD_CHILD)
        if wild_child:
            wild_child[0].choose_idol()
        target = self.wolves()
        targets = [target] if target is not None else []
        if (
            sum(
                1
                for player in self.players
                if player.dead and player.role == Role.WEREWOLF
            )
            == 0
        ):
            big_bad_wolf = self.get_players_with_role(Role.BIG_BAD_WOLF)
            if big_bad_wolf:
                targets.append(big_bad_wolf[0].choose_villager_to_kill())
        witch = self.get_players_with_role(Role.WITCH)
        if witch:
            targets = witch[0].witch_actions(targets)
        flutist = self.get_players_with_role(Role.FLUTIST)
        if flutist:
            possible_targets = [
                p for p in self.alive_players if not p.enchanted and p != flutist[0]
            ]
            flutist[0].enchant(possible_targets)
        final_targets = targets[:]
        for target in targets:
            if target.in_love:
                final_targets.append([p for p in self.lovers if p != target][0])
        return final_targets

    def night(self, white_wolf: bool) -> List[Player]:
        seer = self.get_players_with_role(Role.SEER)
        if seer:
            seer[0].check_player_card()
        fox = self.get_players_with_role(Role.FOX)
        if fox:
            fox[0].check_3_werewolves()
        print(self.alive_players)
        target = self.wolves()
        targets = [target] if target is not None else []
        white_wolf = self.get_players_with_role(Role.WHITE_WOLF)
        if white_wolf:
            target = white_wolf[0].choose_werewolf()
            if target:
                targets.append(target)
        if (
            sum(
                1
                for player in self.players
                if player.dead and player.role == Role.WEREWOLF
            )
            == 0
        ):
            big_bad_wolf = self.get_players_with_role(Role.BIG_BAD_WOLF)
            if big_bad_wolf:
                targets.append(big_bad_wolf[0].choose_villager_to_kill())
        flutist = self.get_players_with_role(Role.FLUTIST)
        if flutist:
            possible_targets = [
                p for p in self.alive_players if not p.enchanted and p != flutist[0]
            ]
            flutist[0].enchant(possible_targets)
        return targets

    def day(self, deaths: List[Player]) -> None:
        for death in deaths:
            death.kill()
            print(f"{death} lost a life.")
        if len(self.alive_players) < 2:
            return
        to_kill = random.choice(self.alive_players)
        to_kill.kill()
        if to_kill.dead:
            maid = self.get_players_with_role(Role.MAID)
            if maid:
                maid[0].handle_maid(to_kill)
        judge = self.get_players_with_role(Role.JUDGE)
        if judge and random.randint(1, 2) == 1:  # new election by decision of judge
            to_kill = random.choice(self.alive_players)
            to_kill.kill()
            if to_kill.dead:
                maid = self.get_players_with_role(Role.MAID)
                if maid:
                    maid[0].handle_maid(to_kill)

    def run(self):
        # Handle thief etc and first night
        deaths = self.initial_preparation()
        round_no = 1
        night_no = 1
        while self.winner() is None:
            if round_no % 2 == 1:
                self.day(deaths)
            else:
                night_no += 1
                deaths = self.night(white_wolf=night_no % 2 == 0)
            round_no += 1
        print(f"{self.winner()} won")

class Player:
    def __init__(self, role: Role, game: Game) -> None:
        self.role = role
        self.initial_role = role
        self.game = game
        self.is_sheriff = False
        self.enchanted = False
        self.in_love = False
        self.idol = None

        # Witch
        self.can_heal = True
        self.can_kill = True

        if role == Role.THE_OLD:
            self.lives = 2
        else:
            self.lives = 1

        if role == Role.WILD_CHILD:
            self.role = Role.VILLAGER

    def __repr__(self):
        return f"<Player role={self.role} initial_role={self.initial_role} is_sheriff={self.is_sheriff} lives={self.lives} side={self.side} dead={self.dead} won={self.has_won}>"

    def send_information(self) -> None:
        pass

    def send_love_msg(self) -> None:
        print("Received love msg")

    def choose_idol(self) -> None:
        idol = random.choice(self.game.players)
        print(f"Chose idol {idol}.")

    def get_judge_symbol(self) -> str:
        symbol = "hahayes"
        print(f"Judge symbol is {symbol}.")
        return symbol

    def handle_maid(self, death: Player) -> None:
        if random.randint(1, 2) == 1 and not self.in_love:
            print(f"Maid swaps cards with {death}")
            self.enchanted = False
            if self.is_sheriff:
                self.is_sheriff = False
                random.choice(self.game.alive_players).is_sheriff = True
            self.role = death.role
        else:
            print("Maid does nothing.")

    def get_healer_target(self) -> Player:
        target = random.choice(self.game.alive_players)
        print(f"Healer protects {target}.")
        return target

    def choose_werewolf(self) -> Optional[Player]:
        possible_targets = [p for p in self.game.alive_players if p.side == Side.WOLVES]
        if random.randint(1, 2) == 1 and possible_targets:
            target = random.choice(possible_targets)
            print(f"White wolf chose {target}")
            return target
        else:
            return None

    def choose_villager_to_kill(self) -> Player:
        target = random.choice(
            [p for p in self.game.alive_players if p.side == Side.VILLAGERS]
        )
        print(f"Big bad wolf chose {target}")
        return target

    def witch_actions(self, targets: List[Player]) -> Player:
        if random.randint(1, 2) == 1 and targets and self.can_heal:
            to_heal = random.choice(targets)
            targets.remove(to_heal)
            print(f"Witch healed {to_heal}")
            self.can_heal = False
        if random.randint(1, 2) == 1 and self.can_kill:
            possible_targets = [
                p for p in self.game.alive_players if p != self and p not in targets
            ]
            targets.append(random.choice(possible_targets))
            self.can_kill = False
            print(f"Witch killed {targets}")
        return targets

    def enchant(self, possible_targets: List[Player]) -> None:
        if len(possible_targets) > 2:
            to_enchant = random.sample(possible_targets, 2)
        else:
            to_enchant = possible_targets
        for p in to_enchant:
            p.enchanted = True
            print(f"Flutist enchanted {p}")

    def send_family_msg(self, relationship: str, family: List[Player]) -> None:
        print(f"Sending {relationship} msg...")

    def check_player_card(self) -> None:
        target = random.choice(self.game.alive_players)
        print(f"Chose {target} for seer inspection")

    def choose_role_from(self, roles: List[Role]) -> None:
        role = random.choice(roles)
        print(f"{self} chose {role} out of {roles}")
        self.role = role

    def check_3_werewolves(self):
        if random.randint(1, 2) == 1:
            targets = random.sample(self.game.alive_players, 3)
            if not any([target.side == Side.WOLVES for target in targets]):
                self.role = Role.VILLAGER
                print("Fox found no wolf.")
            else:
                print(f"Fox inspected {targets}.")
        else:
            print("Fox refused to check anyone")

    def choose_lovers(self) -> None:
        lovers = random.sample(self.game.players, 2)
        for lover in lovers:
            lover.in_love = True
        print(f"Chose {lovers} as lovers")

    @property
    def dead(self) -> bool:
        return self.lives < 1

    def kill(self) -> None:
        self.lives -= 1

    @property
    def side(self) -> Side:
        if 1 <= self.role.value <= 2:
            return Side.WOLVES
        if 3 <= self.role.value <= 17:
            return Side.VILLAGERS
        else:
            return getattr(Side, self.role.name, "NAN")

    @property
    def has_won(self) -> bool:
        # Returns whether the player has reached their goal or not
        if self.side == Side.VILLAGERS:
            return not any(
                [
                    player.side == Side.WOLVES or player.side == Side.WHITE_WOLF
                    for player in self.game.alive_players
                ]
            )
        elif self.side == Side.WOLVES:
            return all([player.side == Side.WOLVES or player.side == Side.WHITE_WOLF for player in self.game.alive_players])
        elif self.side == Side.WHITE_WOLF:
            return len(self.game.players) == 1 and not self.dead
        elif self.side == Side.FLUTIST:
            return all(
                [player.enchanted or player == self for player in self.game.alive_players]
            )


# A list of roles to give depending on the number of total players
# Rule of thumb is to have 50+% of villagers, whereas thief etc count
# as wolves as there is a good chance they might become some
# This is the main subject to change for game balance
ROLES_FOR_PLAYERS: List[Role] = [
    Role.VILLAGER,
    Role.VILLAGER,
    Role.WEREWOLF,
    Role.SEER,
    Role.WITCH,
    Role.HUNTER,
    Role.THIEF,
    Role.WEREWOLF,
    Role.WILD_CHILD,
    Role.PURE_SOUL,
    Role.MAID,
    Role.VILLAGER,
    Role.WHITE_WOLF,
    Role.HEALER,
    Role.AMOR,
    Role.KNIGHT,
    Role.SISTER,
    Role.SISTER,
    Role.BIG_BAD_WOLF,
    Role.THE_OLD,
    Role.WEREWOLF,
    Role.WOLFHOUND,
    Role.SCAPEGOAT,
    Role.FOOL,
    Role.WEREWOLF,
    Role.FOX,
    Role.BROTHER,
    Role.BROTHER,
    Role.BROTHER,
    Role.JUDGE,
    Role.FLUTIST,
    Role.WEREWOLF,
    Role.VILLAGER,
]


def get_roles(number_of_players: int) -> List[Role]:
    number_of_players += 2  # Thief is in play
    if number_of_players > len(ROLES_FOR_PLAYERS):
        roles = ROLES_FOR_PLAYERS
        # Fill up with villagers and wolves as all special roles are taken
        for i in range(number_of_players - len(roles)):
            if i % 2 == 0:
                roles.append(Role.WEREWOLF)
            else:
                roles.append(Role.VILLAGER)
    else:
        roles = ROLES_FOR_PLAYERS[:number_of_players]
    if sum(1 for role in roles if role == Role.SISTER) == 1:
        for idx, role in enumerate(roles):
            if role == Role.SISTER:
                roles[idx] = Role.VILLAGER
    if sum(1 for role in roles if role == Role.BROTHER) < 3:
        for idx, role in enumerate(roles):
            if role == Role.BROTHER:
                roles[idx] = Role.VILLAGER
    random.shuffle(roles)
    return roles


if __name__ == "__main__":
    game = Game(50)
    game.run()
