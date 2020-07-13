<a name="v4.8.0"></a>

## [v4.8.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.7.0...v4.8.0)

> 2020-07-13

### Changes

- 24h cooldown on alliance attacks
- Added more music error handling
- Enhanced HTML generation
- Fixed cache wiping, many thanks to Danny, ImRock and Luke, you guys *rock*
- Fixed Travis
- Clarified `$color` and `$loop`
- Cooldown to crate opening
- Many database optimizations using indexes
- A minor exploit fix
- Lots of translation updates, thanks guys!
- Fixed `$alliance attack` logic
- `$merchall` is available again
- Automatic raid outcome announcements
- Fix typos for help info of `$pet play` and `$pet cuddle`
- Fix insanity wave for Guilt
- Fix command access logic for game master and owner commands
- Prohibit rgb values over 255

### Additions

- Added `$markethistory` to search past market sales
- Added options to `$draw` to play a draw game with someone for money
- Allow opening up to 100 crates at once using `$open rarity amount`
- New command `$offercrate` to offer crates safely
- New profile data caching in Redis to increase performance

### Merge Requests

- Merge branch 'patch-14' into 'redis-cache'
- Merge branch 'children-no-delete' into 'redis-cache'
- Merge branch 'patch-13' into 'redis-cache'
- Merge branch 'patch-12' into 'redis-cache'
- Merge branch 'patch-2' into 'redis-cache'
- Merge branch 'no-cascade' into 'redis-cache'
- Merge branch 'fix-gm-help' into 'v4'
- Merge branch 'patch-6' into 'v4'
- Merge branch 'patch-10' into 'v4'
- Merge branch 'patch-9' into 'v4'
- Merge branch 'patch-5' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'generate-stats-patch' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'okapi-rewrite' into 'v4'
- Merge branch 'patch-2' into 'v4'


<a name="v4.7.0"></a>

## [v4.7.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.6.0...v4.7.0)

> 2020-06-02

### Changes

- Added a mention about `$locale set` in `$locale`
- Added a new colour parser for `$colour`. Works with `color-name`, `#RRGGBB`, `rgb(r,g,b)` or even `rgba(r,g,b,a)` (this means transparency now works). All current colours had to be reset as the data structure significantly changed.
- Added better check-handling for music, modernize error handling itself
- Switched from Andesite to Lavalink
- Added option to choose exact paginator page via reaction control
- After all the months, we're now logging events
- Added alias `$bal` and `$balance` to `$economy`
- Added a new minigame: Werewolf (aka Mafia): Use `$werewolf` to play (there are modes, check the help on it)
- Added a new game: Chess: Use `$chess match` to play either against AI or other users. `$chess register` allows you to play ELO rated. Leaderboard is `$chess elo`.
- Added a new command `$guild distribute` that distributes money to multiple members
- Added a warning/price information when upgrading raidstats
- Added a removeall command that removes all of your items from the market and adds them back to your inventory
- Aww is confirmed cuter than Owwwwww, so we changed the `$marry` text
- Banned people who are bot banned from reacting
- Calculate luck boosters into `$adventures`
- Catch global cooldown exception, remove captcha code. You now get a different error message if you are being rate-limited
- Condensed `$evall` command output, add a new loot item (toilet paper)
- Deprecated `$dungeon` alias
- Donator check logic was redone and now caches
- We are now using gateway intents to reduce the load on the bot significantly and are caching a lot of member-related stuff
- We are also using orjson now to speed up serializing and deserializing of gateway messages
- `$helpme` requests can now be edited, deleted and much more. Check the help on it
- Music was redone internally, featuring the fact that it works now (!), Spotify song querying, `$loop` now repeating the queue, `$chooseplay` to choose one of the search results and much more. YouTube links won't always work anymore. Oh and the `$lyrics` are more exact now
- All command descriptions were significantly extended and are now much easier to understand
- The `$help` command was completely redone to allow ease of use
- We switched from raven to sentry-sdk
- Added `$streak` to check your daily streak
- `$hungergames` now works with a lot more players than before
- Using a hardcoded ARM cpu name table now
- `id_ID_rude` was the superior translation and replaced `id_ID`
- Added a Ikhdosa Raid timeout message
- Implemented graceful shutdown
- Inform players about the guild channel command when creating a guild
- Initial ugly version of `$clusters`
- Two handed items now multiply times 2, not 1.5
- Make less than 1.00 luck more user friendly
- Move activebattles to embeds
- New Partner: chr1s the boss
- Overwrite permissions for the member role in raids instead of default role
- Lots of performance improvements in the launcher
- Prohibit using backticks in character names
- Prohibit users from giving money and crates to the bot
- Prohibit changing one handed to two handed in `$weapontype`
- Publicly log when a magic crate opens a 41+ stat item
- Redesign Guilt's raid and adjusted her boundaries
- We are using true random number generation everywhere now
- Rename Admins to Game Masters
- Support Team now has donator perks
- Update `$pet hunt` to use new midnight cooldown
- Upgrade to Redis 6.0.4, PostgreSQL 13

