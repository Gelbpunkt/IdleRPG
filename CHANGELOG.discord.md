**v4.2.2**
<https://git.travitia.xyz/Kenvyra/IdleRPG/compare/v4.2.1...v4.2.2>

> 2019-11-17

**Additions**

- Add a tax for shop offers
- Market has no price limit anymore (earlier 1000 - value) to enable trading expensive items
- Shop items time out after 2 weeks
- Timed out offers in shop will be moved to inventories again with `$clearshop` (Admin only)

**Fixes**

- Fix wikipedia and error properly if page content unparseable
- Fix postgres syntax errors
- Fix <https://git.travitia.xyz/Kenvyra/IdleRPG/issues/396>
- Fix `$resetitem`
- Fix an unneeded error on startup
- Fix `$unequip`
- Reset guild adventure cooldown is insufficient people join

**Shop Log**

- Log shop sales
- Soon, a market dashboard will follow

**Raid Battles**

- Redesigned the raidbattle system

**Updates**

- Update tr_TR
- Update repo url
- vn_VN update

**Merge Requests**

- Merge branch 'guild-cooldown' into 'v4'
- Merge branch 'battles-fix' into 'v4'
- Merge branch 'raidbattle-redesign' into 'v4'
- Merge branch 'guild-info' into 'v4'
- Merge branch 'v4' into 'v4'
