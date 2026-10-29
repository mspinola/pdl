"""Check the layered rule book against what MyFantasyLeague actually ran.

For every season from 2006, the rule book's facts (rules/amendments.json, as
applied by rulebook_build.py) are compared with the archived MFL data for that
season: the league settings (roster size, starters, injured reserve), the
scoring rules, and the schedule (regular-season length, playoff weeks, and how
the regular season splits between division and other opponents).

This is an independent test of the ledger: a rule change MFL shows but the
ledger lacks, or a ledger date MFL contradicts, shows up as a disagreement.

    python3 src/rulebook_mfl_check.py     # writes docs/rulebook/mfl-check.md

Not compared, and said so in the report: the yardage rates before 2010 (the
book's bonus table and MFL's tiers are not the same shape), defensive and
return scoring, and anything MFL does not record (fees, payouts, deadlines).
"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulebook_build as rb
import store, results

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POS = ["QB", "RB", "WR", "TE"]
EVENTS = {"passing": ("PS", "PY"), "rushing": ("RS", "RY"), "receiving": ("RC", "CY")}


def T(x):
    return x["$t"] if isinstance(x, dict) else x


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def scoring(season):
    """{(position, event): [(lo, hi, points)]} from MFL's rules."""
    rules = store.load(store.season(season, "rules")).get("rules", {})
    out = {}
    for group in as_list(rules.get("positionRules")):
        for pos in group["positions"].split("|"):
            for r in as_list(group.get("rule")):
                lo, hi = (int(v) for v in T(r["range"]).split("-"))
                out.setdefault((pos, T(r["event"])), []).append((lo, hi, T(r["points"])))
    return out


def per_yard(points):
    """MFL's points string as points per yard: '1/10', '.1/2', '*0.1'."""
    p = points.strip()
    if p.startswith("*"):
        return float(p[1:])
    if "/" in p:
        a, b = p.split("/")
        a, b = float(a or 0), float(b or 1)
        return a / b if b else 0.0
    return None


def observed(season, current):
    league = store.load(store.season(season, "league"))["league"]
    starters = {("K" if p["name"] == "PK" else p["name"]): int(p["limit"])
                for p in as_list(league.get("starters", {}).get("position"))}
    obs = {"roster_size": int(league["rosterSize"]), "starters": starters,
           "injured_reserve": int(league.get("injuredReserve") or 0)}

    sc = scoring(season)
    tds = {}
    for name, (td, _) in EVENTS.items():
        tds[name] = {p: [pts for lo, hi, pts in sorted(sc.get((p, td), []))] for p in POS}
        tds[name] = {p: [float(v) if "." in v else int(v) for v in vals] for p, vals in tds[name].items()}
    obs["touchdowns"] = tds

    yfrom, yper = {}, {}
    for name, (_, yd) in EVENTS.items():
        starts, rates = {}, set()
        for p in POS:
            rows = sorted(sc.get((p, yd), []))
            scoring_rows = [(lo, hi, pts) for lo, hi, pts in rows if pts not in ("0", "0/0")]
            starts[p] = scoring_rows[0][0] if scoring_rows else None
            if scoring_rows:
                rates.add(per_yard(scoring_rows[-1][2]))
        yfrom[name] = starts if name == "passing" else (starts["RB"] if len(set(starts.values())) == 1 else starts)
        yper[name] = rates.pop() if len(rates) == 1 else sorted(r for r in rates if r is not None)
    obs["yardage_from"], obs["yardage_per_yard"] = yfrom, yper

    obs["field_goals"] = [[lo, hi, int(pts)] for lo, hi, pts in sorted(sc.get(("PK", "FG"), []))]
    cc = [per_yard(pts) for p in POS for lo, hi, pts in sc.get((p, "CC"), [])]
    obs["receptions"] = cc[0] if cc and len(set(cc)) == 1 else (0 if not cc else sorted(set(cc)))

    # the regular season and playoffs
    if current:
        weeks = store.load(store.season(season, "schedule"))["schedule"]["weeklySchedule"]
        full = [int(w["week"]) for w in weeks if len(as_list(w.get("matchup"))) == 8]
        empty = [int(w["week"]) for w in weeks if not as_list(w.get("matchup"))]
        obs["regular_season_weeks"] = len(full)
        obs["playoff_weeks"] = empty
    else:
        g = [x for x in results.games() if x["season"] == season]
        obs["regular_season_weeks"] = len({x["week"] for x in g if x["stage"] == "regular"})
        obs["playoff_weeks"] = sorted({x["week"] for x in g if x["stage"] != "regular"})

    # how the regular season splits: own division, the other division in the
    # conference, and the other conference (MFL's AFC and NFC, the two that play
    # separate playoff brackets)
    names = {d["id"]: d["name"] for d in as_list(league.get("divisions", {}).get("division"))}
    divs = {f["name"]: names.get(f.get("division"), "") for f in as_list(league["franchises"]["franchise"])}
    per_team = {}
    reg = [] if current else [x for x in results.games() if x["season"] == season and x["stage"] == "regular"]
    for x in reg:
        a, b = x["team_a"], x["team_b"]
        if divs.get(a) and divs.get(b):
            for t, o in ((a, b), (b, a)):
                kind = 0 if divs[t] == divs[o] else 1 if divs[t].split()[0] == divs[o].split()[0] else 2
                per_team.setdefault(t, [0, 0, 0])[kind] += 1
    if per_team:
        obs["schedule"] = list(Counter(tuple(v) for v in per_team.values()).most_common(1)[0][0])
    return obs


