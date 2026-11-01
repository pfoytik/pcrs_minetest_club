# Scavenger Hunt

Glowing **Hunt Stars** hidden across the world: out in the open, on the
floor of lakes and seas, and in caves. Students collect them for points. Stars run out near spawn, and more appear in land nobody has visited
yet, so the way to score is to explore.

## Turning it on

Copy this folder into the server's `mods` folder, then add this line to the
world's `world.mt` and restart the server:

    load_mod_scavenger_hunt = true

Stars are hidden automatically in **newly generated** land only. In a world
that's already been explored, use `/hunt_scatter` to hide stars there.

## Commands

| Command | Who | What it does |
| --- | --- | --- |
| `/hunt` | everyone | Leaderboard (top 10) and your own count |
| `/hunt_scatter <count> [radius] [land\|water\|cave]` | teachers | Hide stars at random spots around you (default radius 200, on land) |
| `/hunt_status` | teachers | How many are hidden, found, and how many players scored |
| `/hunt_clear yes` | teachers | Remove all hidden stars (scores are kept) |
| `/hunt_reset yes` | teachers | Set all scores back to 0 (stars stay hidden) |

"Teachers" means players with the `server` privilege. A teacher can also hide
a star by hand: `/giveme scavenger_hunt:star`, then place it.

## Remote control

`club_scripts/hunt_control.py` can scatter stars (around spawn, a spot, or a
student), clear, reset, check status and message everyone from a terminal
while the server runs. The mod watches `<world>/hunt_control/` for requests.

## Settings (in minetest.conf)

    scavenger_hunt.chance = 0.5      # 0 to 1: chance an 80x80 area gets stars
    scavenger_hunt.per_area = 1      # stars in each area that gets them (1-50)
    scavenger_hunt.underwater = 0.5  # 0-1: how often spots over water are used
    scavenger_hunt.caves_per_area = 1  # cave stars per 80x80x80 underground (0 = none)
    scavenger_hunt.cave_min_y = -80  # deepest a cave star can be
    scavenger_hunt.mapgen = true     # false: only scatter/hand-placed stars
    scavenger_hunt.announce = true   # tell everyone when a star is found

## Where stars go

- **Land:** out in the open, never up in trees.
- **Underwater:** on lake and sea floors no deeper than 12 blocks, so they can
  be reached on one breath.
- **Caves:** on cave floors with room to stand, no deeper than `cave_min_y`.
  A star's sparkle column rises straight up through rock, so sparkles coming
  out of the ground mean a cave star is below.

## Team chests

The mod records who placed each chest ("Chest (placed by abel)" when you point
at it). `club_scripts/hunt_stats.py` uses that to count stars in a chest for
the placer's team, so teammates can share a chest without locking it. Stars
in bones (dropped when a player dies) don't count until picked back up.

## Fair play in creative mode

- Stars are not in the creative inventory, and students can't place them.
- Only stars the mod (or a teacher) hid score points; a copied star scores
  nothing.
- Scores are kept by the mod, not counted from inventories, so dropping or
  trading the collected stars doesn't change anyone's score.
- TNT can't destroy stars.

Each find is logged as `<name> found a hunt star at (x,y,z), total N`.
