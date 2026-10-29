"""Every waiver claim and free agent pickup, 2000 to the current season.

One row per player added or dropped, from two sources:

- 2000 to 2007: the league's own transaction pages (mfl_archive/legacy/
  pdl<year>_trans.html). Before 2008 every add went through waivers: the 2006
  rule book says "There will be no free agents; all players are on waivers."
- 2008 on: MyFantasyLeague's transaction log. MFL logs a first-come-first-served
  pickup as FREE_AGENT from 2017, but before that as WAIVER, the same type as a
  waiver claim. They are told apart by time: a claim is processed in the weekly
  waiver run, so it carries the run's timestamp (within two minutes of an
  AUTO_PROCESS_WAIVERS or PROCESS_WAIVERS entry). From 2017, when MFL logs the
  two separately, every WAIVER entry sits at a run, which is the check on the
  rule.

Trades are left to trades.py. IR moves are kept as their own channel and are
not pickups.

    python3 src/transactions.py      # writes transactions.json
"""
import datetime as dt, html, json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import store
from archive import CANON, TEAM_RE
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = f"{BASE}/mfl_archive/legacy"
ET = dt.timezone(dt.timedelta(hours=-5))   # the league's clock; the hour of DST does not matter here
RUN_WINDOW = 120                            # seconds between a claim and its waiver run

WEEK_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen".split())}


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def kickoff(season):
    """The Thursday of NFL week 1: three days after Labor Day."""
    d = dt.date(season, 9, 1)
    labor = d + dt.timedelta(days=(0 - d.weekday()) % 7)
    return labor + dt.timedelta(days=3)


