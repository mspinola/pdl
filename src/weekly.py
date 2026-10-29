"""Every team's weekly lineup and score, from mfl_archive/<season>/weeks/.

One record per team per week:

    {"season", "week", "team", "stage", "score", "optimal", "opponent",
     "opp_score", "players": [{"id", "score", "started", "should_start"}]}

stage is "regular" for the regular season (games.json), "playoffs" for a game
in one of the championship brackets (the two conference brackets and the
final, playoff_bracket_1 to _3), and "consolation" for anything else MFL scored
in the postseason weeks, which is mostly the toilet bowl. MFL kept lineups from 2003, but
its 2003 to 2007 scoring setup does not match the rule book (see
docs/rulebook/mfl-check.md), so analyses use 2008 on by default.
"""
import json, os, sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = f"{BASE}/mfl_archive"
FIRST_RELIABLE = 2008


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


@lru_cache(maxsize=None)
def _stages():
    out = {}
    for g in json.load(open(f"{BASE}/games.json")):
        out[(g["season"], g["week"], g["team_a"])] = g["stage"]
        out[(g["season"], g["week"], g["team_b"])] = g["stage"]
    return out


@lru_cache(maxsize=None)
def _brackets(year):
    """(week, franchise id) for every championship bracket game."""
    out = set()
    for b in (1, 2, 3):
        p = f"{ARCHIVE}/{year}/playoff_bracket_{b}.json"
        if not os.path.exists(p):
            continue
        for r in as_list(json.load(open(p)).get("playoffBracket", {}).get("playoffRound")):
            for g in as_list(r.get("playoffGame")):
                for side in ("home", "away"):
                    fid = (g.get(side) or {}).get("franchise_id")
                    if fid:
                        out.add((int(r["week"]), fid))
    return out


@lru_cache(maxsize=None)
def _slots():
    return I.slot_index()


@lru_cache(maxsize=None)
def season(year):
    d = f"{ARCHIVE}/{year}/weeks"
    out = []
    if not os.path.isdir(d):
        return tuple()
    stages, slots, brackets = _stages(), _slots(), _brackets(year)
    for name in sorted(os.listdir(d)):
        week = int(name[-7:-5])
        w = json.load(open(f"{d}/{name}")).get("weeklyResults", {})
        for m in as_list(w.get("matchup")):
            fr = [f for f in as_list(m.get("franchise")) if isinstance(f, dict)]
            rows = []
            for f in fr:
                team = slots.get((year, f.get("id")))
                if not team:
                    continue
                team = I.label_for(team, year)
                rows.append({
                    "season": year, "week": week, "team": team,
                    "stage": ("regular" if stages.get((year, week, team)) == "regular"
                              else "playoffs" if (week, f.get("id")) in brackets else "consolation"),
                    "score": float(f.get("score") or 0), "optimal": float(f.get("opt_pts") or 0),
                    "players": [{"id": p["id"], "score": float(p.get("score") or 0),
                                 "started": p.get("status") == "starter",
                                 "should_start": p.get("shouldStart") == "1"} for p in as_list(f.get("player"))],
                })
            for r in rows:
                other = [o for o in rows if o is not r]
                r["opponent"] = other[0]["team"] if other else None
                r["opp_score"] = other[0]["score"] if other else None
            out += rows
    return tuple(out)


def seasons(first=FIRST_RELIABLE, last=None):
    from fetch_mfl import LAST_SEASON
    last = last or LAST_SEASON
    return [r for y in range(first, last + 1) for r in season(y)]


@lru_cache(maxsize=None)
def positions():
    """MFL player id -> position, K for a kicker."""
    out = {}
    for k, v in json.load(open(f"{BASE}/player_index.json")).items():
        p = v.get("position")
        out[k] = "K" if p == "PK" else p
    return out


def starter_averages(rows):
    """(season, position) -> average starter's points that season, and
    (season, "*") -> average over all starters. Regular season."""
    import statistics
    from collections import defaultdict
    pos, by = positions(), defaultdict(list)
    for r in rows:
        if r["stage"] == "regular":
            for p in r["players"]:
                if p["started"]:
                    by[(r["season"], pos.get(p["id"]))].append(p["score"])
    out = {k: statistics.mean(v) for k, v in by.items() if len(v) > 20}
    for y in {k[0] for k in by}:
        out[(y, "*")] = statistics.mean(x for k, v in by.items() if k[0] == y for x in v)
    return out


def over_average(score, season, position, averages):
    """A start's points above the average starter at its position, in average starts."""
    if (season, position) not in averages:
        return 0.0
    return (score - averages[(season, position)]) / averages[(season, "*")]
