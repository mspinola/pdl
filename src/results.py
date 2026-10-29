"""Build the game-by-game record and the champions list.

Games come from MyFantasyLeague's weekly schedule, 2003 to 2026. Each season's
`lastRegularSeasonWeek` (from its league record) separates the regular season
from the postseason. Unplayed fixtures, which the current season still has, are
dropped: a game counts only when both sides carry a result.

Champions come from two places. MyFantasyLeague exposes three playoff brackets
per season; bracket 3 is the final, its two entrants being the winners of
brackets 1 and 2. The league's own archive also lists champions by hand for
2000 to 2019, which is used both to cover the pre-MFL seasons and to check the
bracket reading over the years they share.
"""
import json, os, re, sys, html, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store
import identities as I
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{BASE}/raw"
MFL_YEARS = list(range(2003, LAST_SEASON + 1))


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def played(fr):
    """Whether a matchup was actually played.

    MFL fills a future fixture in with result "T" and no score, so the result
    field alone counts 56 unplayed 2026 games as ties. A played game has a
    score on both sides and at least one of them above zero; a real 0-0 tie
    does not happen in this scoring.
    """
    if len(fr) != 2:
        return False
    if not all(f.get("result") in ("W", "L", "T") for f in fr):
        return False
    scores = []
    for f in fr:
        raw = f.get("score")
        if raw is None or str(raw).strip() == "":
            return False
        try:
            scores.append(float(raw))
        except ValueError:
            return False
    return sum(scores) > 0


def bracket_weeks(year):
    """The weeks the playoff brackets occupy, where MFL has them."""
    weeks = set()
    for b in (1, 2, 3):
        path = store.bracket(year, b)
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        if "error" in d or "playoffBracket" not in d:
            continue
        for rnd in as_list(d["playoffBracket"].get("playoffRound")):
            if rnd.get("week"):
                weeks.add(int(rnd["week"]))
    return weeks


def played_per_week(year):
    out = {}
    for wk in as_list(store.load(store.season(year, "schedule"))
                      .get("schedule", {}).get("weeklySchedule")):
        try:
            week = int(wk.get("week"))
        except (TypeError, ValueError):
            continue
        n = 0
        for mu in as_list(wk.get("matchup")):
            fr = as_list(mu.get("franchise"))
            if played(fr):
                n += 1
        out[week] = n
    return out


def postseason_weeks(year):
    """Which weeks are postseason.

    `lastRegularSeasonWeek` on the league record is not maintained: it reads 16
    in seasons that plainly had three playoff rounds, and 13, 14 or 15 in
    others. So it is not used. The playoff brackets name their weeks directly
    wherever MFL has them (2008 on). For 2003 to 2007, which have no brackets,
    the bracket ladder shows up as weeks that carry fewer games than a full
    slate: 4, then 2, then 1.
    """
    brackets = bracket_weeks(year)
    if brackets:
        return brackets
    per = played_per_week(year)
    if not per:
        return set()
    full = max(per.values())
    return {w for w, n in per.items() if 0 < n < full}


def games():
    slots = I.slot_index()
    out = []
    for year in MFL_YEARS:
        path = store.season(year, "schedule")
        if not os.path.exists(path):
            continue
        post = postseason_weeks(year)
        for wk in as_list(store.load(path).get("schedule", {}).get("weeklySchedule")):
            try:
                week = int(wk.get("week"))
            except (TypeError, ValueError):
                continue
            for mu in as_list(wk.get("matchup")):
                fr = as_list(mu.get("franchise"))
                if not played(fr):
                    continue
                a, b = fr
                la = slots.get((year, a["id"]))
                lb = slots.get((year, b["id"]))
                if la is None or lb is None:
                    continue
                out.append({
                    "season": year,
                    "week": week,
                    "stage": "postseason" if week in post else "regular",
                    "team_a": I.label_for(la, year),
                    "team_b": I.label_for(lb, year),
                    "score_a": float(a.get("score") or 0),
                    "score_b": float(b.get("score") or 0),
                    "result_a": a["result"],
                    "source": "mfl",
                })
    return out


def bracket_champion(year):
    """The winner of bracket 3, which is the final."""
    path = store.bracket(year, 3)
    if not os.path.exists(path):
        return None
    d = store.load(path)
    if "error" in d or "playoffBracket" not in d:
        return None
    rounds = as_list(d["playoffBracket"].get("playoffRound"))
    if not rounds:
        return None
    gms = as_list(rounds[-1].get("playoffGame"))
    if not gms:
        return None
    g = gms[-1]
    home, away = g.get("home") or {}, g.get("away") or {}
    if not home.get("franchise_id") or not away.get("franchise_id"):
        return None
    try:
        hp, ap = float(home.get("points") or 0), float(away.get("points") or 0)
    except ValueError:
        return None
    if hp == ap:
        return None
    win = home if hp > ap else away
    slots = I.slot_index()
    label = slots.get((year, win["franchise_id"]))
    return I.label_for(label, year) if label else None


