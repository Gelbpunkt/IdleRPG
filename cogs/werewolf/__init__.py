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
import asyncio

from typing import Optional

import discord

from discord.ext import commands

from classes.converters import IntGreaterThan, WerewolfMode
from cogs.help import chunks
from utils import random
from utils.i18n import _, locale_doc
from utils.werewolf import DESCRIPTIONS as ROLE_DESC
from utils.werewolf import Game
from utils.werewolf import Role as ROLES


class Werewolf(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.group(
        invoke_without_command=True,
        case_insensitive=True,
        aliases=["ww"],
        brief=_("Starts a game of Werewolf"),
    )
    @locale_doc
    async def werewolf(
        self,
        ctx,
        mode: Optional[WerewolfMode] = "Classic",
        speed: str.title = "Normal",
        min_players: IntGreaterThan(1) = None,
    ):
        _(
            """
            `[mode]` - The mode to play, see below for available options. (optional and defaults to Classic)
            `[speed]` - The game speed to play, see below available options. (optional and defaults to Normal)
            `[min_players]` - The minimum players needed to play. (optional and defaults depending on the game mode: Classic: 5, Imbalanced: 5, Huntergame: 8, Villagergame: 5, Valentines: 8)

            Starts a game of Werewolf. Find the werewolves, before they find you!
            Your goal to win is indicated on the role you have.
            **Game modes:** `Classic` (default), `Imbalanced`, `Huntergame`, `Villagergame`, `Valentines`. Use `{prefix}ww modes` for detailed info.
            **Game speeds** (in seconds): `Normal`: 60 (default), `Extended`: 90, `Fast`: 45, `Blitz`: 30. Use `{prefix}ww speeds` for detailed info.
            **Aliases:**
            `ww`
            **Examples:**
            `{prefix}ww Blitz` for Classic mode on Blitz speed
            `{prefix}ww Imbalanced` for Imbalanced mode on Normal speed
            `{prefix}ww Valentines Extended` for Valentines mode on Extended speed
            `{prefix}ww Huntergame Fast` for Huntergame mode on Fast speed
            """
        )
        # TODO:
        # Bizarro: Roles are flipped.
        # Random: Roles are reassigned randomly every night.
        # IdleRPG: New roles available (most likely based on Imbalanced mode): Paragon, Raider, Ritualist, Were-Shaman, Zombie, Lawyer.
        # Zombie (Classic-based, another team) - There's a chance that a random player will be randomly resurrected as Zombie and they can devour any villagers or werewolves with the other zombies.
        if self.games.get(ctx.channel.id):
            return await ctx.send(_("There is already a game in here!"))
        game_modes = [
            "Classic",
            "Imbalanced",
            "Huntergame",
            "Villagergame",
            "Valentines",
        ]
        if mode not in game_modes:
            return await ctx.send(
                _(
                    "Invalid game mode. Use `{prefix}help ww` to get help on this"
                    " command."
                ).format(prefix=ctx.prefix)
            )
        game_speeds = ["Normal", "Extended", "Fast", "Blitz"]
        if speed not in game_speeds:
            return await ctx.send(
                _(
                    "Invalid game speed. Use `{prefix}help ww` to get help on this"
                    " command."
                ).format(prefix=ctx.prefix)
            )
        minimum_players = {
            "Classic": 5,
            "Imbalanced": 5,
            "Huntergame": 8,
            "Villagergame": 5,
            "Valentines": 8,
        }
        if not min_players:
            default_min_players = (
                5  # Get default of Classic mode if unexpected value happened
            )
            min_players = minimum_players.get(mode, default_min_players)
        self.games[ctx.channel.id] = "forming"
        additional_text = _(
            "Use `{prefix}help ww` to get help on werewolf commands. Use `{prefix}ww"
            " roles` to view descriptions of game roles and their goals to win. Use"
            " `{prefix}ww modes` and `{prefix}ww speeds` to see info about available"
            " game modes and speeds. Use `{prefix}ww updates` to read the new updates."
        ).format(prefix=ctx.prefix)
        mode_emojis = {"Huntergame": ":gun:", "Valentines": ":two_hearts:"}
        mode_emoji = mode_emojis.get(mode, "")
        if ctx.channel.id == self.bot.config.official_tournament_channel_id:
            # TODO: Determine threshold players when wolves can kill 2 villagers per night in mass-games
            id_ = await self.bot.start_joins()
            url = f"https://join.idlerpg.xyz/{id_}"
            text = _(
                "**{author} started a mass-game of Werewolf!**\n**{mode}** mode on"
                " **{speed}** speed. Go to {url} to join in the next 10 minutes."
                " **Minimum of {min_players} players are required.**"
            )
            await ctx.send(
                embed=discord.Embed(
                    title=_("Werewolf Mass-game!"),
                    description=text.format(
                        author=ctx.author.mention,
                        mode=mode_emoji + mode,
                        speed=speed,
                        url=url,
                        min_players=min_players,
                    ),
                    url=url,
                    colour=self.bot.config.primary_colour,
                )
                .set_author(
                    name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
                )
                .add_field(name=_("New to Werewolf?"), value=additional_text)
            )
            await asyncio.sleep(60 * 10)
            players = await self.bot.get_joins(id_)
        else:
            title = _("Werewolf game!")
            text = _(
                "**{author} started a game of Werewolf!**\n**{mode}** mode on"
                " **{speed}** speed. React with :wolf: to join the game! **Minimum of"
                " {min_players} players are required. Starting in 30 seconds.\n{num}"
                " joined**"
            )
            players = [ctx.author]
            msg = await ctx.send(
                embed=discord.Embed(
                    title=title,
                    description=text.format(
                        author=ctx.author.mention,
                        mode=mode_emoji + mode,
                        speed=speed,
                        min_players=min_players,
                        num=len(players),
                    ),
                    colour=self.bot.config.primary_colour,
                )
                .set_author(
                    name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
                )
                .add_field(name=_("New to Werewolf?"), value=additional_text)
            )
            await msg.add_reaction("\U0001f43a")

            def check(reaction, user):
                return (
                    user not in players
                    and reaction.message.id == msg.id
                    and reaction.emoji == "\U0001f43a"
                    and not user.bot
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", check=check, timeout=30
                    )
                except asyncio.TimeoutError:
                    break
                players.append(user)
                await msg.edit(
                    embed=discord.Embed(
                        title=title,
                        description=text.format(
                            author=ctx.author.mention,
                            mode=mode_emoji + mode,
                            speed=speed,
                            min_players=min_players,
                            num=len(players),
                        ),
                        colour=self.bot.config.primary_colour,
                    )
                    .set_author(
                        name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
                    )
                    .add_field(name=_("New to Werewolf?"), value=additional_text)
                )

            # Check for not included participants
            try:
                msg = await ctx.channel.fetch_message(msg.id)
                for reaction in msg.reactions:
                    if reaction.emoji == "\U0001f43a":
                        async for user in reaction.users():
                            if user != ctx.me and user not in players:
                                players.append(user)
                        break
            except discord.errors.NotFound:
                del self.games[ctx.channel.id]
                await ctx.send(
                    _("An error happened during the Werewolf. Please try again!")
                )
                return

        if len(players) < min_players:
            del self.games[ctx.channel.id]
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(
                _(
                    "Not enough players joined... We didn't reach the minimum"
                    " {min_players} players. 🙁"
                ).format(min_players=min_players)
            )

        players = random.shuffle(players)
        try:
            game = Game(ctx, players, mode, speed)
            self.games[ctx.channel.id] = game
            await game.run()
        except Exception as e:
            await ctx.send(
                _("An error happened during the Werewolf. Please try again!")
            )
            del self.games[ctx.channel.id]
            raise e
        try:
            del self.games[ctx.channel.id]
        except KeyError:  # got stuck in between
            pass

    @werewolf.command(brief=_("See available werewolf game modes"))
    @locale_doc
    async def modes(self, ctx):
        _("""Used to see the list of available werewolf game modes.""")
        return await ctx.send(
            embed=discord.Embed(
                title=_("Werewolf Game Modes"),
                description=_(
                    """\
**Game modes:** `Classic` (default), `Imbalanced`, `Huntergame`, `Villagergame`, `Valentines`.
`Classic`: Play the classic werewolf game. (default)
`Imbalanced`: Some roles that are only available in larger games have chances to join even in smaller games. (The size of the game being referred here is about the number of players, i.e. 5-player game is small)
`Huntergame`: Only Hunters and Werewolves are available.
`Villagergame`: No special roles, only Villagers and Werewolves are available.
`Valentines`: (Experimental) There are multiple lovers or couples randomly chosen at the start of the game. A chain of lovers might exist upon the Amor's arrows. If the remaining players are in a single chain of lovers, they all win."""
                ),
                colour=self.bot.config.primary_colour,
            ).set_author(
                name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
            )
        )

    @werewolf.command(brief=_("See available werewolf game speeds"))
    @locale_doc
    async def speeds(self, ctx):
        _("""Used to see the list of available werewolf game speeds.""")
        return await ctx.send(
            embed=discord.Embed(
                title=_("Werewolf Game Speeds"),
                description=_(
                    """\
**Game speeds** (in seconds): `Normal`: 60 (default), `Extended`: 90, `Fast`: 45, `Blitz`: 30
`Normal`: All major action timers are limited to 60 seconds and number of days to play is unlimited.
`Extended`: All major action timers are limited to 90 seconds and number of days to play is unlimited.
`Fast`: All major action timers are limited to 45 seconds and number of days to play is dependent on the number of players plus 3 days. This means not killing anyone every night or every election will likely end the game with no winners.
`Blitz`: Warning: This is a faster game speed suitable for experienced players. All action timers are limited to 30 seconds and number of days to play is dependent on the number of players plus 3 days. This means not killing anyone every night or every election will likely end the game with no winners."""
                ),
                colour=self.bot.config.primary_colour,
            ).set_author(
                name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
            )
        )

    @werewolf.command(brief=_("Check your werewolf role"))
    @locale_doc
    async def myrole(self, ctx):
        _(
            """Check your role in the Werewolf game and have the bot DM it to you.

            You must be part of the ongoing game to get your role."""
        )
        game = self.games.get(ctx.channel.id)
        if not game:
            return await ctx.send(
                _("There is no werewolf game in this channel! {author}").format(
                    author=ctx.author.mention
                )
            )
        if game == "forming":
            return await ctx.send(
                _("The game has yet to be started {author}.").format(
                    author=ctx.author.mention
                )
            )
        if ctx.author not in [player.user for player in game.players]:
            return await ctx.send(
                _("You're not in the game {author}.").format(author=ctx.author.mention)
            )
        else:
            player = discord.utils.get(game.players, user=ctx.author)
            if player is None:
                return await ctx.send(
                    _(
                        "You asked for your role in {channel} but your info couldn't be"
                        " found."
                    ).format(channel=ctx.channel.mention)
                )
            else:
                try:
                    if player.role != player.initial_roles[0]:
                        initial_role_info = _(
                            " A **{initial_roles}** initially"
                        ).format(
                            initial_roles=", ".join(
                                [
                                    game.get_role_name(initial_role)
                                    for initial_role in player.initial_roles
                                ]
                            )
                        )
                    else:
                        initial_role_info = ""
                    await ctx.author.send(
                        _(
                            "Checking your role in {ww_channel}... You are a"
                            " **{role_name}**!{initial_role_info}\n\n{description}"
                        ).format(
                            ww_channel=ctx.channel.mention,
                            role_name=player.role_name,
                            initial_role_info=initial_role_info,
                            description=ROLE_DESC[player.role],
                        )
                    )
                    return await ctx.send(
                        _("I sent a DM containing your role info, {author}.").format(
                            author=ctx.author.mention
                        )
                    )
                except discord.Forbidden:
                    return await ctx.send(
                        _("I couldn't send a DM to you {author}.").format(
                            author=ctx.author.mention
                        )
                    )

    @werewolf.command(brief=_("View descriptions of game roles"))
    @locale_doc
    async def roles(self, ctx, *, role=None):
        _(
            """View the descriptions of roles in the Werewolf game.
            `{prefix}roles` to see all roles.
            `{prefix}roles <role name here>` to view info about a role.
            """
        )
        role_groups = [
            {
                "side": _("The Werewolves"),
                "members": "Werewolf, White Wolf, Big Bad Wolf",
                "goal": _("Must eliminate all other villagers"),
            },
            {
                "side": _("The Villagers"),
                "members": (
                    "Villager, Pure Soul, Seer, Witch, Hunter, Healer, Amor, Knight,"
                    " Sister, Brother, The Old, Fox, Judge"
                ),
                "goal": _("Must find and eliminate the werewolves"),
            },
            {
                "side": _("The Ambiguous"),
                "members": "Thief, Wild Child, Maid, Wolfhound",
                "goal": _("Make their side win"),
            },
            {
                "side": _("The Loners"),
                "members": (
                    f"White Wolf - {_('Be the sole survivor')}, Flutist -"
                    f" {_('Must enchant every living inhabitants')}"
                ),
                "goal": _("Must complete their own objective"),
            },
        ]

        if role is None:
            em = discord.Embed(
                title=_("Werewolf Roles"),
                description=_(
                    "Roles are grouped into \n1. the Werewolves,\n2. the Villagers,\n3."
                    " the Ambiguous, and\n4. the Loners.\n**The available roles are:**"
                ),
                url="https://wiki.idlerpg.xyz/index.php?title=Werewolf",
                colour=self.bot.config.primary_colour,
            ).set_author(
                name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
            )
            tip = _(
                "Use `{prefix}ww roles <role>` to view the description on a specific"
                " role."
            ).format(prefix=ctx.prefix)
            embeds = [
                em.copy().add_field(
                    name=f"{group['side']} - {_('Goal')}: {group['goal']}",
                    value=group["members"].replace(", ", "\n") + f"\n\n**Tip:** {tip}",
                    inline=True,
                )
                for group in role_groups
            ]
            return await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

        search_role = role.upper().replace(" ", "_")
        try:
            ROLES[search_role]
        except KeyError:
            return await ctx.send(
                _("{role}? I couldn't find that role.").format(role=role.title())
            )
        role_groups.reverse()
        return await ctx.send(
            embed=discord.Embed(
                title=search_role.title().replace("_", " "),
                description=ROLE_DESC[ROLES[search_role]],
                colour=self.bot.config.primary_colour,
            )
            .add_field(
                name=_("Side:"),
                value=", ".join(
                    [
                        group["side"]
                        for group in role_groups
                        if group["members"].find(role.title()) != -1
                    ]
                ),
                inline=True,
            )
            .add_field(
                name=_("Goal:"),
                value=", ".join(
                    [
                        group["goal"]
                        for group in role_groups
                        if group["members"].find(role.title()) != -1
                    ]
                ),
                inline=True,
            )
            .set_author(
                name=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64)
            )
        )

    @werewolf.command(brief=_("Read the updates for Werewolf game."))
    @locale_doc
    async def updates(self, ctx):
        _("""Read the updates for Werewolf game.""")
        updates = _(
            """\
**Bug Fixes:**
1. Fix double deaths when Hunter kills the target of Witch or White Wolf. A bug showing 2 death messages for Witch-killed or White Wolf-killed player after it has been killed by the Hunter has been fixed. Second death will not occur anymore.

**Enhancements and Changes:**
1. Revised minor details on description of Fox, Big Bad Wolf, and Healer roles.
2. Changed `role` command to `ww myrole` subcommand. (It's the command that direct messages the player about their current role in a game.)
3. Made few adjustments to prevent more than one game instance in a channel where more than one users attempted to start a werewolf game at the same time.
4. Now users can start a new Werewolf game after failure of getting the joining message for reasons such as accidental deletion of said message.
5. The players are now being shuffled before the start of the game.
6. Thief choosing of new role is now optional, but if given with 2 Werewolf roles as choices, Thief should become a Werewolf. Thief will win with Villagers' side if Thief's role was retained.
7. Improved proper numbering of werewolves' possible victims.
8. Now mentions the users in choices of players selection in dm's. This is to work around users who change their name mid-game which is different from the cached name.
9. Now messages you when you timed out while choosing a player.
10. Changed the default 90-seconds discussion time in classic mode. It's now defaulted to 60 seconds as "Normal" speed.
11. AFK check has been reworked for lesser time consumption.
12. Now shows all the player's previous roles upon player's death or when game's over. Previously, only the first role is being shown as initial role. (Works on Thief and Maid)

**Additions:**
1. Sheriff has been added to the game! The game will randomly choose a player at the start to become the Sheriff that has double count of vote. An eliminated Sheriff should choose a new Sheriff as his successor.
2. Added subcommand `ww roles` that shows the list of available roles. `ww roles <role_name>` can be used to view the description or abilities of the role and see the goal and side it belongs.
3. Added new game modes and speeds: (use `ww modes` and `ww speeds` commands for detailed info)
  - Added Game modes: `Imbalanced`, `Huntergame`, `Villagergame`, `Valentines`.
  - Added Game speeds: `Normal` (60 seconds), `Extended` (90 seconds), `Fast` (45 seconds).
4. Now open for massive werewolf games in experimental phase.
5. The welcome message now displays the number of players and mentions them (several messages might be shown for too many players suitable with mass werewolf game, aka: paginated)
6. Major messages that need pagination of players like during daily elections or when the game is over have been implemented in preparation for mass werewolf games.
7. Now displays the number of in-game days and the limit of days to play if it's on Fast or Blitz speed.
8. Now mentions the werewolf game channel in DM's as shortcut link to easily go back and forth with the channels.
9. Werewolves will now see who the other werewolves are and their count during the victim selection in DM's.
10. Now shows the roles of revealed players next to their names during players selection in dm's. Pure soul's role will be shown to all players with ability to choose a player in DM's. Seer will now be shown with the roles previously revealed to them.
11. Werewolves will now see the current number of votes for nominated victims before they vote.
12. Now has detection for sneaky lynching nomination.
13. Now has workaround on non-players or dead players influencing the game by nuisance voting.
14. Maid will now be asked whether to swap role with the player about to be lynched and not after the player's death. The game will announce the Maid's name that took the player's role. The new role of the Maid will not be revealed. The role of the eliminated player will be shown as Maid since they were exchanged.
15. The former Maid will have her role be called the following night if needed as if it's the first night (e.g: Announced as new Pure Soul, choose from 2 extra roles as Thief (if Thief didn't take other role), choose an Idol if she took Wild Child, etc.)
16. The former Maid can choose another pair of lovers if she took Amor's role hence a possibility of 2 sets of lovers. A player could get caught between 2 lovers in the game.
17. Judge will now receive a message if he successfully triggered a second election.
18. White Wolf update: Removed choosing werewolf phase if there's no other werewolf left.
19. Big Bad Wolf update: Removed choosing villagers victim phase if there's no other possible villagers left to kill.
20. Added 8 players as default minimum number of players for Huntergame and Valentines game modes.
21. Added option to customize minimum number of players.
22. Added more details on description of The Old.
23. Added `ww updates` command to see all of these updates."""
        )
        p = commands.Paginator(prefix="", suffix="")
        for i in chunks(updates, 1900):
            p.add_line(i)
        await self.bot.paginator.Paginator(
            title=_("Werewolf Updates"),
            entries=p.pages,
            length=1,
            colour=self.bot.config.primary_colour,
        ).paginate(ctx)


def setup(bot):
    bot.add_cog(Werewolf(bot))
