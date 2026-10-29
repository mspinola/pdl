"""The rule book as of any season: the 2006 baseline with the ledger applied.

rules/baseline.json is the 2006 text, rules/ledger.json says what changed and
when, and rules/amendments.json holds the exact edit each change makes. This
applies them in order and returns, for a season, every section's text, its
history, the notes that belong beside it, and the facts MFL can confirm.

    python3 src/rulebook_build.py          # apply every change and check each edit lands

Which changes apply to a season:

- adopted and in practice: from the effective season on
- one season: its notes, in that season only (it never changes the text)
- open: its notes from the meeting on, marked unconfirmed (never the text)

Every edit must find its target exactly once. An edit that finds nothing means
the ledger is out of order or the target text has changed, so the build stops
rather than produce a book that silently skipped a rule.
"""
import copy, json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = f"{BASE}/rules"
FIRST, BASELINE_SEASON = 2006, 2006


class AmendmentError(Exception):
    pass


def load(name):
    with open(f"{RULES}/{name}") as f:
        return json.load(f)


def latest_season():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fetch_mfl import LAST_SEASON
    return LAST_SEASON


def _block(b):
    if isinstance(b, str):
        return {"type": "p", "text": b}
    if b.get("type") == "list":
        items = [it if isinstance(it, dict) else {"text": it} for it in b["items"]]
        if b.get("ordered"):
            items = [{**it, "n": it.get("n", i + 1)} for i, it in enumerate(items)]
        return {"type": "list", "ordered": b.get("ordered", False), "items": items}
    return b


def _texts(block):
    """(container, key) pairs for every editable string in a block."""
    if block["type"] in ("p", "h"):
        return [(block, "text")]
    if block["type"] == "list":
        return [(it, "text") for it in block["items"]]
    return []


def _find_block(sec, needle, cid):
    hits = [i for i, b in enumerate(sec["blocks"]) if any(needle in c[k] for c, k in _texts(b))]
    if len(hits) != 1:
        raise AmendmentError(f"{cid}: '{needle[:50]}' is in {len(hits)} blocks of {sec['id']}")
    return hits[0]


def _table(sec, title, cid):
    hits = [b for b in sec["blocks"] if b["type"] == "table" and b["title"] == title]
    if len(hits) != 1:
        raise AmendmentError(f"{cid}: no single table '{title}' in {sec['id']}")
    return hits[0]


def _row(r):
    return {"label": r[0], "values": r[1:]}


def apply_op(sections, op, cid):
    """Apply one edit. `sections` is the ordered list of section dicts."""
    by_id = {s["id"]: s for s in sections}
    kind = op["op"]
    if kind == "add_section":
        if op["id"] in by_id:
            raise AmendmentError(f"{cid}: section {op['id']} already exists")
        at = next(i for i, s in enumerate(sections) if s["id"] == op["after"])
        sections.insert(at + 1, {"id": op["id"], "chapter": op["id"].split(".")[0], "title": op["title"],
                                 "level": 2, "blocks": [_block(b) for b in op["blocks"]], "added": cid})
        return
    sec = by_id.get(op["section"])
    if sec is None:
        raise AmendmentError(f"{cid}: no section {op['section']}")
    if kind == "edit":
        spots = [(c, k) for b in sec["blocks"] for c, k in _texts(b) if op["find"] in c[k]]
        if len(spots) != 1 or spots[0][0][spots[0][1]].count(op["find"]) != 1:
            raise AmendmentError(f"{cid}: '{op['find'][:50]}' is not exactly once in {sec['id']}")
        c, k = spots[0]
        c[k] = c[k].replace(op["find"], op["to"])
    elif kind == "set":
        sec["blocks"] = [_block(b) for b in op["blocks"]]
    elif kind == "replace_block":
        i = _find_block(sec, op["find"], cid)
        sec["blocks"][i:i + 1] = [_block(b) for b in op["blocks"]]
    elif kind == "insert_after":
        i = len(sec["blocks"]) - 1 if op.get("at") == "end" else _find_block(sec, op["find"], cid)
        sec["blocks"][i + 1:i + 1] = [_block(b) for b in op["blocks"]]
    elif kind == "remove_block":
        del sec["blocks"][_find_block(sec, op["find"], cid)]
    elif kind == "insert_item":
        lists = [b for b in sec["blocks"] if b["type"] == "list"
                 and any(it["text"] == op["after_item"] for it in b["items"])]
        if len(lists) != 1:
            raise AmendmentError(f"{cid}: no single list item '{op['after_item'][:40]}' in {sec['id']}")
        items = lists[0]["items"]
        j = next(i for i, it in enumerate(items) if it["text"] == op["after_item"])
        items.insert(j + 1, {"text": op["text"]})
    elif kind == "table_group":
        t = _table(sec, op["table"], cid)
        hits = [i for i, g in enumerate(t["groups"]) if g["label"] == op["group"]]
        if len(hits) != 1:
            raise AmendmentError(f"{cid}: no single group '{op['group']}' in table '{op['table']}'")
        t["groups"][hits[0]] = {"label": op["label"], "rows": [_row(r) for r in op["rows"]]}
    elif kind == "table_row":
        t = _table(sec, op["table"], cid)
        g = next((g for g in t["groups"] if g["label"] == op["group"]), None)
        if g is None:
            raise AmendmentError(f"{cid}: no group '{op['group']}' in table '{op['table']}'")
        row = _row(op["row"])
        same = [i for i, r in enumerate(g["rows"]) if r["label"] == row["label"]]
        if same:
            g["rows"][same[0]] = row
        else:
            g["rows"].append(row)
    elif kind == "note":
        pass  # notes are collected separately, they never change the text
    else:
        raise AmendmentError(f"{cid}: unknown op {kind}")
    sec.setdefault("changed_by", []).append(cid)