### Fixes

- Prevented firing on_ready multiple times
- Our CI script got fixed
- Tons of fixes to IPC which caused processes to disconnect earlier
- Fixed enum value displaying in donator error message
- Fixed beta script database creation with dollar signs
- Fixed Ikhdosa raid
- Fixed typos in Game Master command names
- Fixed autosignup for raids
- Fixed issue with class decorator order
- Fixed `$serverinfo`
- Fixed `$makebackground`
- Fixed familyevent namechange cooldown
- Remove old script file
- Support Team should have donator perks

<a name="v4.6.0"></a>

## [v4.6.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.5.1...v4.6.0)

> 2020-03-31

### Additions

- Add $roulette and $roulette table. They use a French roulette board with only one zero and a full list of bidding options is in the help.
  We do currently not support multiple bids.
- Add redis version and CPU temperature to \$stats
- We have added two new gods (Tet and Eden) plus raids and removed 3 old gods who left the server. Their boundaries are 0.8-1.2 and 0.5-1.5.
- The "You are not a donator" error now shows which donator rank is required for the command.
- We have added https://join.travitia.xyz, a website for joining huge amounts of players outside of Discord to reduce spam.
  This is used for tournaments and hungergames in the Support Server and guild adventures.
- We have added \$adminauction to auction items for Bot Administrators.
- We moved to a new custom proxy solution and have added support for it.
- Many converters for money and users have better error handling instead of "You used a bad argument!" now.
- \$bags shows the trick-or-treat-bags.
- We are now logging every single transaction possible.

### Changes

- Adjust halloween and easter
- We have moved to aiohttp 4.0a1 and are using cchardet and aiodns to speed it up even more.
- We have moved to Alpine Linux 3.12 alpha to use gcc 9.3
- We have moved to Python 3.9a5
- The Dockerfile now installs the dependency libraries based on the current architecture.
  Supported are x86_64 and aarch64
- We have balanced out the easter event
- Be non-NSFW in marriage.py and adapted chance of money loss.
- Handle wavelink connection issues differently
- Rework active battles
- Set upgrade and merge maximum for two-handed items to 62
- Speed up implementation of \$fancy
- Take BlackJack back to 1000
- Update rules, add error handler for some music checks
- Update stats less often

### Fixes

- Add Nitro booster and Administrator as basic donator ranks
- The default timezone is set to prevent DeprecationWarnings
- uvloop is now compiled with Python 3.9 support to prevent DeprecationWarnings
- Default DM messages to English
- Escape username markdown in toplists (this is WIP)
- Fix raid bids logging, no longer log zero gambles
- Fix ikhdosa raid
- Fix issue with bot.wavelink being undefined
- Fix easter guild badge
- Fix factorials in \$math
- Update makebackground to use JSON content type (fix)
- Update imgur command to explicitely send JSON data
- Update adminwipeperks command to current meta

### Merge Requests

- Merge branch 'logging' into 'v4'
- Merge branch 'markdown' into 'v4'
- Merge branch 'typos' into 'v4'
- Merge branch 'battles' into 'v4'
- Merge branch 'feature/extend_french_translation' into 'v4'
- Merge branch 'fix-formatting' into 'v4'
- Merge branch 'feature/extend_french_translation' into 'v4'
- Merge branch 'active-battle' into 'v4'
- Merge branch 'logging' into 'v4'
- Merge branch 'english-in-dm' into 'v4'
- Merge branch 'easter' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'awipeperks' into 'v4'

