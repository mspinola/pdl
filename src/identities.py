"""Owner identities for the PDL, 2000-2026.

`owners.py` links franchise *slots* across seasons by name and roster overlap.
That finds the franchise, which is not always the owner. Two corrections are
applied here, neither of which is discoverable from the data:

1. **The one owner change in league history.** The Bunchalosers franchise
   changed hands after 2017 and was renamed Couchfire. Roster overlap cannot
   see this: a franchise that changes owner keeps its players, so it looks
   like one continuous identity. The chain is therefore split in two, and the
   two owners are reported separately.

2. **The league's first two seasons.** It began in 2000 with 14 teams. Beers
   and OakalDoakals joined in 2001 as expansion teams, confirmed by the 2000
   standings page (which lists exactly the other 14) and by the 2001 expansion
   rules page. MFL has no league data before 2003, so 2000-2002 presence comes
   from those pages rather than from a roster link.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owners as O
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEAGUE_START = 2000
LEAGUE_END = LAST_SEASON

# Franchises that were not there for season 2000.
EXPANSION = {"Beers": 2001, "OakalDoakals": 2001}

# The single owner change: the franchise MFL now calls Couchfire was a
# different owner's team through 2017, under the name Bunchalosers.
OWNER_CHANGE_FRANCHISE = "Couchfire"
OWNER_CHANGE_SEASON = 2018
PREVIOUS_OWNER_LABEL = "Bunchalosers"


def label_for(franchise, season):
    """The owner label to report for a franchise in a given season."""
    if franchise in (OWNER_CHANGE_FRANCHISE, PREVIOUS_OWNER_LABEL):
        return PREVIOUS_OWNER_LABEL if season < OWNER_CHANGE_SEASON else OWNER_CHANGE_FRANCHISE
    return franchise


def build():
    """Owner identities, each with the seasons it was in the league."""
    chains = O.build()
    out = {}
    for chain in chains.values():
        franchise = chain["label"]
        slots = {int(y): f for y, f in chain["slots"].items()}
        start = EXPANSION.get(franchise, LEAGUE_START)
        present = [y for y in range(start, LEAGUE_END + 1)
                   if y < min(slots) or y in slots]

        if franchise == OWNER_CHANGE_FRANCHISE:
            early = [y for y in present if y < OWNER_CHANGE_SEASON]
            late = [y for y in present if y >= OWNER_CHANGE_SEASON]
            out[PREVIOUS_OWNER_LABEL] = {
                "label": PREVIOUS_OWNER_LABEL,
                "franchise": franchise,
                "seasons": early,
                "slots": {str(y): f for y, f in slots.items() if y < OWNER_CHANGE_SEASON},
                "note": f"Original owner of the franchise, through {OWNER_CHANGE_SEASON - 1}.",
            }
            out[OWNER_CHANGE_FRANCHISE] = {
                "label": OWNER_CHANGE_FRANCHISE,
                "franchise": franchise,
                "seasons": late,
                "slots": {str(y): f for y, f in slots.items() if y >= OWNER_CHANGE_SEASON},
                "note": f"Took over the franchise in {OWNER_CHANGE_SEASON} and renamed it.",
            }
            continue

        out[franchise] = {
            "label": franchise,
            "franchise": franchise,
            "seasons": present,
            "slots": {str(y): f for y, f in slots.items()},
            "note": (f"Expansion team, joined in {EXPANSION[franchise]}."
                     if franchise in EXPANSION else ""),
        }
    for v in out.values():
        v["first_season"] = min(v["seasons"])
        v["last_season"] = max(v["seasons"])
        v["season_count"] = len(v["seasons"])
    return out


def slot_index(identities=None):
    """(season, franchise_id) -> owner label, honouring the owner change."""
    identities = identities or build()
    idx = {}
    for ident in identities.values():
        for y, f in ident["slots"].items():
            idx[(int(y), f)] = ident["label"]
    return idx


if __name__ == "__main__":
    ids = build()
    json.dump(ids, open(f"{BASE}/identities.json", "w"), indent=1)
    print(f"{len(ids)} owner identities\n")
    print(f"  {'owner':<22}{'seasons':>9}  span")
    for k, v in sorted(ids.items(), key=lambda kv: (-kv[1]["season_count"], kv[0])):
        print(f"  {v['label']:<22}{v['season_count']:>9}  {v['first_season']}-{v['last_season']}"
              f"{'   ' + v['note'] if v['note'] else ''}")
    counts = {}
    for y in range(LEAGUE_START, LEAGUE_END + 1):
        counts[y] = sum(1 for v in ids.values() if y in v["seasons"])
    print("\n  teams per season:")
    for y, n in counts.items():
        if y <= 2004 or n != 16:
            print(f"    {y}: {n}")
    print(f"    2005-{LEAGUE_END}: 16 (every season)" if all(
        counts[y] == 16 for y in range(2005, LEAGUE_END + 1)) else "    varies")
