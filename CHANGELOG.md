<a name="v4.3.1"></a>

## [v4.3.1](https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.3.0...v4.3.1)

> 2020-01-02

### Additions

- New familyevents: 4/22 for money gain up to $5000, 3/22 for up to 1/64 of total money loss, 2/22 crate gain
- add reset_alliance_cooldown(), change the order of some attacking code
- add raid tournaments
- Add $adminitem

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
