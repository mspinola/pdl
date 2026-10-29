"""Bring the original site's record book (pdl/history/recbook.html) up to date.

That page lists, for each category, every season's leader, newest first, and
was kept by hand through 2015. This computes the same categories for the
seasons since and inserts them at the top of each list, leaving every earlier
entry exactly as it was kept.

The hand-kept book does not follow one definition throughout (its 2009 to 2015
season totals reconcile with no single rule), so the new seasons use the
definitions that match most of what it kept, stated on the page. Team records
are regular-season games: that matches 14 of the 16 game records and 31 of the
32 win and loss records it has for 2000 to 2015. A position's best game counts
every week of the league's season, playoffs included, and every player that
week (weeks/player_scores_wNN.json), the team being whoever had him on its
roster, or Free Agent: that matches 43 of its 48 entries for 2008 to 2015, and
the other five are 2012, evidently written before that season's last weeks.

    python3 src/legacy_record_book.py ~/code/mspinola --dry-run
    python3 src/legacy_record_book.py ~/code/mspinola --apply

Each run adds the seasons the page does not have yet, so after a season ends
the next run adds that one. --correct-dry-run and --correct rewrite the kept
entries that the games contradict (team records for every season, position
records from 2008), and mark the page as corrected.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))
import league_data as d
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "pdl/history/recbook.html"
FIRST_NEW = 2016
NOTE = ("<P><I>2016 on: computed from the league's MyFantasyLeague archive. Team records are regular-season "
        "games. A position's best game counts every week of the season, playoffs included, and every player, "
        "the team being whoever had him on its roster that week, or Free Agent. 2000 to 2015 are as they were "
        "kept.</I></P>")
POSITIONS = {"Quaterback": "QB", "Runningback": "RB", "Wide Receiver": "WR", "Tight End": "TE",
             "Kicker": "PK", "Defense": "Def"}


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def pts(v, season):
    return f"{v:.0f}" if season < 2018 or v == int(v) else f"{v:.1f}"


def names(teams):
    """"A", "A, B", or "A, B, and C", as the page writes ties."""
    teams = sorted(set(teams))
    if len(teams) <= 2:
        return ", ".join(teams)
    return ", ".join(teams[:-1]) + ", and " + teams[-1]


def team_entries(season):
    reg = [g for g in d.season_games(season) if g["stage"] == "regular"]
    scores = [(s, t) for g in reg for t, s in ((g["team_a"], g["score_a"]), (g["team_b"], g["score_b"]))]
    st = d.standings(season)
    out = {}
    for cat, pick in (("Most Points Game.", max), ("Fewest Points Game.", min)):
        v = pick(s for s, _ in scores)
        out[cat] = (v, names(t for s, t in scores if s == v))
    for cat, key, pick in (("Most Points Season.", "pf", max), ("Fewest Points Season.", "pf", min),
                           ("Most Wins Season.", "w", max), ("Most Losses Season.", "l", max)):
        v = pick(r[key] for r in st)
        out[cat] = (v, names(r["team"] for r in st if r[key] == v))
    return out


def owner_of(rostered, played, week, pid):
    """Who had the player that week. A team out of the postseason has no lineup
    in its last weeks, so a player on its final roster is still its own. If the
    team played on without him, he had been dropped and was a free agent."""
    if (week, pid) in rostered:
        return rostered[(week, pid)]
    for w in range(week - 1, 0, -1):
        team = rostered.get((w, pid))
        if team:
            later = any((x, team) in played for x in range(w + 1, week + 1))
            return "Free Agent" if later else team
    return "Free Agent"


def player_entries(season):
    """Each position's best single game, every week of the season, every player."""
    players = json.load(open(f"{BASE}/player_index.json"))
    rostered, played = {}, set()
    for r in weekly.season(season):
        played.add((r["week"], r["team"]))
        for p in r["players"]:
            rostered[(r["week"], p["id"])] = r["team"]
    best = {}
    folder = f"{BASE}/mfl_archive/{season}/weeks"
    for name in sorted(os.listdir(folder)):
        if not name.startswith("player_scores_w"):
            continue
        week = int(name[-7:-5])
        for p in as_list(json.load(open(f"{folder}/{name}")).get("playerScores", {}).get("playerScore")):
            pos = players.get(p["id"], {}).get("position")
            if pos not in POSITIONS.values() or p.get("score") in (None, ""):
                continue
            v = float(p["score"])
            if pos not in best or v > best[pos][0]:
                best[pos] = (v, [])
            if v == best[pos][0]:
                best[pos][1].append((p["id"], week))
    out = {}
    for label, pos in POSITIONS.items():
        if pos not in best:
            continue
        v, who = best[pos]
        parts = []
        for pid, week in who:
            raw = players.get(pid, {}).get("name", pid)
            if pos == "Def":
                shown = raw.split(",")[0]                      # "Seahawks, Seattle" -> "Seahawks"
            else:
                last, _, first = raw.partition(", ")
                shown = f"{first} {last}".strip()
            parts.append(f"{shown} -- {owner_of(rostered, played, week, pid)}")
        out[f"Most Points Game: {label}."] = (v, ", ".join(parts))
    return out


