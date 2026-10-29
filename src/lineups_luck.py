"""Lineup decisions and schedule luck.

Lineups, 2008 on (where MFL's lineups match the rule book): MFL records each
team's actual score and the best score its roster could have produced that week
under the lineup rules (opt_pts). The gap is points left on the bench. A
lineup loss is a game lost that the best lineup would have won against the
opponent's actual score.

Luck, every season from 2000 (games.json): each week, a team's score is set
against every other team's score that week. Its all-play rate is the share of
those it beat. Over a season that gives expected wins, what the team's scoring
was worth against an average schedule. Actual wins minus expected wins is luck:
who it happened to play, and when they had their good weeks.

    python3 src/lineups_luck.py

Writes datasets/lineup_owners.csv, lineup_losses.csv, luck_seasons.csv,
luck_owners.csv and docs/lineups-and-luck.md. Regular season only for luck and
for the lineup rates. Playoff lineup losses are listed separately.
"""
import csv, json, os, statistics, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_csv(name, header, rows):
    with open(f"{BASE}/datasets/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- lineups

def lineups():
    rows = [r for r in weekly.seasons() if r["optimal"] > 0]
    by_owner = defaultdict(lambda: {"games": 0, "score": 0.0, "optimal": 0.0, "perfect": 0,
                                    "lineup_losses": 0, "losses": 0, "playoff_lineup_losses": 0,
                                    "seasons": set(), "by_season": defaultdict(lambda: [0.0, 0.0, 0])})
    losses = []
    for r in rows:
        gap = max(0.0, r["optimal"] - r["score"])
        lost = r["opp_score"] is not None and r["score"] < r["opp_score"]
        saved = lost and r["optimal"] > r["opp_score"]
        if r["stage"] == "regular":
            o = by_owner[r["team"]]
            o["games"] += 1
            o["score"] += r["score"]
            o["optimal"] += r["optimal"]
            o["perfect"] += gap < 0.5
            o["losses"] += lost
            o["lineup_losses"] += saved
            o["seasons"].add(r["season"])
            bs = o["by_season"][r["season"]]
            bs[0] += r["score"]
            bs[1] += r["optimal"]
            bs[2] += 1
        elif r["stage"] == "playoffs" and saved:
            by_owner[r["team"]]["playoff_lineup_losses"] += 1
        if saved and r["stage"] in ("regular", "playoffs"):
            losses.append([r["season"], r["week"], r["stage"], r["team"], r["opponent"], r["score"],
                           r["optimal"], r["opp_score"], round(r["optimal"] - r["opp_score"], 1)])
    league = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r["stage"] == "regular":
            league[r["season"]][0] += r["score"]
            league[r["season"]][1] += r["optimal"]
    league_eff = {y: v[0] / v[1] for y, v in league.items()}
    owners = []
    for team, o in by_owner.items():
        if not o["games"]:
            continue
        # efficiency against the league that season, so owners from different eras compare
        rel = sum((sc / op - league_eff[y]) * n for y, (sc, op, n) in o["by_season"].items()) / o["games"]
        owners.append({
            "owner": team, "seasons": len(o["seasons"]), "games": o["games"],
            "efficiency": round(100 * o["score"] / o["optimal"], 1),
            "vs_league": round(100 * rel, 1),
            "bench_points_share": round(100 * (o["optimal"] - o["score"]) / o["optimal"], 1),
            "perfect_lineups": o["perfect"], "perfect_share": round(100 * o["perfect"] / o["games"], 1),
            "losses": o["losses"], "lineup_losses": o["lineup_losses"],
            "lineup_loss_share": round(100 * o["lineup_losses"] / o["losses"], 1) if o["losses"] else 0,
            "lineup_losses_per_season": round(o["lineup_losses"] / len(o["seasons"]), 2),
            "playoff_lineup_losses": o["playoff_lineup_losses"],
        })
    owners.sort(key=lambda r: -r["vs_league"])
    season_eff = {}
    for y in sorted({r["season"] for r in rows}):
        reg = [r for r in rows if r["season"] == y and r["stage"] == "regular"]
        season_eff[y] = round(100 * sum(r["score"] for r in reg) / sum(r["optimal"] for r in reg), 1)
    losses.sort(key=lambda x: (x[2] != "playoffs", -x[8]))
    return owners, losses, season_eff


# ---------------------------------------------------------------- luck

def luck():
    games = [g for g in json.load(open(f"{BASE}/games.json")) if g["stage"] == "regular"]
    week_scores = defaultdict(list)
    team_games = []
    for g in games:
        for t, s, o, os_, res in ((g["team_a"], g["score_a"], g["team_b"], g["score_b"], g["result_a"]),
                                  (g["team_b"], g["score_b"], g["team_a"], g["score_a"],
                                   {"W": "L", "L": "W", "T": "T"}[g["result_a"]])):
            week_scores[(g["season"], g["week"])].append((t, s))
            team_games.append((g["season"], g["week"], t, s, o, os_, res))
    seasons = defaultdict(lambda: {"games": 0, "wins": 0.0, "expected": 0.0, "points": 0.0, "against": 0.0,
                                   "league_avg": 0.0, "var": 0.0})
    for y, w, t, s, o, os_, res in team_games:
        others = [x for tt, x in week_scores[(y, w)] if tt != t]
        allplay = (sum(x < s for x in others) + 0.5 * sum(x == s for x in others)) / len(others)
        rec = seasons[(y, t)]
        rec["games"] += 1
        rec["wins"] += {"W": 1, "T": 0.5, "L": 0}[res]
        rec["expected"] += allplay
        rec["var"] += allplay * (1 - allplay)   # a game against a random opponent that week: win or not
        rec["points"] += s
        rec["against"] += os_
        rec["league_avg"] += statistics.mean(x for _, x in week_scores[(y, w)])
    out = []
    for (y, t), r in seasons.items():
        out.append({"season": y, "owner": t, "games": r["games"], "wins": r["wins"],
                    "expected_wins": round(r["expected"], 2), "luck": round(r["wins"] - r["expected"], 2),
                    "allplay_pct": round(r["expected"] / r["games"], 3),
                    "win_pct": round(r["wins"] / r["games"], 3),
                    # how hard the schedule was: opponents' points against the week's league average
                    "opponent_points_vs_average": round(100 * r["against"] / r["league_avg"] - 100, 1),
                    "in_progress": y == LAST_SEASON, "_var": r["var"]})
    out.sort(key=lambda r: (r["season"], r["owner"]))
    var_of = {(r["season"], r["owner"]): r.pop("_var") for r in out}
    for r in out:
        r["_var"] = var_of[(r["season"], r["owner"])]
    owners = defaultdict(lambda: {"seasons": 0, "games": 0, "wins": 0.0, "expected": 0.0, "var": 0.0})
    for r in out:
        if r["in_progress"]:
            continue
        o = owners[r["owner"]]
        o["seasons"] += 1
        o["games"] += r["games"]
        o["wins"] += r["wins"]
        o["expected"] += r["expected_wins"]
        o["var"] += r["_var"]
    career = [{"owner": t, "seasons": o["seasons"], "games": o["games"], "wins": o["wins"],
               "expected_wins": round(o["expected"], 1), "luck": round(o["wins"] - o["expected"], 1),
               "luck_per_season": round((o["wins"] - o["expected"]) / o["seasons"], 2),
               # luck in standard deviations of what chance alone gives
               "luck_z": round((o["wins"] - o["expected"]) / o["var"] ** 0.5, 2),
               "allplay_pct": round(o["expected"] / o["games"], 3), "win_pct": round(o["wins"] / o["games"], 3)}
              for t, o in owners.items()]
    career.sort(key=lambda r: -r["luck"])
    return out, career


def champions():
    out = {}
    with open(f"{BASE}/datasets/champions.csv") as f:
        for r in csv.DictReader(f):
            out[int(r["season"])] = r.get("champion") or r.get("owner")
    return out


def main():
    owners, losses, season_eff = lineups()
    cols = list(owners[0])
    write_csv("lineup_owners.csv", cols, [[r[c] for c in cols] for r in owners])
    write_csv("lineup_losses.csv", ["season", "week", "stage", "team", "opponent", "score", "best_possible",
                                    "opponent_score", "best_lineup_margin"], losses)
    seasons, career = luck()
    cols = [c for c in seasons[0] if not c.startswith("_")]
    write_csv("luck_seasons.csv", cols, [[r[c] for c in cols] for r in seasons])
    cols = list(career[0])
    write_csv("luck_owners.csv", cols, [[r[c] for c in cols] for r in career])
    report(owners, losses, season_eff, seasons, career, champions())
    print(f"lineups: {len(owners)} owners, {len(losses)} games lost to the lineup "
          f"({sum(1 for l in losses if l[2] == 'playoffs')} in the playoffs)")
    print(f"luck: {len(seasons)} team-seasons, {len(career)} owners")
    print("wrote datasets/lineup_owners.csv, lineup_losses.csv, luck_seasons.csv, luck_owners.csv, docs/lineups-and-luck.md")
    return 0


def report(owners, losses, season_eff, seasons, career, champs):
    L = ["# Lineup decisions and schedule luck", "",
         "Generated by `python3 src/lineups_luck.py`. Owners are reported by team.", ""]
    reg_losses = [l for l in losses if l[2] == "regular"]
    total_losses = sum(o["losses"] for o in owners)
    L += ["## Lineups (2008 on)", "",
          f"Across {sum(o['games'] for o in owners):,} regular-season team-games, owners started "
          f"{statistics.mean(o['efficiency'] for o in owners):.1f}% of the points their rosters could have scored. "
          f"{len(reg_losses)} of {total_losses:,} regular-season losses ({100 * len(reg_losses) / total_losses:.0f}%) "
          f"were games the best lineup would have won, and so were "
          f"{sum(1 for l in losses if l[2] == 'playoffs')} playoff losses.", "",
          "Efficiency is the share of the best possible score a team actually started. League efficiency rose by "
          "about 4 points with the 2018 scoring change, so owners are ranked by efficiency against the league in "
          "the same seasons (\"vs league\"), which puts Bunchalosers (to 2017) and Couchfire (from 2018) on the "
          "same footing as everyone else. A lineup loss is a loss that the best lineup would have won against the "
          "opponent's actual score.", "",
          "| | Owner | Efficiency | Vs league | Perfect lineups | Lineup losses | Share of losses | Per season | In the playoffs |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, o in enumerate(owners, 1):
        L.append(f"| {i} | {o['owner']} | {o['efficiency']}% | {o['vs_league']:+} | {o['perfect_share']}% | {o['lineup_losses']} | "
                 f"{o['lineup_loss_share']}% | {o['lineup_losses_per_season']} | {o['playoff_lineup_losses']} |")
    L += ["", "League efficiency by season: " + ", ".join(f"{y} {e}%" for y, e in season_eff.items()) + ".", "",
          "### Playoff games lost to the lineup", "",
          "| Season | Week | Team | Opponent | Scored | Best possible | Opponent scored |", "|---|---|---|---|---|---|---|"]
    for l in [x for x in losses if x[2] == "playoffs"]:
        L.append(f"| {l[0]} | {l[1]} | {l[3]} | {l[4]} | {l[5]:g} | {l[6]:g} | {l[7]:g} |")
    L += ["", "### The costliest regular-season benchings", "",
          "Losses where the best lineup would have won by the most.", "",
          "| Season | Week | Team | Opponent | Scored | Best possible | Opponent scored |", "|---|---|---|---|---|---|---|"]
    for l in reg_losses[:10]:
        L.append(f"| {l[0]} | {l[1]} | {l[3]} | {l[4]} | {l[5]:g} | {l[6]:g} | {l[7]:g} |")

    done = [s for s in seasons if not s["in_progress"]]
    L += ["", "## Schedule luck (2000 on)", "",
          "Expected wins are what a team's weekly scores were worth against everyone that week, not just the "
          "opponent it drew. Luck is actual wins minus expected wins. Over a 13 or 14 game season, plus or minus "
          "one win is ordinary, and two or more is a lot.", "",
          f"Across {len(done)} completed team-seasons, all-play rate and actual win rate correlate at "
          f"r = {statistics.correlation([s['allplay_pct'] for s in done], [s['win_pct'] for s in done]):.2f}: "
          "scoring decides most of the standings, and the schedule the rest.", "",
          "### Career", "",
          "The last column is luck in standard deviations of what chance alone produces over that many games. "
          "Within plus or minus 2 is ordinary. With 17 owners, one owner near 2 is expected by chance.", "",
          "| | Owner | Seasons | Wins | Expected | Luck | Per season | Standard deviations |", "|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(career, 1):
        L.append(f"| {i} | {c['owner']} | {c['seasons']} | {c['wins']:g} | {c['expected_wins']} | {c['luck']:+} | "
                 f"{c['luck_per_season']:+} | {c['luck_z']:+} |")
    ranked = sorted(done, key=lambda s: -s["luck"])
    L += ["", "### Luckiest seasons", "", "| Season | Owner | Record | Expected wins | Luck | Champion? |", "|---|---|---|---|---|---|"]
    for s in ranked[:10]:
        L.append(f"| {s['season']} | {s['owner']} | {s['wins']:g}-{s['games'] - s['wins']:g} | {s['expected_wins']} | "
                 f"{s['luck']:+} | {'yes' if champs.get(s['season']) == s['owner'] else ''} |")
    L += ["", "### Unluckiest seasons", "", "| Season | Owner | Record | Expected wins | Luck |", "|---|---|---|---|---|"]
    for s in ranked[::-1][:10]:
        L.append(f"| {s['season']} | {s['owner']} | {s['wins']:g}-{s['games'] - s['wins']:g} | {s['expected_wins']} | {s['luck']:+} |")
    champ_luck = [s for s in done if champs.get(s["season"]) == s["owner"]]
    if champ_luck:
        L += ["", "### Champions", "",
              f"The {len(champ_luck)} champions averaged {statistics.mean(s['luck'] for s in champ_luck):+.2f} wins of luck "
              f"in their title seasons, and an all-play rate of {statistics.mean(s['allplay_pct'] for s in champ_luck):.3f}: "
              "they were mostly the best-scoring teams.", "",
              "| Season | Champion | Record | Expected wins | Luck | All-play |", "|---|---|---|---|---|---|"]
        for s in sorted(champ_luck, key=lambda s: s["season"]):
            L.append(f"| {s['season']} | {s['owner']} | {s['wins']:g}-{s['games'] - s['wins']:g} | {s['expected_wins']} | "
                     f"{s['luck']:+} | {s['allplay_pct']:.3f} |")
    L += ["", "## Notes", "",
          "- Lineups start in 2008: MFL's 2003 to 2007 scoring setup does not match the rule book.",
          "- The best lineup is MFL's own calculation under the starting rules of the time.",
          "- A lineup loss assumes the opponent's lineup as it was. Both teams could have done better.",
          "- Luck uses regular-season games only, and leaves out the season in progress.", ""]
    with open(f"{BASE}/docs/lineups-and-luck.md", "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
