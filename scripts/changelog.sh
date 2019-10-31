#!/usr/bin/env bash
# add git-chglog to path before
git-chglog -o CHANGELOG.md git-chglog --next-tag $1
