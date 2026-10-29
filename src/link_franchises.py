"""Link (year, franchise_id) slots into continuous owner identities.

The league moved MFL league IDs most years before 2016, so franchise IDs are
only guaranteed stable within a league ID. Dynasty rosters carry over almost
intact, so year-over-year roster overlap identifies the same owner.
"""
import json, os, sys, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "raw")
YEARS = list(range(2003, 2027))


def rosters(year):
    d = store.load(store.season(year, "rosters")).get("rosters", {}).get("franchise", [])
    if isinstance(d, dict):
        d = [d]
    out = {}
    for f in d:
        pl = f.get("player", [])
        if isinstance(pl, dict):
            pl = [pl]
        out[f["id"]] = {p["id"] for p in pl}
    return out


def names(year):
    fr = store.load(store.season(year, "league"))["league"]["franchises"]["franchise"]
    return {f["id"]: f["name"] for f in fr}


def best_assignment(a, b):
    """Maximise total roster overlap between year a's and year b's franchises.

    16 franchises, so a full permutation search is out; use greedy on the
    overlap matrix, which is unambiguous when overlaps are this lopsided.
    """
    pairs = []
    for fa, pa in a.items():
        for fb, pb in b.items():
            inter = len(pa & pb)
            union = len(pa | pb) or 1
            pairs.append((inter / union, inter, fa, fb))
    pairs.sort(reverse=True)
    used_a, used_b, m = set(), set(), {}
    for jac, inter, fa, fb in pairs:
        if fa in used_a or fb in used_b:
            continue
        used_a.add(fa); used_b.add(fb)
        m[fa] = (fb, jac, inter)
    return m


def main():
    R = {y: rosters(y) for y in YEARS}
    N = {y: names(y) for y in YEARS}

    # chain forward
    links = {}
    for y1, y2 in zip(YEARS, YEARS[1:]):
        links[(y1, y2)] = best_assignment(R[y1], R[y2])

    # build owner chains
    owner_of = {}
    next_id = itertools.count(1)
    for fid in sorted(R[YEARS[0]]):
        owner_of[(YEARS[0], fid)] = next(next_id)
    for y1, y2 in zip(YEARS, YEARS[1:]):
        for fa, (fb, jac, inter) in links[(y1, y2)].items():
            key = (y1, fa)
            owner_of[(y2, fb)] = owner_of.get(key) or next(next_id)
        for fid in R[y2]:
            owner_of.setdefault((y2, fid), next(next_id))

    # report link quality
    print("link quality (min/median jaccard per year transition)")
    weak = []
    for (y1, y2), m in links.items():
        js = sorted(v[1] for v in m.values())
        print(f"  {y1}->{y2}  min={js[0]:.2f} med={js[len(js)//2]:.2f} max={js[-1]:.2f}")
        for fa, (fb, jac, inter) in m.items():
            if jac < 0.25:
                weak.append((y1, fa, N[y1][fa], y2, fb, N[y2][fb], jac, inter))
    print(f"\nweak links (jaccard < 0.25): {len(weak)}")
    for w in weak:
        print(f"  {w[0]} {w[2]!r} -> {w[3]} {w[5]!r}  jac={w[6]:.2f} shared={w[7]}")

    # id stability check on the constant-league-id era
    print("\nid stability 2016-2026 (same MFL league id 16177):")
    bad = 0
    for y1, y2 in zip(range(2016, 2026), range(2017, 2027)):
        for fa, (fb, jac, inter) in links[(y1, y2)].items():
            if fa != fb:
                bad += 1
                print(f"  MISMATCH {y1}:{fa} -> {y2}:{fb} jac={jac:.2f}")
    print(f"  mismatches: {bad}")

    json.dump({f"{y}:{f}": o for (y, f), o in owner_of.items()},
              open(f"{BASE}/owner_map.json", "w"), indent=1)
    print(f"\ndistinct owner chains: {len(set(owner_of.values()))}")


if __name__ == "__main__":
    main()