<a name="v4.5.1"></a>

## [v4.5.1](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.5.0...v4.5.1)

> 2020-03-13

### Changes

- A couple QoL changes
- Change CHamburr boundaries
- Disable merchall
- Blackjack bid increase to \$10,000
- Make gain/loose from familyevent both up to 1/64
- Set Bot.max_messages to 10000
- Several improvements to \$dice code
- Significant improvements to donator checks resulting in up to 10x faster donator command execution
- tournament text consistency
- Use more accurate CPU detection
- use Redis 6 for significant performance increases on multi-threaded configs

### Additions

- add valentines commands
- Add $aa as alias for $activeadventure
- Add boundaries for Assassin
- Add \$trivia

## Fixes

- Bug with battle
- consistency with active battle text
- Fix equalizers
- Fix visual bug in \$pet hunt command
- fix a bug in adminitem
- fix raids
- fix \$sell
- fix typo
- fix trivia
- fix resetitem
- reset familyevent cooldown when you have no kids or spouse

### Merge Requests

- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-3' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'unfollowing' into 'v4'
- Merge branch 'fixes' into 'v4'
- Merge branch 'v4' into 'fixes'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'valentine' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-10' into 'v4'

<a name="v4.5.0"></a>

## [v4.5.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.4.0...v4.5.0)

> 2020-02-07

### Fixes

- a fix for the translator tool
- Fix maxstat and minstat for merchall with new limits
- Fix startup items
- Fix the top follower order
- Fix locales xgettext issue
- Fix the rules
- fix weapontype
- fix a bug in command sacrifice
- fix equip logic
- fix activeadventure
- fix itemtype and resetitem logic
- fix some equip logic
- fix profile for cases with one item equipped
- fix some equip logic
- fix trader, activebattle
- fix equip formatting
- fix itemreset bug
- fix alterraid
- fix images not loading on previously added pages
- fix a bug with resetting changed type items
- fix alteraid
- include a profile check for every raid: prevents raids from crashing

# Changes

- adapt ingame stat calculations
- Add information on level up to lv12; reset guild and alliance cooldown on ctx confirm deny
- add luck boundaries for god luck
- Change equip logic
- extend occupy cooldown, better information for unable to attack city
- fix weapontype
- Force utf-8 for language fixer
- generate items of other types
- equipping is now based on hands, some types use one hand, any hand or two hands. Two-handed items have a 1.5x higher stat to balance them more with the rest
- make beta.sh retain original ownerships
- Not returning the follower list if the user doesn't follow anyone
- Require sending at least $1 when using $give
- Set $0 defaults for $activebattle, $tournament and $raidtournament
- use python 3.9.0a3

### Merge Requests

- Merge branch 'v4.5' into 'v4'
- Merge branch 'v4' into 'v4.5'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'sac-ex-fix' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'additions' into 'v4'
- Merge branch 'reset-item' into 'v4'
- Merge branch 'zero-defaults' into 'v4'
- Merge branch 'fixes' into 'v4'
- Merge branch 'itemtype-fix' into 'v4'
- Merge branch 'adventure-paginator-fix' into 'v4'
- Merge branch 'tool-fix' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'revert-f504c0fd' into 'v4'
- Merge branch 'patch-8' into 'v4'

<a name="v4.4.0"></a>

## [v4.4.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.3.1...v4.4.0)

> 2020-01-24

### Additions

- Character name as optional argument to `$rename` and `$create`
- Add `$rules` command
- Added adventures 21-30
- Added support for gift codes
- Actually disable the use of god commands
- Added level 30
- Allow demoting non-shared server members
- Better hungergames error handling

### Changes

- Change bandits officers back to bandits
- Renamed many classes, had to reset classes for all users
- XP table was readjusted for better balance
- Updated the `$adventures` images for 1-10 and 21-30. We did not finish 11-20 in time, their time displayed is now 1h too low
- Adventure 1 and 2 have their time taken fixed to be consistent with others
- Getting loot is more likely in high adventures (5% plus 1.5% per adventure level (+3% if Ritualist))
- Disabled god commands. Luck is now generated by the bot and given extra to the top 25 followers weekly
- Grant Translators donator perks
- Make $battle and $raidbattle default to \$0
- paginate \$tree

