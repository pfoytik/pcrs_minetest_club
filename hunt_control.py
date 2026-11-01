# -*- coding: utf-8 -*-
"""Control the Scavenger Hunt on a running server, from a terminal (e.g. ssh).

The scavenger_hunt mod checks <world>/hunt_control every 2 seconds, carries
out the request, and replies. The server must be running.

Usage:
    python3 hunt_control.py [--world WORLD] COMMAND ...

Commands:
    status                         Hidden/found counts and who's online
    players                        Online players: position, score, team
    scatter COUNT [RADIUS]         Hide stars (default radius 200, around spawn)
        [--mode land|water|cave]   Where to hide them (default land)
        [--at X Z]                 Around a spot instead of spawn
        [--near PLAYER]            Around a player (help someone out!)
    say MESSAGE                    Message everyone in the game
    clear                          Remove every hidden star (asks first)
    reset                          Set every score to 0 (asks first)

Examples:
    python3 hunt_control.py scatter 30 250
    python3 hunt_control.py scatter 10 250 --mode cave
    python3 hunt_control.py scatter 3 30 --near abel
    python3 hunt_control.py say "20 new stars hidden near spawn!"

The world is --world, else $LUANTI_WORLD. Teams come from ../teams.txt or
$LUANTI_TEAMS (same as hunt_stats.py).
"""
import argparse
import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 60  # seconds; scattering in new land can take a while to generate


def load_teams():
    path = os.environ.get("LUANTI_TEAMS") or os.path.join(HERE, "..", "teams.txt")
    team_of = {}
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if ":" in line:
                    team, names = line.split(":", 1)
                    for n in names.split():
                        team_of[n.lower()] = team.strip()
    return team_of


def send(world, request, timeout=TIMEOUT):
    """Hand a request to the server and wait for its reply."""
    folder = os.path.join(world, "hunt_control")
    if not os.path.isdir(folder):
        sys.exit("No {} - is the scavenger_hunt mod on in this world, and has the "
                 "server been started since it was installed?".format(folder))
    rid = uuid.uuid4().hex[:12]
    tmp = os.path.join(folder, rid + ".tmp")
    with open(tmp, "w") as f:
        f.write(request + "\n")
    os.rename(tmp, os.path.join(folder, rid + ".cmd"))  # appears all at once

    out = os.path.join(folder, rid + ".out")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(out):
            time.sleep(0.1)  # let the server finish writing
            with open(out) as f:
                answer = json.load(f)
            os.remove(out)
            return answer
        time.sleep(0.5)
    cmd = os.path.join(folder, rid + ".cmd")
    if os.path.exists(cmd):
        os.remove(cmd)
        sys.exit("No answer: the server doesn't seem to be running this world.")
    sys.exit("The server took the request but hasn't answered yet; "
             "check in game or run 'status' in a moment.")


def confirm(question):
    if input(question + " Type yes to go ahead: ").strip().lower() == "yes":
        return True
    print("Cancelled.")
    return False


def show_players(players, team_of):
    if not players:
        print("Nobody is online.")
        return
    rows = [(p["name"], team_of.get(p["name"].lower(), "-"),
             "{},{},{}".format(p["x"], p["y"], p["z"]), p["score"]) for p in players]
    headers = ("Player", "Team", "Position (x,y,z)", "Stars found")
    widths = [max(len(str(v)) for v in col) for col in zip(headers, *rows)]
    line = "  ".join("{:<%d}" % w for w in widths)
    print(line.format(*headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line.format(*r))


def main():
    ap = argparse.ArgumentParser(description="Control the Scavenger Hunt on a running server",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Commands:")[1])
    ap.add_argument("--world", default=os.environ.get("LUANTI_WORLD"))
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("players")
    sc = sub.add_parser("scatter")
    sc.add_argument("count", type=int)
    sc.add_argument("radius", type=int, nargs="?", default=200)
    sc.add_argument("--mode", choices=["land", "water", "cave"], default="land")
    where = sc.add_mutually_exclusive_group()
    where.add_argument("--at", nargs=2, type=int, metavar=("X", "Z"))
    where.add_argument("--near", metavar="PLAYER")
    sy = sub.add_parser("say")
    sy.add_argument("message", nargs="+")
    sub.add_parser("clear")
    sub.add_parser("reset")
    args = ap.parse_args()
    if not args.world:
        ap.error("say which world: --world ~/luanti/worlds/NAME (or set LUANTI_WORLD)")
    world = os.path.expanduser(args.world)

    if args.command == "scatter":
        if args.at:
            place = "at {} {}".format(*args.at)
        elif args.near:
            place = "near " + args.near
        else:
            place = "spawn"
        request = "scatter {} {} {} {}".format(args.count, args.radius, args.mode, place)
        print("Hiding stars... (land that doesn't exist yet gets generated first)")
    elif args.command == "say":
        request = "say " + " ".join(args.message).replace("\n", " ")
    elif args.command == "clear":
        if not confirm("This removes EVERY hidden star from the world."):
            return
        request = "clear"
    elif args.command == "reset":
        if not confirm("This sets EVERYONE's score back to 0."):
            return
        request = "reset"
    else:
        request = args.command

    answer = send(world, request)
    print(answer.get("message", ""))
    data = answer.get("data") or {}
    if args.command in ("status", "players") and "players" in data:
        print()
        show_players(data["players"], load_teams())
    sys.exit(0 if answer.get("ok") else 1)


if __name__ == "__main__":
    main()
