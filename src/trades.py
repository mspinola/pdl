"""Build the combined PDL trade log, 2000-2026.

Two sources, each authoritative where the other is blind:

- **MyFantasyLeague**, 2008 onward. Machine-written, dated to the day, assets
  named by player id and pick token.
- **The league's own GitHub archive**, 2000 to 2007 (`archive.py`). Hand-written
  prose. MFL has no transaction log at all before 2007, and its 2007 league
  year holds a single record. The archive's season labels are offset for
  offseason trades, which is corrected in `archive.py`, and only its seasons
  through 2007 are used so nothing is counted twice.

Known limits of the MFL half, both measured rather than assumed:

- Some records have an **empty side**: MFL logged what one franchise gave and
  nothing for the other. The trade is real and the two franchises are right,
  but its asset counts are a floor. These are flagged `incomplete`.
- A single deal is sometimes **split across two records**, one of them
  empty-sided, or logged in two league years. Both shapes are merged below.

The archive half carries no structured assets at all, only the original
sentence, so player and pick counts are reported over the MFL half only.
"""
import json, os, sys, datetime, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store
import identities as I
import archive as A
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{BASE}/raw"
MFL_YEARS = list(range(2007, LAST_SEASON + 1))

PLAYERS = json.load(open(f"{BASE}/player_index.json"))


def asset(token):
    token = token.strip()
    if not token:
        return None
    if token.startswith("FP_"):
        parts = token.split("_")
        if len(parts) >= 4:
            return {"kind": "pick", "label": f"{parts[2]} R{parts[3]}",
                    "origin_franchise": parts[1], "year": int(parts[2]),
                    "round": int(parts[3])}
        return {"kind": "pick", "label": token}
    if token.startswith("DP_"):
        # DP_<round>_<pick>, both zero-indexed, in the current season's draft
        parts = token.split("_")
        try:
            rnd, pick = int(parts[1]) + 1, int(parts[2]) + 1
            return {"kind": "pick", "label": f"R{rnd} P{pick:02d}",
                    "round": rnd, "pick": pick, "current_year": True}
        except (IndexError, ValueError):
            return {"kind": "pick", "label": token}
    p = PLAYERS.get(token, {})
    return {"kind": "player", "id": token,
            "label": p.get("name") or f"player {token}",
            "position": p.get("position")}


def mfl_records():
    slots = I.slot_index()
    out = []
    for year in MFL_YEARS:
        path = store.season(year, "trades")
        if not os.path.exists(path):
            continue
        d = store.load(path).get("transactions")
        if not d or not d.get("transaction"):
            continue
        recs = d["transaction"]
        recs = recs if isinstance(recs, list) else [recs]
        for r in recs:
            if r.get("type") != "TRADE":
                continue
            f1, f2 = r.get("franchise"), r.get("franchise2")
            if not f1 or not f2:
                continue
            ts = int(r["timestamp"])
            date = datetime.date.fromtimestamp(ts)
            a = slots.get((year, f1))
            b = slots.get((year, f2))
            if a is None or b is None:
                continue
            # the owner label depends on when the trade happened, not on the
            # league year the record sits in
            a = I.label_for(a, date.year)
            b = I.label_for(b, date.year)
            out.append({
                "season": year,
                "date": date.isoformat(),
                "date_precision": "day",
                "timestamp": ts,
                "team_a": a,
                "team_b": b,
                "a_gave": [x for x in (asset(t) for t in r.get("franchise1_gave_up", "").split(",")) if x],
                "b_gave": [x for x in (asset(t) for t in r.get("franchise2_gave_up", "").split(",")) if x],
                "by_commish": r.get("by_commish") == "1",
                "comments": (r.get("comments") or "").strip(),
                "source": "mfl",
            })
    out.sort(key=lambda t: t["timestamp"])
    return out


