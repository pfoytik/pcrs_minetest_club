# -*- coding: utf-8 -*-
"""Scavenger Hunt stats, for teachers, from outside the game.

Reads the world's saved hunt data (scores and where unfound stars are), the
server log (when and where each star was found), and where the collected
stars are now: in players' inventories and in chests and other containers.
Opens everything read-only, so it is safe to run while the server is running.

Usage:
    python3 hunt_stats.py WORLD_FOLDER [options]

    python3 hunt_stats.py ~/luanti/worlds/test_pcrs2026
    python3 hunt_stats.py ~/luanti/worlds/test_pcrs2026 --today

Options:
    --log FILE       Server log (default: $LUANTI_LOG, else ../debug.txt)
    --teams FILE     Team list (default: $LUANTI_TEAMS, else ../teams.txt if it
                     exists). One team per line:  Red Team: abel eve pete
    --today          Only count finds from today's log (e.g. this club day)
    --since DATE     Only count finds from the log on/after DATE (YYYY-MM-DD)
    --spawn X,Z      Where students start (default: 0,0), for distances
    --recent N       How many recent finds to list (default: 10)
    --no-map         Skip searching chests (faster on a very big world)

Team totals for stars held: a player's inventory counts for their team, and
a chest counts for the team of whoever placed it (the scavenger_hunt mod
records that) or, for a locked chest, its owner. Stars in bones (left behind
when a player dies) don't count until the player picks them back up.
"""
import argparse
import datetime
import math
import os
import re
import sqlite3
import struct
import sys
from collections import defaultdict

TOKEN = "scavenger_hunt:star_token"
FIND_LINE = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d): ACTION\[[^\]]+\]: (\S+) found a hunt star "
    r"at \((-?\d+),(-?\d+),(-?\d+)\), total (\d+)")
DISTANCE_RINGS = [100, 250, 500, 1000]
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- helpers

def default_log():
    return os.environ.get("LUANTI_LOG", os.path.join(HERE, "..", "debug.txt"))


def default_teams():
    if os.environ.get("LUANTI_TEAMS"):
        return os.environ["LUANTI_TEAMS"]
    path = os.path.normpath(os.path.join(HERE, "..", "teams.txt"))
    return path if os.path.isfile(path) else None


def open_ro(path):
    return sqlite3.connect("file:{}?mode=ro".format(path), uri=True)


def text(v):
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else v


def dist(spawn, x, z):
    return math.hypot(x - spawn[0], z - spawn[1])


