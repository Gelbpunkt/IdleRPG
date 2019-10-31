#!/usr/bin/env bash
# add git-chglog to path before
git-chglog --next-tag $1 -o NEXT_CHANGELOG.md $1
read -p "Done, please now hit enter, modify it and then I will add it to the changelog file"
vim NEXT_CHANGELOG.md
cat <(cat NEXT_CHANGELOG.md) CHANGELOG.md > CHANGELOG.tmp
rm CHANGELOG.md
mv CHANGELOG.tmp CHANGELOG.md
