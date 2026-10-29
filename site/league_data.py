"""Everything the season and franchise pages show, gathered once.

All of it comes from files the pipeline already builds: games.json, the
datasets/ CSVs, trades.json, identities.json, the rules ledger, and the MFL
archive for divisions and playoff brackets. Nothing here computes a new
statistic; it arranges existing ones by season and by franchise.
"""
import csv, json, os, sys
from collections import Counter, defaultdict
from functools import lru_cache

SITE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SITE)
sys.path.insert(0, f"{BASE}/src")
import identities as I
from fetch_mfl import LAST_SEASON

DATA = f"{BASE}/datasets"


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def read_csv(name):
    with open(f"{DATA}/{name}") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=None)
def games():
    return json.load(open(f"{BASE}/games.json"))


@lru_cache(maxsize=None)
def identities():
    return I.build()


@lru_cache(maxsize=None)
def champions():
    return {int(r["season"]): r["champion"] for r in read_csv("champions.csv")}


@lru_cache(maxsize=None)
def luck():
    return {(int(r["season"]), r["owner"]): r for r in read_csv("luck_seasons.csv")}


@lru_cache(maxsize=None)
def legacy_divisions(season):
    """identity -> division name, from the league's own 2000 to 2002 standings pages."""
    import html as H, re
    from archive import CANON, TEAM_RE
    p = f"{BASE}/mfl_archive/legacy/pdl{season}_standings.html"
    if not os.path.exists(p):
        return {}
    text = H.unescape(re.sub(r"<[^>]+>", "|", open(p, encoding="utf-8", errors="replace").read()))
    cells = [c.strip() for c in text.split("|") if c.strip()]
    out, current = {}, None
    for c in cells:
        if re.fullmatch(r"(AFC|NFC) (East|West)", c):
            current = c
            continue
        m = re.fullmatch(rf"({TEAM_RE})", c.lower())
        if current and m:
            out.setdefault(I.label_for(CANON[m.group(1)], season), current)   # its first table is its division
    return out


@lru_cache(maxsize=None)
def divisions(season):
    """identity -> division name: MFL from 2003, the league's standings pages before."""
    p = f"{BASE}/mfl_archive/{season}/league.json"
    if not os.path.exists(p):
        return legacy_divisions(season)
    league = json.load(open(p))["league"]
    names = {d["id"]: d["name"] for d in as_list(league.get("divisions", {}).get("division"))}
    slots = I.slot_index()
    out = {}
    for f in as_list(league["franchises"]["franchise"]):
        team = slots.get((season, f["id"]))
        if team and f.get("division") in names:
            out[I.label_for(team, season)] = names[f["division"]]
    return out


@lru_cache(maxsize=None)
def bracket_teams(season):
    """Teams in the championship brackets (2008 on), else None."""
    slots = I.slot_index()
    out = set()
    for b in (1, 2, 3):
        p = f"{BASE}/mfl_archive/{season}/playoff_bracket_{b}.json"
        if not os.path.exists(p):
            continue
        for r in as_list(json.load(open(p)).get("playoffBracket", {}).get("playoffRound")):
            for g in as_list(r.get("playoffGame")):
                for side in ("home", "away"):
                    fid = (g.get(side) or {}).get("franchise_id")
                    if fid and slots.get((season, fid)):
                        out.add(I.label_for(slots[(season, fid)], season))
    return out or None


@lru_cache(maxsize=None)
def seeds(season):
    """team -> playoff seed in its conference bracket (2008 on): 1 and 2 are the
    division winners, 3 and 4 the wild cards (rule book 2.3)."""
    slots = I.slot_index()
    out = {}
    for b in (1, 2):
        p = f"{BASE}/mfl_archive/{season}/playoff_bracket_{b}.json"
        if not os.path.exists(p):
            continue
        rounds = as_list(json.load(open(p)).get("playoffBracket", {}).get("playoffRound"))
        if not rounds:
            continue
        for g in as_list(rounds[0].get("playoffGame")):
            for side in ("home", "away"):
                x = g.get(side) or {}
                if x.get("franchise_id") and x.get("seed") and (season, x["franchise_id"]) in slots:
                    out[I.label_for(slots[(season, x["franchise_id"])], season)] = int(x["seed"])
    return out


@lru_cache(maxsize=None)
def division_records(season):
    """team -> [wins, losses, ties] against its own division, regular season."""
    divs = divisions(season)
    out = defaultdict(lambda: [0, 0, 0])
    for g in season_games(season):
        if g["stage"] != "regular" or not divs.get(g["team_a"]) or divs.get(g["team_a"]) != divs.get(g["team_b"]):
            continue
        res_b = {"W": "L", "L": "W", "T": "T"}[g["result_a"]]
        for t, res in ((g["team_a"], g["result_a"]), (g["team_b"], res_b)):
            out[t]["WLT".index(res)] += 1
    return out


def season_games(season):
    return [g for g in games() if g["season"] == season]


def postseason(season):
    """(playoff games, consolation games) for a season."""
    post = [g for g in season_games(season) if g["stage"] == "postseason"]
    teams = bracket_teams(season)
    if teams is None:
        return post, []   # before 2008: no toilet bowl yet, so every postseason game is the playoffs
    playoff = [g for g in post if g["team_a"] in teams and g["team_b"] in teams]
    return playoff, [g for g in post if g not in playoff]