### Fixes

- Divorce when deleting a user.
- Fix initial classes for new selections
- Fix levelup crates
- Fix guilds
- Fix get_class_grade issue
- Fix 1337 indentions
- Fix 1337 tool
- Fix exploit in weapontype
- Fix typo in \$bet help message
- Fix chance calculation of \$bet
- Fix raids

### Also There

- Language fixer tool

### Merge Requests

- Merge branch 'patch-1' into 'v4'
- Merge branch 'v4' into 'v4'
- Merge branch 'tree' into 'v4'
- Merge branch 'naming' into 'v4'
- Merge branch 'additions' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-4' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'gambit-raid' into 'v4'
- Merge branch 'patch-7' into 'v4'
- Merge branch 'raid-patch' into 'v4'
- Merge branch 'occupy-cd' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'text-fixes' into 'v4'
- Merge branch 'rules' into 'v4'

<a name="v4.3.1"></a>

## [v4.3.1](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.3.0...v4.3.1)

> 2020-01-02

### Additions

- New familyevents: 4/22 for money gain up to \$5000, 3/22 for up to 1/64 of total money loss, 2/22 crate gain
- add reset_alliance_cooldown(), change the order of some attacking code
- add raid tournaments
- Add \$adminitem

### Fixes

- Fix formatting
- Fix no decoder for composite type element issue (https://github.com/MagicStack/asyncpg/issues/360) (this issue affected raids)
- Fix attack check order
- Fix alliance attack target selection
- fix a bug in alliance invite
- fix an exploit
- fix trade security
- fix Asmodeus raid
- fix child rename bug
- prevent bots from joining alliance attacks
- Prevent alliance occupy spam

### QoL

- Show money in merchall confirmation

### Merge Requests

- Merge branch 'patch-7' into 'v4'
- Merge branch 'patch-4' into 'v4'
- Merge branch 'familyevent' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'alliance-fix' into 'v4'
- Merge branch 'alliance-fix' into 'v4'
- Merge branch 'patch-4' into 'v4'
- Merge branch 'multi-patch' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-3' into 'v4'
- Merge branch 'raid-tournaments' into 'v4'
- Merge branch 'trade-security' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'

<a name="v4.3.0"></a>

## [v4.3.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.2.3...v4.3.0)

> 2019-12-17

### New Features

- Alliances and cities (`$alliance`, `$cities`)
- Allow viewing others' XP
- Global event channel
- Cooldowns which last until the next day UTC

### Fixes

- Calculate raidstats properly
- Fix betting cooldown
- Decorator order fixes for god commands
- Error handling is fixed for many cases
- Prevent duplicate guild names
- Quick rework of XP viewing
- Raid autojoin for diamond

### Merge Requests

- Merge branch 'v4' into 'guild-wars'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'guild-wars' into 'guild-wars'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'public-logs' into 'guild-wars'
- Merge branch 'guild-wars' into 'guild-wars'
- Merge branch 'guild-wars' into 'guild-wars'
- Merge branch 'guild-wars' into 'guild-wars'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'v4' into 'v4'
- Merge branch 'bettercd' into 'v4'

<a name="v4.2.3"></a>

## [v4.2.3](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.2.2...v4.2.3)

> 2019-11-30

### Additions

- ability to sacrifice multiple loot at once
- Add Hungarian translation
- add \$chucknorris
- blackjack revisit with splitting and fixes
- Raid auto-join for Ruby Donators, nerf XP from exchanging
- Redesign loot to resemble inventory

### Fixes

- fix a bug that allowed to add multiple of the same item in trades
- Fix hungergames and some god raids
- Fix syntax error
- raidbattle patch
- several formatting issues/clarifications adressed
- Several fixes
- smaller files

### Merge Requests

- Merge branch 'blackjack-revisit' into 'v4'
- Merge branch 'blackjack-patch' into 'v4'
- Merge branch 'fix-mash' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-2' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'sacrifice-multiple' into 'v4'
- Merge branch 'informational' into 'v4'
- Merge branch 'loot-redesign' into 'v4'
- Merge branch 'patch-1' into 'v4'

<a name="v4.2.2"></a>

## [v4.2.2](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.2.1...v4.2.2)

> 2019-11-17

### Additions

- Add a tax for shop offers
- Market has no price limit anymore (earlier 1000 \* value) to enable trading expensive items
- Shop items time out after 2 weeks
- Timed out offers in shop will be moved to inventories again with `$clearshop` (Admin only)

### Fixes

- Fix wikipedia and error properly if page content unparseable
- Fix postgres syntax errors
- Fix [#396](https://git.travitia.xyz/Kenvyra/IdleRPG/issues/396)
- Fix `$resetitem`
- Fix an unneeded error on startup
- Fix `$unequip`
- Reset guild adventure cooldown if insufficient people join

### Shop Log

- Log shop sales
- Soon, a market dashboard will follow

### Raid Battles

- Redesigned the raidbattle system

### Updates

- Update tr_TR
- Update repo url
- vn_VN update

### Merge Requests

- Merge branch 'guild-cooldown' into 'v4'
- Merge branch 'battles-fix' into 'v4'
- Merge branch 'raidbattle-redesign' into 'v4'
- Merge branch 'guild-info' into 'v4'

<a name="v4.2.1"></a>

## [v4.2.1](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.2.0...v4.2.1)

> 2019-11-13

### New Features

- allow exchanging multiple items by tying `$exchange`
- allow seeing guild info by mentioning a user (force guild by using `guild:name`)
- BlackJack will only ask for insurance if needed
- Raid battles will account for your raid stats and classes (`$raidbattle`)

## Changes

- Change git URL
- Exploit fixes

### Fixes

- Fix yesno by working around aiohttp
- Fix logic issue for raidbattle winner
- Fix classes in raidbattles
- Fix raidbattles beginning
- Fix aliases for adminsign
- Fix donator daily

### Code Style

- flake8 fix
- less code duplication
- Refactor inv code

### Locales

- Locales updated

### Admins

- Remove old admins

### Merge Requests

- Merge branch 'patch-1' into 'v4'
- Merge branch 'exc-all' into 'v4'
- Merge branch 'guild-info-user' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'raidbattles' into 'v4'
- Merge branch 'patch-1' into 'v4'

<a name="v4.2.0"></a>

## [v4.2.0](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.1.10...v4.2.0)

> 2019-11-07

### Fixes

- Fix dict -> set for caches
- Fix beta.sh script
- Fix profile issues and replace "None" with useful info
- Fix [#384](https://git.travitia.xyz/Kenvyra/IdleRPG/issues/384)

### Guild

- Guild Bank Upgrade now has a db entry

## Items

- Items have signatures now
- Admins can use `$adminsign` every 3 days to sign an item

### New

- Implemented `$adminsign`
- Increase guild bank limit for donators
- Add `$donatordaily`
- Decrease adventure time for donators
- More daily money for silver donators
- New script to show columns in schema
- Add global 2s cooldown for donators

### Pets

- pet fix / more info for class checks fail
- Pet purgatory fix

### Trading

- Prevent selling donator modified items

### Removed

- Removed unneeded file

### Revert

- revert leftover halloween stuff

### Marriage

- show gained lovescore on lovely night

### Merge Requests

- Merge branch 'patch-1' into 'v4'
- Merge branch 'pets' into 'v4'
- Merge branch 'patch-1' into 'v4'
- Merge branch 'pet-fix' into 'v4'

<a name="v4.1.10"></a>

## [v4.1.10](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.1.9...v4.1.10)

> 2019-10-31

### GitLab

- Add GitLab Merge Request Template
- Add GitLab Issue Templates

### New Commands

- Add alterraid command that updates Zerekiel's HP in case of typo (also testing gitlab)
- Adds an admin exclusive cooldown overwriting command

### Fixes

- Fix permissions on changelog.sh and alter the script a bit
- Fix flake8 issues
- Fix a bug with raid damage to player and edit Bandit raid to Fox' needs
- Fix formatting in guild adventure message

### Merge Requests

- Merge branch 'raid-patch' into 'v4'
- Merge branch 'raid-addon' into 'v4'
- Merge branch 'v4' into 'v4'
