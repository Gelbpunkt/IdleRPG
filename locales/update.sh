#!/bin/bash

xgettext \
	--files-from POTFILES.in \
	--from-code utf-8 \
	--add-comments \
	--directory ../ \
	--output messages.pot

for locale in */; do
	file="$locale/LC_MESSAGES/idlerpg"

	msgmerge \
		--update \
		--no-fuzzy-matching \
		--backup off \
		"$file.po" \
		messages.pot

	msgfmt "$file.po" --output-file "$file.mo"; done
