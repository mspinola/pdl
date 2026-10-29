"""Draft value: what each pick gave the team that made it, 2008 on.

The annual draft is for rookies and free agents (rule book 3.1). In a dynasty
league a pick pays over years, so each pick is judged over three seasons: the
draft season and the two after it, for the team that drafted the player.

- starts: regular-season starts for the drafting team in those seasons
- value: points above the average starter at the player's position, in that
  season's average starts (weekly.over_average), summed over those starts
- a hit: 10 or more starts in the three seasons

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
    for r in rows:
        if r["stage"] != "regular":
            continue
        for p in r["players"]:
            if p["started"]:
                starts[(r["team"], p["id"])].append(
                    (r["season"], weekly.over_average(p["score"], r["season"], weekly.positions().get(p["id"]), averages)))
    out = picks()
    for p in out:
        window = [v for y, v in starts.get((p["team"], p["player_id"]), []) if p["season"] <= y < p["season"] + HORIZON]
        p["starts"] = len(window)
        p["value"] = round(sum(window), 1)
        p["hit"] = len(window) >= HIT
        p["complete"] = p["season"] + HORIZON - 1 < LAST_SEASON
    done = [p for p in out if p["complete"]]
    by_overall = defaultdict(list)
    for p in done:
        by_overall[p["overall"]].append(p["starts"])
    for p in out:
        near = [s for o in range(p["overall"] - 2, p["overall"] + 3) for s in by_overall.get(o, [])]
        p["expected_starts"] = round(statistics.mean(near), 1) if near else None
        p["starts_over_slot"] = round(p["starts"] - p["expected_starts"], 1) if near else None

    cols = ["season", "round", "pick", "overall", "team", "player", "position", "starts", "value", "hit",
            "expected_starts", "starts_over_slot", "complete"]
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
                      "starts_per_pick": round(statistics.mean(p["starts"] for p in ps), 2),
                      "starts_over_slot": round(statistics.mean(p["starts_over_slot"] for p in ps), 2),
                      # two standard errors: an owner's figure is unlikely to be chance only beyond this
                      "margin": round(2 * statistics.stdev(p["starts_over_slot"] for p in ps) / len(ps) ** 0.5, 2),
                      "first_round_hit_rate": round(100 * statistics.mean(p["hit"] for p in ps if p["round"] == 1), 1)
                      if any(p["round"] == 1 for p in ps) else None,
                      "value_per_pick": round(statistics.mean(p["value"] for p in ps), 2)})
    orows.sort(key=lambda r: -r["starts_over_slot"])
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
    L = ["# Draft value", "",
         f"Generated by `python3 src/draft_value.py`. Every pick from 2008, judged over {HORIZON} seasons (the draft "
         "season and the two after) for the team that made it. Starts are regular-season starts. Value is points "
         "above the average starter at the player's position, counted in that season's average starts. A hit is "
         f"{HIT} or more starts. Owner figures use drafts with all {HORIZON} seasons played "
         f"(2008 to {LAST_SEASON - HORIZON}).", ""]
    rounds = defaultdict(list)
    for p in done:
        rounds[p["round"]].append(p)
    def rate(ps):
        return f"{100 * sum(p['hit'] for p in ps) / len(ps):.0f}%" if ps else "-"
    L += ["## By round", "",
          "Kickers and defenses are split out: they start every week once drafted, so they make the middle rounds "
          "look better than they are for everyone else.", "",
          "| Round | Picks | Hit rate | Skill positions | Kickers and defenses (share of picks) | Starts per pick | Never started |",
          "|---|---|---|---|---|---|---|"]
    for rd in sorted(rounds):
        ps = rounds[rd]
        kd = [p for p in ps if p["position"] in ("K", "Def")]
        sk = [p for p in ps if p["position"] not in ("K", "Def")]
        L.append(f"| {rd} | {len(ps)} | {rate(ps)} | {rate(sk)} | {rate(kd)} ({100 * len(kd) / len(ps):.0f}%) | "
                 f"{statistics.mean(p['starts'] for p in ps):.1f} | "
                 f"{100 * sum(p['starts'] == 0 for p in ps) / len(ps):.0f}% |")
    first = [p for p in done if p["round"] == 1]
    tops = defaultdict(list)
    for p in first:
        tops[min(p["pick"], 17)].append(p)
    L += ["", "## The first round, pick by pick", "",
          "| Pick | Drafts | Hit rate | Starts per pick |", "|---|---|---|---|"]
    for k in sorted(tops):
        ps = tops[k]
        L.append(f"| {k}{' (the toilet bowl pick, from the 2023 draft)' if k == 17 else ''} | {len(ps)} | "
                 f"{100 * sum(p['hit'] for p in ps) / len(ps):.0f}% | {statistics.mean(p['starts'] for p in ps):.1f} |")
    p17 = [p for p in out if p["round"] == 1 and p["pick"] == 17]
    if p17:
        L += ["", "Every pick 17 so far, including drafts still inside their three seasons:", ""]
        L += [f"- {p['season']}: {p['team']} took {p['player']} ({p['position']}), {p['starts']} starts so far" for p in p17]
    L += ["", "## Owners", "",
          "Starts over slot is the average number of starts a pick gave above what picks at that point in the draft "
          "usually give, so an owner is not rewarded for drafting early. The margin is two standard errors: a figure "
          "inside plus or minus the margin is indistinguishable from an average drafter. With 17 owners, about one "
          "lands outside it by chance alone.", "",
          "| | Owner | Drafts | Picks | Hit rate | First-round hit rate | Starts per pick | Starts over slot | Margin | Value per pick |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(orows, 1):
        flag = " (outside)" if abs(r["starts_over_slot"]) > r["margin"] else ""
        L.append(f"| {i} | {r['owner']} | {r['drafts']} | {r['picks']} | {r['hit_rate']}% | "
                 f"{r['first_round_hit_rate']}% | {r['starts_per_pick']} | {r['starts_over_slot']:+}{flag} | "
                 f"{r['margin']} | {r['value_per_pick']:+} |")
    best = sorted(out, key=lambda p: -p["value"])
    L += ["", "## Best picks", "", "By value over the three seasons (or so far, for recent drafts).", "",
          "| Season | Round | Pick | Team | Player | Pos | Starts | Value |", "|---|---|---|---|---|---|---|---|"]
    for p in best[:15]:
        L.append(f"| {p['season']} | {p['round']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | "
                 f"{p['starts']} | {p['value']:+} |")
    steals = sorted([p for p in done if p["round"] >= 3], key=lambda p: -p["value"])
    L += ["", "## Best late picks (round 3 on)", "",
          "| Season | Round | Pick | Team | Player | Pos | Starts | Value |", "|---|---|---|---|---|---|---|---|"]
    for p in steals[:10]:
        L.append(f"| {p['season']} | {p['round']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | "
                 f"{p['starts']} | {p['value']:+} |")
    busts = sorted([p for p in first if p["pick"] <= 8], key=lambda p: (p["starts"], p["value"]))
    L += ["", "## Top-8 picks that never paid", "",
          "First-round picks in the top 8 with the fewest starts for the team that drafted them.", "",
          "| Season | Pick | Team | Player | Pos | Starts |", "|---|---|---|---|---|---|"]
    for p in busts[:10]:
        L.append(f"| {p['season']} | {p['pick']} | {p['team']} | {p['player']} | {p['position']} | {p['starts']} |")
    L += ["", "## Notes", "",
          "- From 2008, where MFL kept the draft and the lineups.",
          "- Starts count only for the team that drafted the player. A pick traded away, or a player traded after "
          "the draft, stops counting for the drafter, which is the point: value to the team that spent the pick.",
          "- A dynasty pick can pay later than three seasons. The horizon is a choice, and the CSV has every pick "
          "for a longer view.", ""]
    with open(f"{BASE}/docs/draft-value.md", "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