def compare(facts, obs):
    rows = []
    for key in ("roster_size", "starters", "injured_reserve", "regular_season_weeks", "playoff_weeks",
                "schedule", "touchdowns", "yardage_from", "yardage_per_yard", "field_goals", "receptions"):
        want, got = facts.get(key), obs.get(key)
        if key == "yardage_per_yard" and want is None:
            rows.append((key, "not compared", "the book's yardage table is a bonus schedule before 2010"))
        elif got is None:
            rows.append((key, "not in MFL", "the season is not finished" if key == "schedule" else ""))
        elif want == got:
            rows.append((key, "agrees", ""))
        else:
            rows.append((key, "DIFFERS", f"book {json.dumps(want)}, MFL {json.dumps(got)}"))
    return rows


LABELS = {"roster_size": "roster size", "starters": "starting lineup", "injured_reserve": "injured reserve spots",
          "regular_season_weeks": "regular-season weeks", "playoff_weeks": "playoff weeks",
          "schedule": "schedule split (division, conference, other conference)", "touchdowns": "touchdown points", "yardage_from": "yardage scored from",
          "yardage_per_yard": "yardage rate", "field_goals": "field goals", "receptions": "receptions"}


def main():
    last = rb.latest_season()
    known = {(s, k["fact"]): k["why"] for k in rb.load("amendments.json").get("mfl_known_differences", [])
             for s in k["seasons"]}
    report, totals = [], Counter()
    for season in range(rb.FIRST, last + 1):
        facts = rb.book(season)["facts"]
        rows = compare(facts, observed(season, current=(season == last)))
        rows = [(k, "explained" if v == "DIFFERS" and (season, k) in known else v, d) for k, v, d in rows]
        for _, verdict, _ in rows:
            totals[verdict] += 1
        report.append((season, rows))

    lines = ["# The rule book against MyFantasyLeague", "",
             "Generated by `python3 src/rulebook_mfl_check.py`. For each season, the facts",
             "the layered rule book states are compared with what MFL's archived settings,",
             "scoring rules and schedule show for that season. Do not edit by hand.", "",
             f"{totals['agrees']} comparisons agree, {totals['explained']} differ for a known reason, {totals['DIFFERS']} differ unexplained, "
             f"{totals['not in MFL'] + totals['not compared']} could not be compared.", ""]
    differs = [(s, k, d) for s, rows in report for k, v, d in rows if v == "DIFFERS"]
    explained = [(s, k, d) for s, rows in report for k, v, d in rows if v == "explained"]
    if explained:
        lines += ["## Explained differences", "",
                  "These differ for a known reason, recorded in `rules/amendments.json`:", ""]
        for s, k, d in explained:
            lines.append(f"- **{s}, {LABELS[k]}**: {d}. {known[(s, k)]}")
        lines.append("")
    lines += ["## Disagreements", ""]
    if differs:
        lines += [f"- **{s}, {LABELS[k]}**: {d}" for s, k, d in differs]
    else:
        lines.append("None. Every fact MFL records matches the rule book in force that season.")
    lines += ["", "## By season", "", "| Season | " + " | ".join(LABELS[k] for k, _, _ in report[0][1]) + " |",
              "|---|" + "---|" * len(report[0][1])]
    mark = {"agrees": "yes", "DIFFERS": "**no**", "explained": "explained", "not in MFL": "-", "not compared": "-"}
    for s, rows in report:
        lines.append(f"| {s} | " + " | ".join(mark[v] for _, v, _ in rows) + " |")
    lines += ["", "A dash: not compared. The yardage rate is compared from 2010, when the book",
              "moves to a per-yard rate. The current season's schedule split waits for the",
              "season to finish. Not checked at all: defensive and return scoring, and what",
              "MFL does not record (fees, payouts, deadlines, draft order).", ""]
    out = f"{BASE}/docs/rulebook/mfl-check.md"
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"{totals['agrees']} agree, {totals['explained']} explained, {totals['DIFFERS']} differ, "
          f"{totals['not in MFL'] + totals['not compared']} not compared")
    for s, k, d in differs:
        print(f"  {s} {LABELS[k]}: {d}")
    print(f"wrote {os.path.relpath(out, BASE)}")
    return 1 if differs else 0


if __name__ == "__main__":
    sys.exit(main())