def table(headers, rows):
    widths = [max(len(str(v)) for v in col) for col in zip(headers, *rows)]
    line = "  ".join("{:<%d}" % w for w in widths)
    print(line.format(*headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line.format(*r))


def heading(title):
    print("\n" + title)
    print("=" * len(title))


def count_tokens(itemstring):
    """'scavenger_hunt:star_token 5' -> 5; a single item has no number -> 1."""
    parts = itemstring.split()
    if not parts or parts[0] != TOKEN:
        return 0
    return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1


# ------------------------------------------------- scores and hidden stars

def read_storage(world):
    path = os.path.join(world, "mod_storage.sqlite")
    if not os.path.isfile(path):
        sys.exit("No mod_storage.sqlite in {} - is that a world folder?".format(world))
    db = open_ro(path)
    rows = db.execute(
        "SELECT key, value FROM entries WHERE modname = 'scavenger_hunt'").fetchall()
    db.close()

    scores, stars, total_found = {}, [], 0
    for key, value in rows:
        key, value = text(key), text(value)
        if key.startswith("score:"):
            scores[key[len("score:"):]] = int(value or 0)
        elif key == "total_found":
            total_found = int(value or 0)
        elif key == "stars":
            # Saved as a Lua table: return {[hash]=true, ...}
            for h in re.findall(r"\[(\d+)\]=true", value):
                stars.append(unhash(int(h)))
    return scores, stars, total_found


def unhash(h):
    """Undo core.hash_node_position: number -> (x, y, z)."""
    return (h % 65536 - 32768, (h // 65536) % 65536 - 32768,
            (h // 4294967296) % 65536 - 32768)


# ------------------------------------------------------------- the log

def read_finds(log_path, since):
    finds = []
    if not os.path.isfile(log_path):
        print("(No server log at {} - find times and places not shown. "
              "Use --log to point at it.)\n".format(log_path))
        return finds
    with open(log_path, "r", errors="replace") as f:
        for line in f:
            if "found a hunt star" not in line:
                continue
            m = FIND_LINE.match(line)
            if not m:
                continue
            when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            if since and when < since:
                continue
            finds.append((when, m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(5))))
    return finds


# ------------------------------------------------ stars held by players

def scan_players(world):
    """{player: collected stars in their inventory}"""
    path = os.path.join(world, "players.sqlite")
    if not os.path.isfile(path):
        return {}
    db = open_ro(path)
    held = defaultdict(int)
    for player, item in db.execute(
            "SELECT player, item FROM player_inventory_items WHERE item LIKE ?",
            (TOKEN + "%",)):
        held[text(player)] += count_tokens(text(item))
    db.close()
    return dict(held)


# ------------------------------------------- stars stored in containers

def get_decompressor():
    try:
        from compression import zstd  # Python 3.14+
        return zstd.decompress
    except ImportError:
        pass
    try:
        import zstandard  # older Python: pip install zstandard
        return lambda data: zstandard.ZstdDecompressor().decompressobj().decompress(data)
    except ImportError:
        pass
    return system_zstd()


def system_zstd():
    """Fallback for Python < 3.14 with no zstandard package: use the system's
    libzstd (always present on Debian/Ubuntu - apt itself needs it)."""
    import ctypes
    import ctypes.util
    name = ctypes.util.find_library("zstd")
    try:
        lib = ctypes.CDLL(name or "libzstd.so.1")
    except OSError:
        return None
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                    ctypes.c_char_p, ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_getErrorName.restype = ctypes.c_char_p
    lib.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]

    def decompress(data):
        size = 1 << 16  # a map block is usually ~20 KB unpacked
        while True:
            buf = ctypes.create_string_buffer(size)
            n = lib.ZSTD_decompress(buf, size, data, len(data))
            if not lib.ZSTD_isError(n):
                return buf.raw[:n]
            err = lib.ZSTD_getErrorName(n).decode()
            if "too small" not in err.lower() or size >= 1 << 28:
                raise ValueError("zstd: " + err)
            size *= 4
    return decompress


class Reader:
    """Big-endian reader for Luanti's binary map format."""

    def __init__(self, data):
        self.d, self.i = data, 0

    def take(self, n):
        v = self.d[self.i:self.i + n]
        self.i += n
        return v

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack(">H", self.take(2))[0]

    def u32(self):
        return struct.unpack(">I", self.take(4))[0]

    def str16(self):
        return self.take(self.u16())

    def str32(self):
        return self.take(self.u32())

    def inventory(self):
        """Inventory text up to and including 'EndInventory'."""
        # (each list inside ends with 'EndInventoryList', which this won't match)
        end = self.d.index(b"EndInventory\n", self.i)
        inv = self.d[self.i:end]
        self.i = end + len(b"EndInventory\n")
        return inv.decode("utf-8", "replace")


def parse_block(raw):
    """Containers holding collected stars in one map block.
    Returns [(x, y, z inside block, node name, owner, count)]."""
    r = Reader(raw)
    r.u8()   # flags
    r.u16()  # lighting
    r.u32()  # timestamp
    if r.u8() != 0:
        raise ValueError("unknown name-id mapping version")
    names = {}
    for _ in range(r.u16()):
        nid = r.u16()
        names[nid] = r.str16().decode()
    content_width, params_width = r.u8(), r.u8()
    if content_width != 2 or params_width != 2:
        raise ValueError("unexpected node data layout")
    param0 = r.take(4096 * 2)
    r.take(4096 * 2)  # param1 + param2

    found = []
    meta_version = r.u8()
    if meta_version == 0:
        return found
    for _ in range(r.u16()):
        p = r.u16()
        x, y, z = p % 16, (p // 16) % 16, p // 256
        vars_ = {}
        for _ in range(r.u32()):
            key = r.str16().decode("utf-8", "replace")
            vars_[key] = r.str32().decode("utf-8", "replace")
            if meta_version >= 2:
                r.u8()  # private flag
        count = sum(count_tokens(line[5:]) for line in r.inventory().splitlines()
                    if line.startswith("Item "))
        if count:
            nid = struct.unpack(">H", param0[p * 2:p * 2 + 2])[0]
            # Locked chests and bones have an owner; the scavenger_hunt mod
            # records who placed ordinary chests
            owner = vars_.get("owner") or vars_.get("placed_by") or ""
            found.append((x, y, z, names.get(nid, "?"), owner, count))
    return found


def scan_map(world):
    """[(x, y, z, node name, owner, count)] for every container holding stars."""
    decompress = get_decompressor()
    if decompress is None:
        print("*** WARNING: can't search chests - this Python can't read the map. ***\n"
              "*** Chest columns will show '-'. Fix: sudo apt install python3-zstandard ***")
        return None
    db = open_ro(os.path.join(world, "map.sqlite"))
    cols = [c[1] for c in db.execute("PRAGMA table_info(blocks)")]
    if "x" in cols:
        rows = db.execute("SELECT x, y, z, data FROM blocks")
    else:  # older worlds: one number per block position
        rows = ((*unhash_block(p), d) for p, d in db.execute("SELECT pos, data FROM blocks"))
    needle = TOKEN.encode()
    containers, skipped = [], 0
    for bx, by, bz, data in rows:
        if data[0] < 29:
            skipped += 1  # very old block format; Luanti converts it when loaded
            continue
        try:
            raw = decompress(data[1:])
            if needle not in raw:
                continue
            for x, y, z, node, owner, count in parse_block(raw):
                containers.append((bx * 16 + x, by * 16 + y, bz * 16 + z, node, owner, count))
        except Exception as e:  # one damaged block shouldn't stop the report
            print("(Skipped block {},{},{}: {})".format(bx, by, bz, e))
    db.close()
    if skipped:
        print("({} old-format blocks not searched - they update when players visit.)".format(skipped))
    return containers


def unhash_block(p):
    """Old map.sqlite 'pos' number -> block x, y, z."""
    def signed(v):
        return v - 4096 if v >= 2048 else v
    x = signed(p % 4096)
    p = (p - x) // 4096
    y = signed(p % 4096)
    p = (p - y) // 4096
    return x, y, signed(p % 4096)


# ------------------------------------------------------------------ teams

def read_teams(path):
    teams = {}
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if ":" in line:
                team, names = line.split(":", 1)
                teams[team.strip()] = names.split()
    return teams


# ------------------------------------------------------------------ report

def main():
    ap = argparse.ArgumentParser(description="Scavenger Hunt stats for teachers")
    ap.add_argument("world", nargs="?", default=os.environ.get("LUANTI_WORLD"),
                    help="world folder (or set LUANTI_WORLD)")
    ap.add_argument("--log", default=default_log())
    ap.add_argument("--teams", default=default_teams())
    ap.add_argument("--today", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--spawn", default="0,0")
    ap.add_argument("--recent", type=int, default=10)
    ap.add_argument("--no-map", action="store_true")
    args = ap.parse_args()
    if not args.world:
        ap.error("give the world folder, e.g. python3 hunt_stats.py ~/luanti/worlds/test_pcrs2026")

    since = None
    if args.today:
        since = datetime.datetime.combine(datetime.date.today(), datetime.time())
    elif args.since:
        since = datetime.datetime.strptime(args.since, "%Y-%m-%d")
    spawn = tuple(float(v) for v in args.spawn.split(","))

    scores, stars, total_found = read_storage(args.world)
    finds = read_finds(os.path.abspath(args.log), since)
    in_inventory = scan_players(args.world)
    containers = None if args.no_map else scan_map(args.world)
    # Stars in bones were dropped when a player died: they don't count until
    # the player digs the bones and has them back in their inventory
    in_bones = [c for c in containers or [] if c[3].startswith("bones:")]
    stashed = [c for c in containers or [] if not c[3].startswith("bones:")]

    print("Scavenger Hunt - {}".format(os.path.basename(os.path.abspath(args.world))))
    print("Report made {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))

    heading("Summary")
    print("Stars found (all time):    {}".format(total_found))
    print("Stars still hidden:        {}".format(len(stars)))
    print("Players who found any:     {}".format(sum(1 for s in scores.values() if s > 0)))
    print("Held in inventories:       {}".format(sum(in_inventory.values())))
    if containers is not None:
        print("Stored in chests etc.:     {}".format(sum(c[5] for c in stashed)))
        print("In bones (don't count):    {}".format(sum(c[5] for c in in_bones)))
    if since:
        print("Finds since {}:    {}".format(since.strftime("%Y-%m-%d"), len(finds)))

    # Leaderboard
    per = defaultdict(list)
    for when, name, x, y, z in finds:
        per[name].append((when, dist(spawn, x, z)))
    if since:
        heading("Leaderboard (since {})".format(since.strftime("%Y-%m-%d")))
        ranking = sorted(((len(v), n) for n, v in per.items()), key=lambda t: (-t[0], t[1]))
    else:
        heading("Leaderboard (all time)")
        ranking = sorted(((s, n) for n, s in scores.items() if s > 0), key=lambda t: (-t[0], t[1]))
    rows = []
    for rank, (count, name) in enumerate(ranking, 1):
        d = [x[1] for x in per.get(name, [])]
        last = max((x[0] for x in per.get(name, [])), default=None)
        rows.append((rank, name, count, in_inventory.get(name, 0),
                     "{:.0f}".format(sum(d) / len(d)) if d else "-",
                     "{:.0f}".format(max(d)) if d else "-",
                     last.strftime("%m-%d %H:%M") if last else "-"))
    if rows:
        table(["#", "Player", "Found", "Carrying", "Avg dist", "Farthest", "Last find"], rows)
        print("(Distances are in blocks from spawn {:.0f},{:.0f} - "
              "bigger means exploring further.)".format(*spawn))
    else:
        print("No stars found yet.")

    # Teams
    unclaimed = [c for c in stashed if not c[4]]
    if args.teams:
        teams = read_teams(args.teams)
        team_of = {m.lower(): t for t, ms in teams.items() for m in ms}
        found_by = {n.lower(): c for c, n in ranking}
        carried = defaultdict(int)
        for name, n in in_inventory.items():
            carried[team_of.get(name.lower())] += n
        stored = defaultdict(int)
        for c in stashed:
            if c[4]:
                stored[team_of.get(c[4].lower())] += c[5]

        heading("Teams (from {})".format(args.teams))
        rows = []
        for team, members in teams.items():
            found = sum(found_by.get(m.lower(), 0) for m in members)
            rows.append((team, found, carried[team],
                         stored[team] if containers is not None else "-",
                         carried[team] + stored[team],
                         ", ".join(members)))
        rows.sort(key=lambda r: (-r[4], -r[1]))
        table(["Team", "Found", "Carrying", "In chests", "Held now", "Members"], rows)
        if containers is None:
            print("(In chests '-' = chests were NOT searched; see the warning at the top.)")
        print("(Found = stars collected. Held now = stars the team has right now:\n"
              " carried by members + in chests a member placed. Stars in bones don't count.)")
        loose = sorted({n for _, n in ranking} | set(in_inventory) |
                       {c[4] for c in stashed if c[4]})
        missing = [n for n in loose if n.lower() not in team_of]
        if missing:
            print("Not on any team: {}".format(", ".join(missing)))
    else:
        print("\n(No team list. Put one in {} to see team totals.)".format(
            os.path.normpath(os.path.join(HERE, "..", "teams.txt"))))

    # Containers
    if stashed:
        heading("Chests and containers holding stars")
        rows = [("{},{},{}".format(x, y, z), node.split(":")[-1], owner or "(unknown)", n)
                for x, y, z, node, owner, n in sorted(stashed, key=lambda c: -c[5])]
        table(["Where (x,y,z)", "Container", "Placed by", "Stars"], rows)
        if unclaimed:
            print("({} stars are in containers with no recorded placer, so they count "
                  "for no team.\n Chests placed before the mod recorded placers, and "
                  "furnaces etc., show as unknown.)".format(sum(c[5] for c in unclaimed)))
    if in_bones:
        heading("Stars lost in bones (don't count until picked back up)")
        rows = [("{},{},{}".format(x, y, z), owner or "(unknown)", n)
                for x, y, z, _, owner, n in sorted(in_bones, key=lambda c: -c[5])]
        table(["Where (x,y,z)", "Died", "Stars"], rows)

    # Hidden stars by distance
    heading("Where the hidden stars are")
    if stars:
        bands = defaultdict(int)
        for x, _, z in stars:
            d = dist(spawn, x, z)
            bands[next((r for r in DISTANCE_RINGS if d < r), None)] += 1
        rows, low = [], 0
        for r in DISTANCE_RINGS + [None]:
            rows.append(("{}-{} blocks".format(low, r) if r else "{}+ blocks".format(low), bands[r]))
            low = r
        table(["Distance from spawn", "Stars"], rows)
        print("(Stars also appear in land nobody has visited yet, so there are "
              "always more further out.)")
    else:
        print("None hidden right now.")

    if finds and args.recent > 0:
        heading("Most recent finds")
        rows = [(w.strftime("%m-%d %H:%M:%S"), n, "{},{},{}".format(x, y, z),
                 "{:.0f}".format(dist(spawn, x, z)))
                for w, n, x, y, z in finds[-args.recent:][::-1]]
        table(["Time", "Player", "Where (x,y,z)", "Dist"], rows)

    print("\nNote: the server saves to disk every few seconds, so very recent "
          "changes may not show yet.\nStars dropped on the ground aren't counted "
          "(dropped items vanish after 15 minutes).")


if __name__ == "__main__":
    main()