def entries(first=FIRST_NEW):
    out = {}
    for y in range(first, LAST_SEASON):   # the season in progress waits until it is over
        e = team_entries(y)
        e.update(player_entries(y))
        out[y] = e
    return out


def apply(site, write):
    path = f"{site}/{PAGE}"
    html = open(path, encoding="latin-1").read()
    # add whatever seasons the page does not have yet, so each year's run adds one
    have = max(int(y) for y in re.findall(r"<B>(\d{4})</B>", html))
    first = max(FIRST_NEW, have + 1)
    if first >= LAST_SEASON:
        print(f"{PAGE} already runs to {have}: nothing to add until {LAST_SEASON} is over")
        return 0
    new = entries(first)
    adding_note = NOTE not in html
    changed = 0
    for cat in sorted({c for e in new.values() for c in e}):
        head = f"<h3>{cat}</h3></i>"
        if head not in html:
            print(f"  no category {cat!r} on the page")
            continue
        lines = "".join(f"\n<li><B>{y}</B> ({pts(new[y][cat][0], y)}) {new[y][cat][1]}"
                        for y in sorted(new, reverse=True) if cat in new[y])
        html = html.replace(head, head + lines, 1)
        changed += 1
    if adding_note:
        first_cat = html.find("<i><h3>")
        html = html[:first_cat] + NOTE + "\n" + html[first_cat:]
    for y in sorted(new):
        print(f"  {y}: " + "; ".join(f"{c.split('.')[0].replace('Most Points Game: ', '')} ({pts(v, y)}) {who}"
                                      for c, (v, who) in new[y].items()))
    print(f"{'updated' if write else 'would update'} {changed} categories with {len(new)} seasons")
    if write:
        open(path, "w", encoding="latin-1").write(html)
    return 0


POSITION_RELIABLE = 2008   # MFL's scoring follows the rule book from 2008 (docs/rulebook/mfl-check.md)
CORRECTED = ("<P><I>Corrected on 2026-10-29 to match the games: team records for every season, and a position's "
             "best game from 2008. Before 2008 the position records are as they were kept, since the archive's "
             "scoring for those seasons does not follow the rule book.</I></P>")


def correct(site, write):
    """Rewrite the entries the games contradict, from 2000 to the last kept season."""
    path = f"{site}/{PAGE}"
    html = open(path, encoding="latin-1").read()
    fixed = []
    for y in range(2000, FIRST_NEW):
        computed = team_entries(y)
        if y >= POSITION_RELIABLE:
            computed.update(player_entries(y))
        for cat, (v, who) in computed.items():
            head = f"<h3>{cat}</h3></i>"
            i = html.find(head)
            if i < 0:
                continue
            j = html.find("<h3>", i + len(head))
            seg = html[i:j if j > 0 else len(html)]
            m = re.search(rf"\n<li><B>{y}</B>\s*\((-?[\d.]+)\)[^\n]*", seg)
            if not m or round(float(m.group(1)), 1) == round(v, 1):
                continue
            line = f"\n<li><B>{y}</B> ({pts(v, y)}) {who}"
            fixed.append((y, cat, m.group(0).strip(), line.strip()))
            html = html[:i] + seg.replace(m.group(0), line, 1) + html[i + len(seg):]
    if fixed and CORRECTED not in html:
        first_cat = html.find("<i><h3>")
        html = html[:first_cat] + CORRECTED + "\n" + html[first_cat:]
    for y, cat, was, now in fixed:
        print(f"  {y} {cat}: {re.sub('<[^>]+>', '', was)}  ->  {re.sub('<[^>]+>', '', now)}")
    print(f"{'corrected' if write else 'would correct'} {len(fixed)} entries")
    if write:
        open(path, "w", encoding="latin-1").write(html)
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[2] in ("--correct-dry-run", "--correct"):
        sys.exit(correct(os.path.expanduser(sys.argv[1]), sys.argv[2] == "--correct"))
    if len(sys.argv) < 3 or sys.argv[2] not in ("--dry-run", "--apply"):
        print(__doc__)
        sys.exit(2)
    sys.exit(apply(os.path.expanduser(sys.argv[1]), sys.argv[2] == "--apply"))