def drop_exact_repeats(trades, window_days=21):
    """A deal agreed near a season rollover can land in both league years' logs,
    and a re-submitted deal can be logged twice the same day. Both look like the
    same pair giving the same assets within days."""
    seen, out = {}, []
    for t in trades:
        key = (tuple(sorted((t["team_a"], t["team_b"]))),
               tuple(sorted((tuple(sorted(a["label"] for a in t["a_gave"])),
                             tuple(sorted(a["label"] for a in t["b_gave"]))))))
        prev = seen.get(key)
        if prev is not None and t["timestamp"] - prev <= window_days * 86400:
            continue
        seen[key] = t["timestamp"]
        out.append(t)
    return out


def merge_split_records(trades):
    """Join records that are one deal written as two.

    Same two franchises, same day, and at least one of the records missing a
    side. The assets are unioned and the deal is dated to the later league
    year, which is the one an offseason trade belongs to.
    """
    groups = collections.defaultdict(list)
    for t in trades:
        groups[(tuple(sorted((t["team_a"], t["team_b"]))), t["date"])].append(t)
    out = []
    for group in groups.values():
        if len(group) == 1 or not any(not g["a_gave"] or not g["b_gave"] for g in group):
            out.extend(group)
            continue
        base = max(group, key=lambda g: (len(g["a_gave"]) + len(g["b_gave"]), g["season"]))
        merged = dict(base)
        merged["season"] = max(g["season"] for g in group)
        for g in group:
            if g is base:
                continue
            # a record may name the two sides in the opposite order
            same = (g["team_a"], g["team_b"]) == (base["team_a"], base["team_b"])
            for key, other in (("a_gave", "b_gave"), ("b_gave", "a_gave")):
                extra = g[key] if same else g[other]
                have = {a["label"] for a in merged[key]}
                merged[key] = merged[key] + [a for a in extra if a["label"] not in have]
        merged["merged_records"] = len(group)
        out.append(merged)
    out.sort(key=lambda t: t["timestamp"])
    return out


def build():
    mfl = merge_split_records(drop_exact_repeats(mfl_records()))
    for t in mfl:
        t["assets_known"] = True
        t["incomplete"] = not t["a_gave"] or not t["b_gave"]

    out = list(mfl)
    for t in A.archive_trades():
        out.append({
            "season": t["season"],
            "date": str(t["season"]),
            "date_precision": "season",
            "timestamp": datetime.datetime(t["season"], 7, 1).timestamp(),
            "team_a": I.label_for(t["team_a"], t["season"]),
            "team_b": I.label_for(t["team_b"], t["season"]),
            "a_gave": [],
            "b_gave": [],
            "by_commish": False,
            "comments": "",
            "raw": t["raw"],
            "source": "archive",
            "assets_known": False,
            "incomplete": False,
        })
    out.sort(key=lambda t: (t["season"], t["timestamp"]))
    return out


if __name__ == "__main__":
    t = build()
    json.dump(t, open(f"{BASE}/trades.json", "w"), indent=1)
    mfl = [x for x in t if x["source"] == "mfl"]
    arc = [x for x in t if x["source"] == "archive"]
    print(f"{len(t)} trades, seasons {min(x['season'] for x in t)}-{max(x['season'] for x in t)}")
    print(f"  {len(arc)} from the archive (2000-2007), {len(mfl)} from MFL (2008-2026)")
    print(f"  merged split records: {sum(1 for x in mfl if x.get('merged_records'))}")
    print(f"  MFL records still missing one side: {sum(1 for x in mfl if x['incomplete'])}")
    bad = [x for x in t if x["team_a"] == x["team_b"]]
    print(f"  self-trades (should be 0): {len(bad)}")
    labels = {x["team_a"] for x in t} | {x["team_b"] for x in t}
    known = set(I.build())
    print(f"  unknown owner labels (should be empty): {labels - known}")
    print(f"  Bunchalosers trades: {sum(1 for x in t if 'Bunchalosers' in (x['team_a'], x['team_b']))}"
          f"   Couchfire trades: {sum(1 for x in t if 'Couchfire' in (x['team_a'], x['team_b']))}")
