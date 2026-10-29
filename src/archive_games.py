"""Parse the 2000-2002 game results out of the league's GitHub archive.

MyFantasyLeague has no data at all before 2003, but the archive keeps a
schedule page per season with every score on it, at
mspinola.github.io/mspinola/pdl/pdl<year>/schedule.html.

The page lays two weeks side by side in one table: column 0 is one week,
column 2 the next, column 1 a spacer. A header row names the two weeks, and
the rows under it carry one game per cell as "Team 42 vs Team 104".
"""
import os, re, sys, html, json, urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store
import archive as A
import identities as I

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{BASE}/raw"
YEARS = (2000, 2001, 2002)
UA = "PDL league analytics (+https://github.com/mspinola/pdl)"

# 2000 writes "Team 42 vs Team 104"; 2001 and 2002 write "Team 42 at Team 104"
GAME_RE = re.compile(
    r"^(?P<a>.+?)\s+(?P<sa>-?\d+)\s+(?:vs|at)\.?\s+(?P<b>.+?)\s+(?P<sb>-?\d+)$", re.I)
OWNER_SUFFIX_RE = re.compile(r"\s*--.*$")
POSSESSIVE_RE = re.compile(r"^\S+'s\s+(?P<rest>.+)$")
WEEK_RE = re.compile(r"^Week\s+(\d+)$", re.I)


class Rows(HTMLParser):
    """Collect the table as a list of rows, each a list of cell texts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell, self.in_cell = [], None, [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.in_cell, self.cell = True, []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            text = re.sub(r"\s+", " ", "".join(self.cell)).strip()
            if self.row is not None:
                self.row.append(text)
            self.in_cell = False
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)


def fetch(year):
    archived = store.legacy(f"schedule_{year}")
    if archived:
        return open(archived, encoding="utf-8", errors="replace").read()
    path = f"{RAW}/archive_schedule_{year}.html"
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return open(path, encoding="utf-8", errors="replace").read()
    url = f"https://mspinola.github.io/mspinola/pdl/pdl{year}/schedule.html"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    os.makedirs(RAW, exist_ok=True)
    open(path, "w", encoding="utf-8").write(body)
    return body


def team(name):
    """Canonical team name, with any owner name stripped off.

    The 2001 and 2002 pages append the owner to the team after a double dash,
    and one team is written with its owner's name in front of it. Owner names
    are discarded here and never stored: this feeds a public page.
    Possessives that are part of a team's real name, as in Carter's Commandos
    and Scooter's Boozers, are kept by trying the whole name first.
    """
    n = OWNER_SUFFIX_RE.sub("", name).strip().rstrip(".")
    found = A.CANON.get(n.lower())
    if found:
        return found
    m = POSSESSIVE_RE.match(n)
    if m:
        return A.CANON.get(m.group("rest").strip().lower())
    return None


def parse_year(year):
    p = Rows()
    p.feed(fetch(year))
    games, unparsed = [], []
    col_week = {}
    for row in p.rows:
        heads = {i: int(m.group(1)) for i, c in enumerate(row)
                 if (m := WEEK_RE.match(c))}
        if heads:
            col_week = heads
            continue
        for i, cell in enumerate(row):
            if not cell or i not in col_week:
                continue
            m = GAME_RE.match(cell)
            if not m:
                unparsed.append((year, col_week[i], cell))
                continue
            a, b = team(m.group("a")), team(m.group("b"))
            if not a or not b or a == b:
                unparsed.append((year, col_week[i], cell))
                continue
            sa, sb = int(m.group("sa")), int(m.group("sb"))
            games.append({
                "season": year, "week": col_week[i],
                "team_a": a, "team_b": b,
                "score_a": float(sa), "score_b": float(sb),
                "result_a": "W" if sa > sb else "L" if sa < sb else "T",
                "source": "archive",
            })
    return games, unparsed


def parse():
    allg, allu = [], []
    for y in YEARS:
        g, u = parse_year(y)
        allg += g
        allu += u
    return allg, allu


def stage_games():
    """Games with the regular season and postseason separated.

    The archive page does not label playoff rounds, so the same narrowing rule
    used for the 2003-2007 MFL seasons applies: a full slate is teams/2 games,
    and a week carrying fewer than that is a playoff round.
    """
    games, _ = parse()
    by_week = {}
    for g in games:
        by_week.setdefault((g["season"], g["week"]), 0)
        by_week[(g["season"], g["week"])] += 1
    full = {}
    for (season, week), n in by_week.items():
        full[season] = max(full.get(season, 0), n)
    for g in games:
        n = by_week[(g["season"], g["week"])]
        g["stage"] = "regular" if n == full[g["season"]] else "postseason"
        g["team_a"] = I.label_for(g["team_a"], g["season"])
        g["team_b"] = I.label_for(g["team_b"], g["season"])
    return games


if __name__ == "__main__":
    games, unparsed = parse()
    print(f"parsed {len(games)} games from {len(YEARS)} seasons")
    for y in YEARS:
        ws = sorted({g["week"] for g in games if g["season"] == y})
        if not ws:
            print(f"  {y}: no games parsed")
            continue
        per = [sum(1 for g in games if g["season"] == y and g["week"] == w) for w in ws]
        teams = {t for g in games if g["season"] == y for t in (g["team_a"], g["team_b"])}
        print(f"  {y}: {sum(per)} games, weeks {min(ws)}-{max(ws)}, "
              f"{len(teams)} teams, per week {per}")
    print(f"\nunparsed cells: {len(unparsed)}")
    for y, w, c in unparsed[:12]:
        print(f"  [{y} wk{w}] {c[:100]}")

    staged = stage_games()
    json.dump(staged, open(f"{BASE}/archive_games.json", "w"))
    print("\nafter staging:")
    for y in YEARS:
        rs = [g for g in staged if g["season"] == y and g["stage"] == "regular"]
        ps = [g for g in staged if g["season"] == y and g["stage"] == "postseason"]
        rec = {}
        for g in rs:
            rec[g["team_a"]] = rec.get(g["team_a"], 0) + 1
            rec[g["team_b"]] = rec.get(g["team_b"], 0) + 1
        print(f"  {y}: {len(rs)} regular + {len(ps)} postseason, "
              f"games per team {sorted(set(rec.values()))}")
