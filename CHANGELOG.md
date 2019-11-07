<a name="v4.2.0"></a>
## [v4.2.0](https://git.travitia.xyz/Adrian/IdleRPG/compare/v4.1.10...v4.2.0)

> 2019-11-07

### Fixes

* Fix dict -> set for caches
* Fix beta.sh script
* Fix profile issues and replace "None" with useful info
* Fix [#384](https://git.travitia.xyz/Adrian/IdleRPG/issues/384)

### Guild

* Guild Bank Upgrade now has a db entry

## Items
* Items have signatures now
* Admins can use `$adminsign` every 3 days to sign an item

### New

* Implemented `$adminsign`
* Increase guild bank limit for donators
* Add `$donatordaily`
* Decrease adventure time for donators
* More daily money for silver donators
* New script to show columns in schema
* Add global 2s cooldown for donators

### Pets

* pet fix / more info for class checks fail
* Pet purgatory fix

### Trading

* Prevent selling donator modified items

### Removed

* Removed unneeded file

### Revert

* revert leftover halloween stuff

### Marriage

* show gained lovescore on lovely night

### Merge Requests

* Merge branch 'patch-1' into 'v4'
* Merge branch 'pets' into 'v4'
* Merge branch 'patch-1' into 'v4'
* Merge branch 'pet-fix' into 'v4'

<a name="v4.1.10"></a>
## [v4.1.10](https://git.travitia.xyz/Adrian/IdleRPG/compare/v4.1.9...v4.1.10)

> 2019-10-31

### GitLab

* Add GitLab Merge Request Template
* Add GitLab Issue Templates

### New Commands

* Add alterraid command that updates Zerekiel's HP in case of typo (also testing gitlab)
* Adds an admin exclusive cooldown overwriting command

### Fixes

* Fix permissions on changelog.sh and alter the script a bit
* Fix flake8 issues
* Fix a bug with raid damage to player and edit Bandit raid to Fox' needs
* Fix formatting in guild adventure message

### Merge Requests

* Merge branch 'raid-patch' into 'v4'
* Merge branch 'raid-addon' into 'v4'
* Merge branch 'v4' into 'v4'
