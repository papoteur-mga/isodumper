#!/bin/sh

set -e

if test "$1" = "-h" -o "$1" = "--help"; then
	echo "Use: $0 [<language>]"
	echo "Run without arguments to update all translation files."
	exit 0
fi

cd "$(readlink -f "$(dirname "$0")/..")"

#VERSION=(0.1)
DOMAIN=(isodumper)
intltool-extract --type=gettext/glade ../share/isodumper/isodumper.glade

SOURCE_FILES=$(/bin/mktemp --tmpdir $DOMAIN-po-update-XXXXXX)
find "lib" -name '*.py' >"$SOURCE_FILES"
find "share/isodumper" -name '*.glade.h' >"$SOURCE_FILES"

POT_DIR="$PWD/po"
test -d "$POT_DIR"

POT_FILE="$POT_DIR/$DOMAIN.pot"

/usr/bin/xgettext \
	--package-name "$DOMAIN" \
	--package-version "$VERSION" \
	--default-domain="$L_NAME" \
	--language=Python --from-code=UTF-8 --files-from="$SOURCE_FILES" \
	--no-escape --add-location --sort-by-file \
	--add-comments=I18N \
	--output="$POT_FILE"

/bin/sed --in-place --expression="s/charset=CHARSET/charset=UTF-8/" "$POT_FILE"

rm -f ../share/isodumper/isodumper.glade.h

update_po() {
	local LL_CC="$1"
	local PO_FILE="$POT_DIR/$LL_CC.po"

        echo "Update $(basename "$PO_FILE"):"
	/usr/bin/msgmerge \
		--update --no-fuzzy-matching \
		--no-escape --add-location --sort-by-file \
		--lang="$LL_CC" \
		"$PO_FILE" "$POT_FILE"

	# /bin/sed --in-place --expression="s/Language: \\\\n/Language: $L_NAME\\\\n/" "$PO_FILE"
}

if test "$1"; then
	update_po "$1"
else
	for l in $(ls -1 "$POT_DIR"/??.po); do
		l="$(basename "$l")"
		update_po "${l%.po}"
	done
fi
