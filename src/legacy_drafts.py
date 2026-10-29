"""The 2000 to 2007 drafts, from the league's own draft boards.

MFL's draft results start in 2008. Before that the drafts are on the original
site, archived in mfl_archive/legacy/:

- 2000 to 2004: setup/draft.html, a table of pick, overall, team, player,
  position. The team cell can carry a pick's history ("Ho Train From: Moose
  From: Blitzkrieg"): the first team named is the one that drafted.
- 2005 to 2007: setup/draft_team.html, each team's picks as "round-pick |
  POS - Surname, First (NFL team)". (2007's by-round page is an empty template.)
- 2001: setup/expdraft.html, the expansion draft for Beers and OakalDoakals.

From 2003, when MFL kept lineups, each pick is matched to MFL's player list by
name and position, and its starts are counted over three seasons as for the
later drafts (draft_value.py): for any team, and for the drafting team. 2000 to
2002 picks have no lineups to count.

    python3 src/legacy_drafts.py   # datasets/drafts_2000_2007.csv, datasets/expansion_draft_2001.csv
"""
import csv, html, json, os, re, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import weekly
from archive import CANON, TEAM_RE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEG = f"{BASE}/mfl_archive/legacy"
HORIZON, HIT = 3, 10
POS = {"D": "Def", "DEF": "Def", "O/D": "Def", "OD": "Def", "PK": "K", "K": "K"}


# spellings on the draft boards that the trade parser never met
BOARD_SPELLINGS = {"cammandos": "Carter's Commandos", "ho trian": "Ho Train", "bnchalosers": "Bunchalosers"}


def team_of(cell, season):
    low = cell.lower()
    hits = [(low.find(k), v) for k, v in BOARD_SPELLINGS.items() if k in low]
    m = re.search(TEAM_RE, low)
    if m:
        hits.append((m.start(), CANON[m.group(0)]))
    return I.label_for(min(hits)[1], season) if hits else None


def rows_of(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S | re.I)
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
        if any(cells):
            out.append(cells)
    return out


def table_board(season):
    """2000 to 2004."""
    picks, rnd, last_pick = [], 1, 0
    for c in rows_of(f"{LEG}/pdl{season}_setup_draft.html"):
        c = [x for x in c if x != ""]
        if len(c) < 5 or not c[0].isdigit() or not c[1].isdigit():
            continue
        pick, overall = int(c[0]), int(c[1])
        if pick < last_pick:
            rnd += 1
        last_pick = pick
        team = team_of(c[2], season)
        if not team or not c[3].strip("- "):
            continue   # a row of dashes is a pick not made
        picks.append({"season": season, "round": rnd, "pick": pick, "overall": overall, "team": team,
                      "player": c[3], "position": POS.get(c[4].upper(), c[4].upper())})
    return picks


def team_board(season):
    """2005 to 2007: each team's heading, then "round-pick | POS - Surname, First (Tm)"."""
    t = open(f"{LEG}/pdl{season}_setup_draft_team.html", encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S | re.I)
    cells = [re.sub(r"\s+", " ", html.unescape(c)).strip() for c in re.split(r"<[^>]+>", t)]
    cells = [c for c in cells if c]
    picks, team = [], None
    for i, c in enumerate(cells):
        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", c)
        if not m:
            if re.fullmatch(rf"(?:{TEAM_RE})[\w' .-]*", c.lower()) and len(c) < 40:
                team = team_of(c, season)
            continue
        nxt = cells[i + 1] if i + 1 < len(cells) else ""
        if not team or "No Pick Made" in nxt:
            continue
        pm = re.match(r"([A-Z/]+)\s*-\s*(.+?)(?:\s*\(([A-Za-z]+)\))?$", nxt)
        if not pm:
            continue
        picks.append({"season": season, "round": int(m.group(1)), "pick": int(m.group(2)), "overall": None,
                      "team": team, "player": pm.group(2).strip(), "position": POS.get(pm.group(1), pm.group(1))})
    teams = len({p["team"] for p in picks})
    for p in picks:
        p["overall"] = (p["round"] - 1) * max(teams, 16) + p["pick"]
    return picks


def expansion():
    out = []
    for c in rows_of(f"{LEG}/pdl2001_setup_expdraft.html"):
        if len(c) >= 4 and re.search(TEAM_RE, c[1].lower()) and c[2] and c[2] != ".":
            rnd = c[0] if c[0].isdigit() else (out[-1]["round"] if out else "")
            out.append({"round": rnd, "team": team_of(c[1], 2001), "player": c[2],
                        "taken_from": team_of(c[3], 2001) or c[3]})
    return out


# ------------------------------------------------------------------ matching and starts

def player_index():
    idx = json.load(open(f"{BASE}/player_index.json"))
    by_surname = defaultdict(list)
    for pid, p in idx.items():
        name = p["name"]
        surname = name.split(",")[0].strip().lower()
        first = name.split(",")[1].strip().lower() if "," in name else ""
        pos = "K" if p.get("position") == "PK" else p.get("position")   # MFL says PK, the boards K
        by_surname[surname].append((pid, first, pos))
    return idx, by_surname


# the boards' abbreviations where MFL's differ
ALT_CODES = {"JAX": "JAC", "SF": "SFO", "NE": "NEP", "GB": "GBP", "KC": "KCC", "NO": "NOS", "SD": "SDC", "TB": "TBB"}


