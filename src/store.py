"""Where the data is read from.

Everything downstream reads through here, so the analysis depends on the
archive rather than on MyFantasyLeague being up. `mfl_archive/` is the durable
copy taken by `archive_mfl.py` and checked by its manifest; `raw/` is the older
working cache and is only a fallback, so a checkout with just the archive still
rebuilds every figure.
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = f"{BASE}/mfl_archive"
RAW = f"{BASE}/raw"

# logical name -> (archive filename, old raw filename pattern)
SEASON = {
    "league": ("league.json", "league_{y}.json"),
    "rosters": ("rosters.json", "rosters_{y}.json"),
    "schedule": ("schedule.json", "schedule_{y}.json"),
    "trades": ("transactions_trade.json", "trades_{y}.json"),
    "transactions": ("transactions.json", None),
    "players": ("players.json", "players_{y}.json"),
    "standings": ("standings.json", None),
    "draft_results": ("draft_results.json", None),
    "future_draft_picks": ("future_draft_picks.json", None),
    "player_scores": ("player_scores.json", None),
    "weekly_results": ("weekly_results.json", None),
    "rules": ("rules.json", None),
}

LEGACY = {
    "trades": "history_trades.html",
    "champions": "history_misc.html",
    "record_book": "history_recbook.html",
    "schedule_2000": "pdl2000_schedule.html",
    "schedule_2001": "pdl2001_schedule.html",
    "schedule_2002": "pdl2002_schedule.html",
    "standings_2000": "pdl2000_standings.html",
    "standings_2001": "pdl2001_standings.html",
    "standings_2002": "pdl2002_standings.html",
}


def season(year, kind):
    """Path to a season's file, archive first."""
    arch_name, raw_pattern = SEASON[kind]
    p = f"{ARCHIVE}/{year}/{arch_name}"
    if os.path.exists(p) and os.path.getsize(p) > 2:
        return p
    if raw_pattern:
        q = f"{RAW}/{raw_pattern.format(y=year)}"
        if os.path.exists(q):
            return q
    return p


def bracket(year, n):
    p = f"{ARCHIVE}/{year}/playoff_bracket_{n}.json"
    if os.path.exists(p) and os.path.getsize(p) > 2:
        return p
    return f"{RAW}/bracket_{year}_{n}.json"


def legacy(name):
    p = f"{ARCHIVE}/legacy/{LEGACY[name]}"
    return p if os.path.exists(p) else None


def load(path):
    with open(path) as f:
        return json.load(f)


def seasons():
    """Seasons the archive holds, from its own league map."""
    p = f"{ARCHIVE}/leagues.json"
    if os.path.exists(p):
        return sorted(int(y) for y in load(p))
    return []


def build_player_index(dest=None):
    """Union of every season's player table, which is how ids become names."""
    dest = dest or f"{BASE}/player_index.json"
    index = {}
    for year in seasons():
        p = season(year, "players")
        if not os.path.exists(p):
            continue
        try:
            players = load(p).get("players", {}).get("player", [])
        except (json.JSONDecodeError, AttributeError):
            continue
        for pl in players if isinstance(players, list) else [players]:
            index.setdefault(pl["id"], {"name": pl.get("name"),
                                        "position": pl.get("position")})
    with open(dest, "w") as f:
        json.dump(index, f)
    return len(index)


if __name__ == "__main__":
    print(f"archive seasons: {len(seasons())} ({min(seasons())}-{max(seasons())})")
    missing = [(y, k) for y in seasons() for k in SEASON
               if not os.path.exists(season(y, k))]
    print(f"missing season files: {len(missing)}")
    for y, k in missing[:10]:
        print(f"  {y} {k}")
    gone = [n for n in LEGACY if legacy(n) is None]
    print(f"missing legacy pages: {gone or 'none'}")
    print(f"player index: {build_player_index()} players")
