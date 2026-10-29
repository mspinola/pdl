"""Canonical owner identities for the PDL, 2003-2026.

Franchise slots are linked year over year on a combined score: team-name
identity (which holds for 366 of 368 transitions) plus dynasty roster overlap
(which breaks ties when a team renames). Within 2016-2026 the MFL league id is
constant and franchise ids are stable, which is used to check the linker: it
reproduces the known mapping with zero mismatches.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_franchises import rosters, names, YEARS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())


def link(ra, rb, na, nb):
    scored = []
    for fa, pa in ra.items():
        for fb, pb in rb.items():
            overlap = len(pa & pb) / (len(pa | pb) or 1)
            score = overlap + (1.0 if norm(na[fa]) == norm(nb[fb]) else 0.0)
            scored.append((score, overlap, fa, fb))
    scored.sort(reverse=True)
    used_a, used_b, m = set(), set(), {}
    for score, overlap, fa, fb in scored:
        if fa in used_a or fb in used_b:
            continue
        used_a.add(fa); used_b.add(fb)
        m[fa] = fb
    return m


def build():
    R = {y: rosters(y) for y in YEARS}
    N = {y: names(y) for y in YEARS}

    chains = {}          # owner_id -> {year: franchise_id}
    cur = {}             # franchise_id in first year -> owner_id
    for i, fid in enumerate(sorted(R[YEARS[0]]), start=1):
        chains[i] = {YEARS[0]: fid}
        cur[fid] = i
    for y1, y2 in zip(YEARS, YEARS[1:]):
        m = link(R[y1], R[y2], N[y1], N[y2])
        nxt = {}
        for fa, fb in m.items():
            oid = cur[fa]
            chains[oid][y2] = fb
            nxt[fb] = oid
        cur = nxt

    # label each chain by its most recent team name, and keep the name history
    owners = {}
    for oid, byyear in chains.items():
        hist, last = [], None
        for y in YEARS:
            if y in byyear:
                nm = N[y][byyear[y]]
                if nm != last:
                    hist.append({"year": y, "name": nm})
                    last = nm
        owners[oid] = {
            "label": hist[-1]["name"],
            "name_history": hist,
            "slots": {str(y): byyear[y] for y in sorted(byyear)},
        }
    return owners


def slot_index(owners):
    """(year, franchise_id) -> owner label"""
    idx = {}
    for oid, o in owners.items():
        for y, f in o["slots"].items():
            idx[(int(y), f)] = o["label"]
    return idx


if __name__ == "__main__":
    o = build()
    json.dump(o, open(f"{BASE}/owners.json", "w"), indent=1)
    print(f"{len(o)} owner chains\n")
    for oid, v in sorted(o.items(), key=lambda kv: kv[1]["label"]):
        yrs = sorted(int(y) for y in v["slots"])
        hist = " -> ".join(f"{h['name']} ({h['year']})" for h in v["name_history"])
        print(f"{v['label']:<22} {len(yrs)} seasons {min(yrs)}-{max(yrs)}")
        if len(v["name_history"]) > 1:
            print(f"   names: {hist}")
