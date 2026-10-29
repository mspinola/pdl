"""Draft value: what each pick gave the team that made it, 2008 on.

The annual draft is for rookies and free agents (rule book 3.1). In a dynasty
league a pick pays over years, so each pick is judged over three seasons: the
draft season and the two after it, for the team that drafted the player.

- starts: regular-season starts for the drafting team in those seasons, and
  starts_any_team for any team. A pick is judged on whether it became a
  starter, whoever started him, because in a dynasty league a drafted player is
  also currency: the Moose took DK Metcalf 7th in 2019, started him twice, and
  traded him in a three-for-three deal, after which he started 33 times.
- a hit: 10 or more starts for any team in the three seasons. Kept: 10 or more
  for the drafting team, so whether the drafter got the starts himself.
- value: points above the average starter at the player's position, in that
  season's average starts (weekly.over_average), summed over the starts, for
  any team (value_any_team) and for the drafting team (value)

Each pick is also set against what that slot usually yields: the average over
every draft of the picks within two places of it, overall. An owner's draft
skill is his picks' average starts above their slot's expectation, using only
drafts whose three seasons are complete.

    python3 src/draft_value.py      # datasets/draft_value.csv, draft_owners.csv, docs/draft-value.md
"""
import csv, json, os, statistics, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HORIZON = 3
HIT = 10


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def picks():
    slots = I.slot_index()
    names = json.load(open(f"{BASE}/player_index.json"))
    out = []
    for y in range(2008, LAST_SEASON + 1):
        p = f"{BASE}/mfl_archive/{y}/draft_results.json"
        if not os.path.exists(p):
            continue
        # skip unmade picks and the ones the commissioner skipped (no round, player "----")
        dp = [x for x in as_list(json.load(open(p)).get("draftResults", {}).get("draftUnit", {}).get("draftPick"))
              if x.get("player") and x.get("round") and x["player"].strip("-")]
        dp.sort(key=lambda x: (int(x["round"]), int(x["pick"])))
        for overall, x in enumerate(dp, 1):
            team = slots.get((y, x["franchise"]))
            if not team:
                continue
            out.append({"season": y, "round": int(x["round"]), "pick": int(x["pick"]), "overall": overall,
                        "team": I.label_for(team, y), "player_id": x["player"],
                        "player": names.get(x["player"], {}).get("name", x["player"]),
                        "position": weekly.positions().get(x["player"])})
    return out