def defense_codes():
    """NFL team code, as MFL writes it (TBB, NEP), -> defense id."""
    out = {}
    for y in range(2003, 2008):
        for p in json.load(open(f"{BASE}/mfl_archive/{y}/players.json")).get("players", {}).get("player", []):
            if p.get("position") == "Def" and p.get("team"):
                out.setdefault(p["team"], p["id"])
    return out


def close_on_roster(p, idx, rostered_by_team):
    """A misspelled name ("B Leftwitch"): the closest surname among players the
    drafting team rostered that season, at the same position, if clearly close."""
    import difflib
    surname, first = split_name(p["player"], p["position"])
    best, score = None, 0.0
    for pid in rostered_by_team.get((p["season"], p["team"]), ()):
        q = idx.get(pid, {})
        pos = "K" if q.get("position") == "PK" else q.get("position")
        if p["position"] not in ("", "-", None) and pos != p["position"]:
            continue
        s2, _, f2 = q.get("name", "").partition(", ")
        if first and f2 and f2[0].lower() != first[0]:
            continue
        r = difflib.SequenceMatcher(None, surname, s2.lower()).ratio()
        if r > score:
            best, score = pid, r
    return best if score >= 0.75 else None


def split_name(raw, position):
    raw = raw.strip()
    if "," in raw:
        surname, first = (x.strip() for x in raw.split(",", 1))
    else:
        parts = raw.split()
        surname, first = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (raw, "")
    return surname.lower(), first.lower().rstrip(".")


def match(p, by_surname, rostered, codes=None):
    """The MFL id of a drafted player, or None if it is not clear."""
    if p["position"] == "Def":
        raw = p["player"].split("(")[0].strip()
        city = raw.lower()
        abbr = ALT_CODES.get(raw.upper(), raw.upper())
        code = [c for c in (codes or {}) if 2 <= len(raw) <= 3 and c.startswith(abbr)]
        if len(code) == 1:
            return codes[code[0]]
        cands = [pid for s, lst in by_surname.items() for pid, first, pos in lst
                 if pos == "Def" and (city in s or city in first or s in city)]
    else:
        surname, first = split_name(p["player"], p["position"])
        cands = [pid for pid, f, pos in by_surname.get(surname, [])
                 if (not first or f.startswith(first[:1])) and (pos == p["position"] or p["position"] in ("", "-", None))]
        if first and len(first) > 1:
            exact = [pid for pid in cands if any(f == first for x, f, _ in by_surname[surname] if x == pid)]
            cands = exact or cands
    if len(cands) > 1:   # prefer whoever the drafting team rostered, then anyone rostered that season
        mine = [c for c in cands if (p["season"], p["team"], c) in rostered]
        cands = mine or [c for c in cands if (p["season"], None, c) in rostered] or cands
    return cands[0] if len(cands) == 1 else None


def main():
    picks = []
    for y in range(2000, 2005):
        picks += table_board(y)
    for y in range(2005, 2008):
        picks += team_board(y)
    rows = weekly.seasons(2003, 2009)
    rostered, starts = set(), defaultdict(list)
    for r in rows:
        for pl in r["players"]:
            rostered.add((r["season"], r["team"], pl["id"]))
            rostered.add((r["season"], None, pl["id"]))
            if r["stage"] == "regular" and pl["started"]:
                starts[pl["id"]].append((r["season"], r["team"]))
    idx, by_surname = player_index()
    codes = defense_codes()
    rostered_by_team = defaultdict(set)
    for y, t, pid in rostered:
        if t:
            rostered_by_team[(y, t)].add(pid)
    matched = 0
    for p in picks:
        p["player_id"] = p["starts_any_team"] = p["starts"] = p["hit"] = p["kept"] = None
        if p["season"] < 2003:
            continue
        pid = match(p, by_surname, rostered, codes) or close_on_roster(p, idx, rostered_by_team)
        if not pid:
            continue
        matched += 1
        window = [t for y, t in starts.get(pid, []) if p["season"] <= y < p["season"] + HORIZON]
        p.update(player_id=pid, starts_any_team=len(window), starts=sum(1 for t in window if t == p["team"]))
        p["hit"] = p["starts_any_team"] >= HIT
        p["kept"] = p["starts"] >= HIT
    cols = ["season", "round", "pick", "overall", "team", "player", "position", "player_id",
            "starts_any_team", "starts", "hit", "kept"]
    with open(f"{BASE}/datasets/drafts_2000_2007.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows([[("" if p[c] is None else p[c]) for c in cols] for p in picks])
    exp = expansion()
    with open(f"{BASE}/datasets/expansion_draft_2001.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "team", "player", "taken_from"])
        w.writerows([[e["round"], e["team"], e["player"], e["taken_from"]] for e in exp])
    per = Counter(p["season"] for p in picks)
    later = [p for p in picks if p["season"] >= 2003]
    print("picks by season: " + ", ".join(f"{y}: {n}" for y, n in sorted(per.items())))
    print(f"2003 to 2007: {matched} of {len(later)} picks matched to MFL players ({100 * matched / len(later):.0f}%)")
    print(f"expansion draft 2001: {len(exp)} picks")
    print("wrote datasets/drafts_2000_2007.csv and datasets/expansion_draft_2001.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