def final(season):
    """The championship game: the last playoff game the champion played."""
    champ = champions().get(season)
    playoff, _ = postseason(season)
    mine = [g for g in playoff if champ in (g["team_a"], g["team_b"])]
    return max(mine, key=lambda g: g["week"]) if mine else None


@lru_cache(maxsize=None)
def playoff_record(team):
    """Wins and losses in championship playoff games only, not the toilet bowl."""
    w = l = 0
    for y in seasons():
        playoff, _ = postseason(y)
        for g in playoff:
            if team == g["team_a"]:
                w, l = (w + 1, l) if g["result_a"] == "W" else (w, l + 1)
            elif team == g["team_b"]:
                w, l = (w + 1, l) if g["result_a"] == "L" else (w, l + 1)
    return w, l


@lru_cache(maxsize=None)
def regular_record(team):
    w = l = t = 0
    for y in seasons():
        for r in standings(y):
            if r["team"] == team:
                w, l, t = w + r["w"], l + r["l"], t + r["t"]
    return w, l, t


def runner_up(season):
    g = final(season)
    if not g:
        return None
    return g["team_b"] if g["team_a"] == champions()[season] else g["team_a"]


@lru_cache(maxsize=None)
def standings(season):
    """Regular-season rows, best first: wins, then points."""
    rows = defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0})
    for g in season_games(season):
        if g["stage"] != "regular":
            continue
        # the recorded result, not the score: since 2004 a tied score goes to the
        # team with the higher-scoring player (rule book 6.1)
        res_b = {"W": "L", "L": "W", "T": "T"}[g["result_a"]]
        for t, s, o, res in ((g["team_a"], g["score_a"], g["score_b"], g["result_a"]),
                             (g["team_b"], g["score_b"], g["score_a"], res_b)):
            r = rows[t]
            r["pf"] += s
            r["pa"] += o
            r[res.lower()] += 1
    divs = divisions(season)
    playoff_teams = bracket_teams(season)
    if playoff_teams is None:
        playoff, _ = postseason(season)
        playoff_teams = {x for g in playoff for x in (g["team_a"], g["team_b"])}
    out = []
    for t, r in rows.items():
        lk = luck().get((season, t), {})
        out.append({"team": t, **r, "division": divs.get(t),
                    "allplay": float(lk["allplay_pct"]) if lk else None,
                    "expected": float(lk["expected_wins"]) if lk else None,
                    "luck": float(lk["luck"]) if lk else None,
                    "playoffs": t in playoff_teams,
                    "champion": champions().get(season) == t,
                    "runner_up": runner_up(season) == t})
    out.sort(key=lambda r: (-(r["w"] + 0.5 * r["t"]), -r["pf"]))
    return out


def finish(season, team):
    """Champion, runner-up, playoffs, or nothing."""
    if champions().get(season) == team:
        return "champion"
    if runner_up(season) == team:
        return "runner-up"
    if any(r["team"] == team and r["playoffs"] for r in standings(season)):
        return "playoffs"
    return ""


@lru_cache(maxsize=None)
def trades():
    return json.load(open(f"{BASE}/trades.json"))


def asset_label(a):
    return a.get("label") or a.get("kind", "")


@lru_cache(maxsize=None)
def ledger():
    return json.load(open(f"{BASE}/rules/ledger.json"))["changes"]


def by_owner(name, key="owner"):
    return {r[key]: r for r in read_csv(name)}


@lru_cache(maxsize=None)
def best_pickups():
    return read_csv("best_pickups.csv")


@lru_cache(maxsize=None)
def draft_value():
    return read_csv("draft_value.csv")


@lru_cache(maxsize=None)
def all_drafts():
    """Every pick, 2000 on: the original boards to 2007 (legacy_drafts.py), MFL from 2008.
    The early rows carry no value figures, and no starts before 2003."""
    out = []
    for r in read_csv("drafts_2000_2007.csv"):
        out.append({**r, "complete": "True" if r["starts_any_team"] != "" else "False", "early": True})
    out += [{**r, "early": False} for r in draft_value()]
    return out


@lru_cache(maxsize=None)
def expansion_draft():
    return read_csv("expansion_draft_2001.csv")


@lru_cache(maxsize=None)
def got_away():
    return read_csv("got_away.csv")


@lru_cache(maxsize=None)
def lineup_losses():
    return read_csv("lineup_losses.csv")


@lru_cache(maxsize=None)
def head_to_head():
    out = defaultdict(dict)
    for r in read_csv("head_to_head.csv"):
        a, b = r["owner_a"], r["owner_b"]
        out[a][b] = {"games": int(r["games"]), "w": int(r["a_wins"]), "l": int(r["b_wins"]), "t": int(r["ties"]),
                     "pf": float(r["a_points"]), "pa": float(r["b_points"])}
        out[b][a] = {"games": int(r["games"]), "w": int(r["b_wins"]), "l": int(r["a_wins"]), "t": int(r["ties"]),
                     "pf": float(r["b_points"]), "pa": float(r["a_points"])}
    return out


@lru_cache(maxsize=None)
def name_history():
    """identity -> [(first season, name)], from MFL's names, which start in 2003."""
    owners = json.load(open(f"{BASE}/owners.json"))
    out = {}
    for chain in owners.values():
        hist = [(h["year"], h["name"]) for h in chain.get("name_history", [])]
        out[chain["label"]] = hist
    return out


def seasons():
    return list(range(2000, LAST_SEASON + 1))