def week_of(season, when):
    """NFL week a move counts toward. Each week runs Tuesday to Monday, so a
    pickup on the Tuesday or Wednesday before a Thursday kickoff is for that
    week. 0 is the preseason, after the draft."""
    start = dt.datetime.combine(kickoff(season) - dt.timedelta(days=2), dt.time(), ET)
    return max(0, (when - start).days // 7 + 1)


def team_label(name, season):
    m = re.search(TEAM_RE, name.lower())
    return I.label_for(CANON[m.group(0)], season) if m else None


def position_of(name, index):
    if re.search(r"Over Def|Overall Defense|Defense", name):
        return "Def"
    return index.get(re.sub(r"\s+", " ", name.split(" (")[0]).strip().lower())


def name_index():
    """'surname, first' -> position, from the player tables."""
    out = {}
    for p in json.load(open(f"{BASE}/player_index.json")).values():
        out.setdefault(p["name"].lower(), p.get("position"))
    return out


# ------------------------------------------------------------------ 2000-2002

PRE_ROW = re.compile(r"^\s*\d+\.?\s+(.+?)\s{2,}((?:Waiver|Trade|Free Agent)\s*-\s*)?(Acquire|Release)\s+(.+?)\s*$")


def legacy_pre(season, index):
    t = open(f"{LEGACY}/pdl{season}_trans.html", encoding="utf-8", errors="replace").read()
    out, week = [], None
    for line in t.split("\n"):
        h = re.search(r"Week\s+([A-Za-z]+)\s*</H3>", line, re.I)
        if h:
            week = WEEK_WORDS.get(h.group(1).lower())
            continue
        m = PRE_ROW.match(html.unescape(re.sub(r"<[^>]+>", "", line)))
        if not m or (m.group(2) or "").startswith("Trade"):
            continue
        team = team_label(m.group(1), season)
        if not team:
            continue
        player = m.group(4).strip()
        out.append({"season": season, "week": week, "when": None, "team": team, "source": "legacy",
                    "action": "add" if m.group(3) == "Acquire" else "drop", "channel": "waiver",
                    "player": player, "player_id": None, "position": position_of(player, index)})
    return out


# ------------------------------------------------------------------ 2003-2007

def legacy_table(season, index):
    t = open(f"{LEGACY}/pdl{season}_trans.html", encoding="utf-8", errors="replace").read()
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
        if len(cells) < 5 or cells[3] != "Waiver":
            continue
        team = team_label(cells[2], season)
        if not team:
            continue
        when = dt.datetime.strptime(cells[1].replace(" EST", "").replace(" EDT", ""), "%m/%d/%y %I:%M %p").replace(tzinfo=ET)
        for verb, player in re.findall(r"(Acquire|Waive):\s*(.+?\([A-Za-z]+ [A-Za-z]+\)|Overall Defense \([A-Za-z]+\))", cells[4]):
            pos = re.search(r"\(([A-Za-z]+) [A-Za-z]+\)", player)
            out.append({"season": season, "week": int(cells[0]) if cells[0].isdigit() else week_of(season, when),
                        "when": when, "team": team, "source": "legacy",
                        "action": "add" if verb == "Acquire" else "drop", "channel": "waiver",
                        "player": player.split(" (")[0], "player_id": None,
                        "position": "Def" if player.startswith("Overall Defense") else
                        {"PK": "K"}.get(pos.group(1), pos.group(1)) if pos else None})
    return out


# ------------------------------------------------------------------ 2008 on

def mfl(season, slots, players):
    path = store.season(season, "transactions")
    if not os.path.exists(path):
        return [], {}
    tx = as_list(store.load(path).get("transactions", {}).get("transaction"))
    runs = sorted(int(x["timestamp"]) for x in tx if x.get("type") in ("AUTO_PROCESS_WAIVERS", "PROCESS_WAIVERS"))
    check = Counter()
    out = []

    def at_run(ts):
        return any(abs(ts - r) <= RUN_WINDOW for r in runs)

    def rows(team, when, channel, ids, action):
        for pid in [p for p in ids.split(",") if p]:
            p = players.get(pid, {})
            out.append({"season": season, "week": week_of(season, when), "when": when, "team": team,
                        "source": "mfl", "action": action, "channel": channel, "player": p.get("name"),
                        "player_id": pid, "position": {"PK": "K"}.get(p.get("position"), p.get("position"))})

    for x in tx:
        kind = x.get("type")
        if kind not in ("WAIVER", "FREE_AGENT", "IR") or not x.get("franchise"):
            continue
        team = slots.get((season, x["franchise"]))
        if team is None:
            continue
        ts = int(x["timestamp"])
        when = dt.datetime.fromtimestamp(ts, ET)
        team = I.label_for(team, season)
        if kind == "IR":
            rows(team, when, "ir", x.get("deactivated", ""), "to IR")
            rows(team, when, "ir", x.get("activated", ""), "from IR")
            continue
        if kind == "WAIVER":
            channel = "waiver" if at_run(ts) else "free_agent"
            if season >= 2017:
                check["claims at a run" if channel == "waiver" else "claims off a run"] += 1
            rows(team, when, channel, x.get("added", ""), "add")
            rows(team, when, channel, x.get("dropped", ""), "drop")
        else:
            adds, _, drops = x.get("transaction", "").partition("|")
            rows(team, when, "free_agent", adds, "add")
            rows(team, when, "free_agent", drops, "drop")
    return out, check


def build():
    slots = I.slot_index()
    index = name_index()
    players = json.load(open(f"{BASE}/player_index.json"))
    moves, check = [], Counter()
    for season in range(2000, LAST_SEASON + 1):
        if season <= 2002:
            moves += legacy_pre(season, index)
        elif season <= 2007:
            moves += legacy_table(season, index)
        else:
            rows, c = mfl(season, slots, players)
            moves += rows
            check.update(c)
    return moves, check


def main():
    moves, check = build()
    out = [{**m, "when": m["when"].isoformat() if m["when"] else None} for m in moves]
    with open(f"{BASE}/transactions.json", "w") as f:
        json.dump(out, f, indent=0)
    adds = [m for m in moves if m["action"] == "add"]
    by = Counter((m["season"] <= 2007, m["channel"]) for m in adds)
    print(f"{len(moves):,} player moves, {len(adds):,} adds: "
          f"{by[(True, 'waiver')]:,} waiver claims before 2008, "
          f"{by[(False, 'waiver')]:,} waiver claims and {by[(False, 'free_agent')]:,} free agent pickups from 2008")
    print(f"  the timing rule, from 2017 when MFL logs the two apart: {dict(check)}")
    no_team = [m for m in moves if not m["team"]]
    no_pos = sum(1 for m in adds if not m["position"])
    print(f"  adds with no position: {no_pos} of {len(adds)}")
    per = Counter(m["season"] for m in adds)
    print("  adds by season: " + " ".join(f"{y}:{per[y]}" for y in sorted(per)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