def main():
    rows = weekly.seasons()
    averages = weekly.starter_averages(rows)
    starts = defaultdict(list)   # (team, player) -> [(season, over_average)]
    anywhere = defaultdict(list)  # player -> [(season, over_average)], starts for any team
    for r in rows:
        if r["stage"] != "regular":
            continue
        for p in r["players"]:
            if p["started"]:
                starts[(r["team"], p["id"])].append(
                    (r["season"], weekly.over_average(p["score"], r["season"], weekly.positions().get(p["id"]), averages)))
                anywhere[p["id"]].append(
                    (r["season"], weekly.over_average(p["score"], r["season"], weekly.positions().get(p["id"]), averages)))
    out = picks()
    for p in out:
        window = [v for y, v in starts.get((p["team"], p["player_id"]), []) if p["season"] <= y < p["season"] + HORIZON]
        p["starts"] = len(window)
        # starts for any team: did he pick a player who became a starter, whoever started him
        anyw = [v for y, v in anywhere.get(p["player_id"], []) if p["season"] <= y < p["season"] + HORIZON]
        p["starts_any_team"] = len(anyw)
        p["value_any_team"] = round(sum(anyw), 1)
        p["value"] = round(sum(window), 1)
        p["hit"] = p["starts_any_team"] >= HIT
        p["kept"] = len(window) >= HIT
        p["complete"] = p["season"] + HORIZON - 1 < LAST_SEASON
    done = [p for p in out if p["complete"]]
    by_overall, any_overall = defaultdict(list), defaultdict(list)
    for p in done:
        by_overall[p["overall"]].append(p["starts"])
        any_overall[p["overall"]].append(p["starts_any_team"])
    for p in out:
        near = [s for o in range(p["overall"] - 2, p["overall"] + 3) for s in by_overall.get(o, [])]
        p["expected_starts"] = round(statistics.mean(near), 1) if near else None
        p["starts_over_slot"] = round(p["starts"] - p["expected_starts"], 1) if near else None
        near_any = [s for o in range(p["overall"] - 2, p["overall"] + 3) for s in any_overall.get(o, [])]
        p["any_team_over_slot"] = round(p["starts_any_team"] - statistics.mean(near_any), 1) if near_any else None

    cols = ["season", "round", "pick", "overall", "team", "player", "position", "starts_any_team", "starts",
            "hit", "kept", "value_any_team", "value", "any_team_over_slot", "expected_starts", "starts_over_slot",
            "complete"]
    with open(f"{BASE}/datasets/draft_value.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows([[p[c] for c in cols] for p in out])

    owners = defaultdict(list)
    for p in done:
        owners[p["team"]].append(p)
    orows = []
    for team, ps in owners.items():
        orows.append({"owner": team, "picks": len(ps), "drafts": len({p["season"] for p in ps}),
                      "hit_rate": round(100 * sum(p["hit"] for p in ps) / len(ps), 1),
                      "kept_rate": round(100 * sum(p["kept"] for p in ps) / len(ps), 1),
                      "starts_per_pick": round(statistics.mean(p["starts"] for p in ps), 2),
                      "starts_over_slot": round(statistics.mean(p["starts_over_slot"] for p in ps), 2),
                      # two standard errors: an owner's figure is unlikely to be chance only beyond this
                      "margin": round(2 * statistics.stdev(p["starts_over_slot"] for p in ps) / len(ps) ** 0.5, 2),
                      "first_round_hit_rate": round(100 * statistics.mean(p["hit"] for p in ps if p["round"] == 1), 1)
                      if any(p["round"] == 1 for p in ps) else None,
                      "value_per_pick": round(statistics.mean(p["value_any_team"] for p in ps), 2),
                      "any_team_over_slot": round(statistics.mean(p["any_team_over_slot"] for p in ps), 2),
                      "any_team_margin": round(2 * statistics.stdev(p["any_team_over_slot"] for p in ps) / len(ps) ** 0.5, 2),
                      # of the starts his draftees made in the three seasons, the share made for other teams
                      "started_elsewhere": round(100 * (1 - sum(p["starts"] for p in ps) /
                                                        max(1, sum(p["starts_any_team"] for p in ps))), 1)})
    orows.sort(key=lambda r: -r["any_team_over_slot"])
    cols = list(orows[0])
    with open(f"{BASE}/datasets/draft_owners.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows([[r[c] for c in cols] for r in orows])
    report(out, done, orows)
    print(f"{len(out):,} picks 2008 to {LAST_SEASON}, {len(done):,} with all {HORIZON} seasons played")
    print("wrote datasets/draft_value.csv, draft_owners.csv and docs/draft-value.md")
    return 0


def report(out, done, orows):
    def rate(ps, key="hit"):
        return f"{100 * sum(p[key] for p in ps) / len(ps):.0f}%" if ps else "-"
    L = ["# Draft value", "",
         f"Generated by `python3 src/draft_value.py`. Every pick from 2008, judged over {HORIZON} seasons: the draft "
         "season and the two after.", "",
         f"A pick is a **hit** if the player made {HIT} or more regular-season starts in those seasons for any team. "
         "In a dynasty league a drafted player is also currency: the Moose took DK Metcalf 7th overall in 2019, "
         "started him twice, and traded him that October with two others for three players, after which he started "
         "33 times. That pick worked, and a measure that counts only the drafting team's starts would call it a bust. "
         f"So the drafting team's starts are a second measure, **kept**: {HIT} or more starts for the team that made "
         "the pick. Value is points above the average starter at the player's position that season, counted in that "
         f"season's average starts. Owner figures use drafts with all {HORIZON} seasons played "
         f"(2008 to {LAST_SEASON - HORIZON}).", ""]
    rounds = defaultdict(list)
    for p in done:
        rounds[p["round"]].append(p)
    L += ["## By round", "",
          "Kickers and defenses are split out: they start every week once drafted, so they make the middle rounds "
          "look better than they are for everyone else.", "",
          "| Round | Picks | Hit rate | Skill positions | Kickers and defenses (share of picks) | Kept | Starts per pick | Never started anywhere |",
          "|---|---|---|---|---|---|---|---|"]
    for rd in sorted(rounds):
        ps = rounds[rd]
        kd = [p for p in ps if p["position"] in ("K", "Def")]
        sk = [p for p in ps if p["position"] not in ("K", "Def")]
        L.append(f"| {rd} | {len(ps)} | {rate(ps)} | {rate(sk)} | {rate(kd)} ({100 * len(kd) / len(ps):.0f}%) | "
                 f"{rate(ps, 'kept')} | {statistics.mean(p['starts_any_team'] for p in ps):.1f} | "
                 f"{100 * sum(p['starts_any_team'] == 0 for p in ps) / len(ps):.0f}% |")
    first = [p for p in done if p["round"] == 1]
    tops = defaultdict(list)
    for p in first:
        tops[min(p["pick"], 17)].append(p)
    L += ["", "## The first round, pick by pick", "",
          "| Pick | Drafts | Hit rate | Kept | Starts per pick |", "|---|---|---|---|---|"]
    for k in sorted(tops):
        ps = tops[k]
        L.append(f"| {k}{' (the toilet bowl pick, from the 2023 draft)' if k == 17 else ''} | {len(ps)} | "
                 f"{rate(ps)} | {rate(ps, 'kept')} | {statistics.mean(p['starts_any_team'] for p in ps):.1f} |")
    p17 = [p for p in out if p["round"] == 1 and p["pick"] == 17]
    if p17:
        L += ["", "Every pick 17 so far, including drafts still inside their three seasons:", ""]
        L += [f"- {p['season']}: {p['team']} took {p['player']} ({p['position']}), {p['starts_any_team']} starts so far" for p in p17]
    L += ["", "## Owners", "",
          "Over slot is the average number of starts a pick gave above what picks at that point in the draft usually "
          "give, so an owner is not rewarded for drafting early. The first is for any team (did he pick players who "
          "became starters), the second for his own team (did he keep them). The margin is two standard errors on the "
          "first: inside it, a figure is indistinguishable from an average drafter. With 17 owners, about one lands "
          "outside it by chance alone. Started elsewhere is the share of his draftees' starts made for other teams.", "",
          "| | Owner | Picks | Hit rate | Kept | First-round hit rate | Over slot, any team | Margin | Over slot, his team | Started elsewhere |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(orows, 1):
        flag = " (outside)" if abs(r["any_team_over_slot"]) > r["any_team_margin"] else ""
        L.append(f"| {i} | {r['owner']} | {r['picks']} | {r['hit_rate']}% | {r['kept_rate']}% | "
                 f"{r['first_round_hit_rate']}% | {r['any_team_over_slot']:+}{flag} | {r['any_team_margin']} | "
                 f"{r['starts_over_slot']:+} | {r['started_elsewhere']}% |")
    best = sorted(out, key=lambda p: -p["value_any_team"])
    L += ["", "## Best picks", "", "By value over the three seasons, for whichever teams started him (or so far, "
          "for recent drafts).", "",
          "| Season | Round | Pick | Team | Player | Pos | Starts | For the drafting team | Value |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in best[:15]:
        L.append(f"| {p['season']} | {p['round']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | "
                 f"{p['starts_any_team']} | {p['starts']} | {p['value_any_team']:+} |")
    steals = sorted([p for p in done if p["round"] >= 3], key=lambda p: -p["value_any_team"])
    L += ["", "## Best late picks (round 3 on)", "",
          "| Season | Round | Pick | Team | Player | Pos | Starts | For the drafting team | Value |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in steals[:10]:
        L.append(f"| {p['season']} | {p['round']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | "
                 f"{p['starts_any_team']} | {p['starts']} | {p['value_any_team']:+} |")
    busts = sorted([p for p in first if p["pick"] <= 8], key=lambda p: (p["starts_any_team"], p["value_any_team"]))
    L += ["", "## Top-8 picks that never paid", "",
          "First-round picks in the top 8 with the fewest starts for anyone in their three seasons.", "",
          "| Season | Pick | Team | Player | Pos | Starts |", "|---|---|---|---|---|---|"]
    for p in busts[:10]:
        L.append(f"| {p['season']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | {p['starts_any_team']} |")
    traded = sorted([p for p in done if p["hit"] and not p["kept"]], key=lambda p: -p["starts_any_team"])
    L += ["", "## Hits that started elsewhere", "",
          "Picks that became starters, but mostly for other teams: traded, dropped, or kept on the bench.", "",
          "| Season | Round | Pick | Drafted by | Player | Pos | Starts | For the drafting team |", "|---|---|---|---|---|---|---|---|"]
    for p in traded[:10]:
        L.append(f"| {p['season']} | {p['round']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | "
                 f"{p['starts_any_team']} | {p['starts']} |")
    L += ["", "## Notes", "",
          "- From 2008, where MFL kept the draft and the lineups.",
          "- A dynasty pick can pay later than three seasons. The horizon is a choice, and the CSV has every pick "
          "for a longer view.", ""]
    with open(f"{BASE}/docs/draft-value.md", "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