ARCHIVE_CHAMPS_URL = "pdl/history/misc.html"


def archive_champions():
    """The hand-kept champions list, 2000 onward.

    Only the champion table is read. That page also lists owners by name, which
    is deliberately not parsed: this data feeds a public page.
    """
    archived = store.legacy("champions")
    path = archived or f"{RAW}/archive_history.html"
    if not os.path.exists(path):
        import urllib.request
        url = f"https://mspinola.github.io/mspinola/{ARCHIVE_CHAMPS_URL}"
        req = urllib.request.Request(url, headers={"User-Agent": "PDL league analytics"})
        with urllib.request.urlopen(req, timeout=60) as r:
            open(path, "w", encoding="utf-8").write(r.read().decode("utf-8", "replace"))
    body = open(path, encoding="utf-8", errors="replace").read()
    txt = html.unescape(re.sub(r"<[^>]+>", "|", body))
    lines = [re.sub(r"\s+", " ", re.sub(r"\|+", "|", l)).strip(" |") for l in txt.split("\n")]

    # take only the block under "PDL Champion", stopping at the next heading
    champs, inside = {}, False
    alias = {"oakaldoakal": "OakalDoakals", "oakaldokal": "OakalDoakals",
             "f-jacki": "F-Jackie", "ic pounders": "Iron City Pounders",
             "boozers": "Scooter's Boozers"}
    known = set(I.build())
    for line in lines:
        if re.match(r"^PDL Champion", line, re.I):
            inside = True
            continue
        if inside and re.match(r"^PDL \w", line) and not re.match(r"^PDL Champion", line, re.I):
            break
        if not inside:
            continue
        m = re.match(r"^(\d{4})\s*\|\s*(.+?)\s*$", line)
        if not m:
            continue
        year, name = int(m.group(1)), m.group(2).strip()
        name = alias.get(name.lower(), name)
        if name in known:
            champs[year] = name
    return champs


def champions():
    """Merged champions: the archive where it has a year, MFL brackets after."""
    arc = archive_champions()
    out = {}
    for year in range(I.LEAGUE_START, I.LEAGUE_END + 1):
        if year in arc:
            out[year] = {"season": year, "champion": arc[year], "source": "archive"}
        else:
            c = bracket_champion(year)
            if c:
                out[year] = {"season": year, "champion": c, "source": "mfl"}
    return out


if __name__ == "__main__":
    g = games()
    json.dump(g, open(f"{BASE}/games.json", "w"))
    seasons = sorted({x["season"] for x in g})
    print(f"{len(g)} games, seasons {min(seasons)}-{max(seasons)}")
    print(f"  regular {sum(1 for x in g if x['stage'] == 'regular')}, "
          f"postseason {sum(1 for x in g if x['stage'] == 'postseason')}")
    print("\n  per season (regular + postseason), and the record check:")
    bad = []
    for y in seasons:
        rs = [x for x in g if x["season"] == y and x["stage"] == "regular"]
        ps = [x for x in g if x["season"] == y and x["stage"] == "postseason"]
        rec = collections.Counter()
        for x in rs:
            rec[x["team_a"]] += 1
            rec[x["team_b"]] += 1
        played = sorted(set(rec.values()))
        wins = sum(1 for x in rs if x["result_a"] == "W")
        losses = sum(1 for x in rs if x["result_a"] == "L")
        ties = sum(1 for x in rs if x["result_a"] == "T")
        ok = len(played) == 1 and wins + losses + ties == len(rs)
        if not ok:
            bad.append(y)
        print(f"    {y}: {len(rs):3d} regular + {len(ps):2d} postseason, "
              f"each team played {played}, {'ok' if ok else 'UNEVEN'}")
    print(f"  seasons where teams played an uneven number of regular games: {bad or 'none'}")

    arc = archive_champions()
    print(f"\narchive champions: {len(arc)} seasons {min(arc)}-{max(arc)}")
    agree = dis = miss = 0
    print("\n  cross-check of the bracket reading against the hand-kept list:")
    for y in sorted(arc):
        b = bracket_champion(y)
        if b is None:
            miss += 1
            continue
        if b == arc[y]:
            agree += 1
        else:
            dis += 1
            print(f"    {y}: archive says {arc[y]}, bracket says {b}")
    print(f"    agree {agree}, disagree {dis}, no bracket {miss}")

    ch = champions()
    json.dump(ch, open(f"{BASE}/champions.json", "w"), indent=1)
    print(f"\nchampions on record: {len(ch)}")
    tally = collections.Counter(v["champion"] for v in ch.values())
    for name, n in tally.most_common():
        yrs = ",".join(str(k) for k, v in sorted(ch.items()) if v["champion"] == name)
        print(f"  {n}x {name:<22} {yrs}")
    gap = [y for y in range(I.LEAGUE_START, I.LEAGUE_END + 1) if y not in ch]
    print(f"\n  seasons with no champion recorded: {gap}")
