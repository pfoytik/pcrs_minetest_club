#!/bin/bash

# Usage: sqTest.sh [world folder]   (default: current folder)
WORLD="${1:-.}"
DB="$WORLD/players.sqlite"
if [ ! -f "$DB" ]; then
	echo "No players.sqlite in $WORLD - pass the world folder, e.g. $0 ~/luanti/worlds/test_pcrs2026"
	exit 1
fi
cmd="sqlite3 $DB"
cmd1="select name from player;"
result=$($cmd "$cmd1")
echo $result

while read -r word; do
	w="$word"
	echo "Current word is $w"
	echo "way to go $w"

	# SQLite query
	update_query="UPDATE player_inventory_items SET item='map:mapping_kit' WHERE player='$w' AND inv_id=0 AND slot_id=30;"
	$cmd "$update_query"

	update_query="UPDATE player_inventory_items SET item='beds:bed_bottom' WHERE player='$w' AND inv_id=0 AND slot_id=31;"
	$cmd "$update_query"

	update_query="UPDATE player_inventory_items set item='default:pick_diamond' WHERE player='$w' AND inv_id=0 and slot_id=25;"
	$cmd "$update_query"

done <<< "$result"

