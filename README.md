# PCRS Minecraft Club scripts (Luanti)

Tools for running the club server. They work on this machine and on the
school server; only the paths you pass in change.

## Log-watching stats (Python)

Read the server log (`debug.txt`) and build stats.

| Script | What it tracks |
| --- | --- |
| `eco_champion_farming.py` | Eco score: mining, building, farming (newest) |
| `eco_champion.py` / `eco_minetest.py` | Eco score without farming (identical) |
| `eco_minetest_v1.py` | First version: stone/sand dug |
| `back_eco_champion_farm.py` | Backup of an earlier farming version |
| `deathCount.py` / `g_deathCount.py` | Deaths and causes, survival leaderboard |

Which log file is used (first match wins):

1. A path given on the command line: `python3 deathCount.py ~/.minetest/debug.txt`
2. The `LUANTI_LOG` environment variable: `export LUANTI_LOG=~/.minetest/debug.txt`
3. `../debug.txt`: the Luanti folder this one sits in (run-in-place installs)

Stats (`minetest_stats.json`, `minetest_deaths.json`) are saved **next to the
log**, not here, so student data never ends up in git.

## Scavenger Hunt stats

`hunt_stats.py` reports on the `scavenger_hunt` mod: leaderboard, how far
each student explored, where the unfound stars are, recent finds, and where
the **collected** stars are now: in each player's inventory and in chests,
locked chests and bones. It only reads data, so it's safe while the server
is running.

```bash
python3 hunt_stats.py ~/luanti/worlds/test_pcrs2026             # all time
python3 hunt_stats.py ~/luanti/worlds/test_pcrs2026 --today     # this club day
```

Other options: `--since 2026-11-01`, `--spawn X,Z` (if spawn isn't near 0,0),
`--recent N`, `--log FILE`, `--teams FILE`, `--no-map` (skip the chest search).

### Teams (kept out of git)

Put the real team list in **`teams.txt` in the Luanti folder** (one level up
from this folder), so student names never end up in the repo. Format: see
`teams_example.txt`. `hunt_stats.py` finds it automatically; or set
`LUANTI_TEAMS=/path/to/teams.txt`, or pass `--teams`. (`.gitignore` also
blocks any `teams*.txt` here, just in case.)

Team "held now" = stars carried by members + stars in **chests placed by a
member** (teammates can share a chest; nobody has to lock it). The
`scavenger_hunt` mod records who placed each chest, and shows it when you
point at the chest. Locked chests count for their owner. Chests placed before
the mod was installed have no placer, so they count for no team.

**Stars in bones don't count.** When a player dies, their stars go into a
bones box; they count again once the player digs the bones and has the stars
back in their inventory. The report lists bones holding stars separately.

Searching chests needs a zstd decompressor. It uses the first one available:
Python 3.14+'s built-in zstd, the `zstandard` package
(`sudo apt install python3-zstandard`), or the system's `libzstd` (always
present on Debian/Ubuntu). If none work, the report shows a warning and `-`
for chests. Use `--no-map` to skip chests entirely.

## Scavenger Hunt remote control

`hunt_control.py` runs the hunt on a **running** server from a terminal (e.g.
over ssh while you walk around helping students). The mod picks up each
request within ~2 seconds and replies.

```bash
export LUANTI_WORLD=~/luanti/worlds/test_pcrs2026   # once per ssh session
python3 hunt_control.py status                     # counts + who's online
python3 hunt_control.py players                    # positions, scores, teams
python3 hunt_control.py scatter 30 250             # 30 stars within 250 of spawn
python3 hunt_control.py scatter 10 250 --mode cave # ...in caves (or --mode water)
python3 hunt_control.py scatter 3 30 --near abel   # a few right around a student
python3 hunt_control.py scatter 20 100 --at 300 -250
python3 hunt_control.py say "New stars hidden near spawn!"
python3 hunt_control.py clear                      # remove all hidden stars (asks)
python3 hunt_control.py reset                      # all scores to 0 (asks)
```

Requests go through the `hunt_control` folder inside the world, so you need
write access to the world folder (the account that runs the server).

## Database scripts (bash)

Read or change `players.sqlite` in a world. Pass the world folder, or run from
inside it.

| Script | What it does |
| --- | --- |
| `sqTest.sh` | **Changes inventories:** gives every player a mapping kit, bed and diamond pick |
| `PCRS_countItems.sh` | Scores ore totals per team (school team list) |
| `home_countItems.sh` | Same, with test players at home |
| `countItems.sh` | Oldest version: totals break (coal count never starts at 0) |

```bash
./PCRS_countItems.sh ~/luanti/worlds/test_pcrs2026
```

**Stop the server before running `sqTest.sh`.** The server keeps inventories
in memory and overwrites the database when it saves, so changes made while it
is running can be lost.

Requires `sqlite3` (`sudo apt install sqlite3`).

## Known issues

- Items held as a single (count 1) are not counted by the `countItems` scripts.
- Planting detection in `eco_champion_farming.py` never fires: Luanti does not
  log a "planted" line.