def changes():
    """Ledger changes joined to their amendments, in ledger order."""
    amend = load("amendments.json")["changes"]
    out = []
    for c in load("ledger.json")["changes"]:
        if c["id"] not in amend:
            raise AmendmentError(f"{c['id']}: no entry in amendments.json")
        out.append({**c, **amend[c["id"]]})
    return out


def applies(c, season):
    """Whether a change has changed the text by `season`."""
    return c["status"] in ("adopted", "in practice") and c.get("effective") and c["effective"] <= season


def notes_for(c, season):
    if c["status"] == "one season":
        return c.get("effective") == season
    if c["status"] == "open":
        return c["meeting"] <= season
    if c["status"] == "in practice":
        return c.get("effective") and c["effective"] <= season
    return False


def book(season):
    """The rule book in force for `season`."""
    baseline = load("baseline.json")
    sections = copy.deepcopy(baseline["sections"])
    facts = copy.deepcopy(load("amendments.json")["baseline_facts"])
    history, notes = {}, {}
    # apply in effective order, keeping ledger order within a season
    todo = sorted(enumerate(changes()), key=lambda ic: (ic[1].get("effective") or ic[1]["meeting"], ic[0]))
    for _, c in todo:
        if applies(c, season):
            for op in c["ops"]:
                apply_op(sections, op, c["id"])
            facts.update(c.get("facts", {}))
        for s in c["sections"]:
            if c["meeting"] <= season:
                history.setdefault(s, []).append(c)
        if c["status"] == "one season" and c.get("effective") == season:
            facts.update(c.get("facts", {}))  # a one-season rule's facts hold for its season only
        if notes_for(c, season):
            for op in c["ops"]:
                if op["op"] == "note":
                    notes.setdefault(op["section"], []).append((c, op["text"]))
    return {"season": season, "sections": sections, "facts": facts, "history": history, "notes": notes}


def section_ids_ever():
    """Every section id the book has had, baseline or added."""
    ids = {s["id"] for s in load("baseline.json")["sections"]}
    for c in changes():
        ids |= {op["id"] for op in c["ops"] if op["op"] == "add_section"}
    return ids


def check():
    """Build every season, and the latest with every change applied."""
    last = latest_season()
    problems = []
    for season in range(FIRST, last + 1):
        try:
            book(season)
        except AmendmentError as e:
            problems.append(f"{season}: {e}")
            break
    cs = changes()
    for c in cs:
        if c["status"] in ("one season", "open") and any(op["op"] != "note" for op in c["ops"]):
            problems.append(f"{c['id']}: a {c['status']} change may only carry notes")
    return problems


def main():
    problems = check()
    for p in problems:
        print("  PROBLEM", p)
    if problems:
        return 1
    last = latest_season()
    b = book(last)
    changed = sum(1 for s in b["sections"] if s.get("changed_by"))
    print(f"built {FIRST} to {last}: every edit lands. {last}: {len(b['sections'])} sections, "
          f"{changed} changed since 2006, {sum(len(v) for v in b['notes'].values())} notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
