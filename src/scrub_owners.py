"""Remove owner names from the archived legacy pages.

The MyFantasyLeague half of the archive carries no owner names at all: its
public API exposes team names only. The league's own pages do carry them, in
five different shapes, and this repository is meant to be public.

This script holds **no names of its own**. It derives the owner-to-team mapping
at run time from the Original Owners list on the league history page, then uses
it to replace owner references elsewhere with the team name. Scrubbing that
history page last removes the mapping itself, so after a run nothing here states
who owned what.

Replacing rather than deleting makes the archive more useful, not less: the
inaugural draft board labels its picks by owner, and after a run it labels them
by team, which is what every other dataset uses.

Nothing is lost: the untouched originals remain on the league's own site, in the
mspinola/mspinola repository.

The hazard this is careful about: owner first names collide with NFL players.
The 2001 expansion draft alone lists Matt Hasselbeck, Keenan McCardell, Mike
Vanderjagt, Tony Martin and Chris Redman. So nothing is matched on a bare name
inside running text. Only these positions are touched:

1. "Team (Owner)" in the owners list
2. "Team -- Owner" in the 2001 and 2002 schedules and standings
3. "Owner's Team" where the remainder is a real team name
4. a table cell that is exactly an owner label, which is how the draft boards
   name the drafting team
5. an owner's full name as a column header on the original rosters page
6. page metadata: keywords, and the author fields Word left in the exported
   draft boards

After scrubbing it checks its own work, including that the colliding player
names are still intact.
"""
import html, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = f"{BASE}/mfl_archive/legacy"
OWNERS_PAGE = "history_misc.html"
ROSTERS_PAGE = "history_orgrost.html"

# players whose first name is also an owner's: proof the scrub stayed surgical
COLLISION_CANARIES = [
    "Matt Hasselbeck", "Keenan McCardell", "Mike Vanderjagt",
    "Tony Martin", "Chris Redman", "Mike Hollis",
]

NEUTRAL_KEYWORDS = "fantasy football, PDL, dynasty league"


def mapping():
    """owner label -> team, plus the raw pairs and the founding subset."""
    path = f"{LEGACY}/{OWNERS_PAGE}"
    text = html.unescape(re.sub(r"<[^>]+>", "|", open(path, encoding="utf-8",
                                                      errors="replace").read()))
    # the page lists the founding owners, then a heading, then the two the
    # league expanded with in 2001
    split = re.search(r"\|[^|]*Expansion Owners[^|]*\|", text)
    head, tail = (text[:split.start()], text[split.start():]) if split else (text, "")
    pairs, founding = {}, {}
    for section, store in ((head, founding), (tail, None)):
        for m in re.finditer(r"\|\s*([A-Za-z][A-Za-z'\- ]+?)\s*\(([^)]+)\)", section):
            team, owner = m.group(1).strip(), m.group(2).strip()
            pairs[owner] = team
            if store is not None:
                store[owner] = team
    out = {}
    for owner, team in pairs.items():
        keys = label_keys(owner)
        for k in keys:
            k = k.lower()
            if k in out and out[k] != team:
                out[k] = None          # ambiguous, so unusable
            else:
                out.setdefault(k, team)
    founding_labels = {}
    for owner, team in founding.items():
        for k in label_keys(owner):
            k = k.lower()
            if k in founding_labels and founding_labels[k] != team:
                founding_labels[k] = None
            else:
                founding_labels.setdefault(k, team)
    return ({k: v for k, v in out.items() if v}, pairs, founding,
            {k: v for k, v in founding_labels.items() if v})


def _norm(label):
    return re.sub(r"[.\s]+", " ", label).strip().lower().strip("'")


def label_keys(owner):
    """Every spelling of one owner label the pages use.

    One label is a pair of names, written three different ways across the
    pages. One is spelled with and without a trailing letter. Two are shortened
    to a first name plus an initial, and one to two letters. Where a key ends up
    ambiguous across owners the resolvers refuse it rather than guess.
    """
    keys = {owner}
    parts = [p.strip() for p in re.split(r"\s+and\s+|/|&", owner) if p.strip()]
    keys.update(parts)
    keys.add(" / ".join(parts))
    keys.add(" and ".join(parts))
    if len(parts) == 1 and " " in owner:
        first, last = owner.split()[0], owner.split()[-1]
        keys.update({f"{first} {last[0]}", last, first})
    return keys


def team_for(label, owners):
    """Strict: for a table cell, where a wrong match would rewrite a player.

    A cell is only an owner reference if its whole text is an owner label. A
    multi-word cell must match a label exactly, so a player such as "Keenan
    McCardell" or "P Manning" is left alone while a two-owner label is not. A
    single word may differ by up to two characters, which covers a surname
    written with or without its final letter.
    """
    key = _norm(label)
    if not key:
        return None
    if key in owners:
        return owners[key]
    if " " in key:
        return None
    for k, team in owners.items():
        if " " in k or len(k) < 4:
            continue
        if (k.startswith(key) or key.startswith(k)) and abs(len(key) - len(k)) <= 2:
            return team
    return None


def team_for_annotation(label, owners):
    """Loose: for the tail of "Team -- Owner", which is an owner by position.

    Those pages abbreviate some labels to two letters, disambiguate the two
    owners who share a first name by adding an initial, and truncate others
    where a table cell was too narrow. Used nowhere else.
    """
    key = _norm(label)
    if not key:
        return None
    strict = team_for(label, owners)
    if strict:
        return strict
    parts = [p for p in re.split(r"[/\s]+", key) if p]
    initials = "".join(p[0] for p in parts)
    for k, team in owners.items():
        kparts = [p for p in re.split(r"[/\s]+|\band\b", _norm(k)) if p]
        if len(initials) > 1 and initials == "".join(p[0] for p in kparts):
            return team
        if len(parts) == 2 and len(kparts) >= 2 and kparts[0] == parts[0] \
           and kparts[-1].startswith(parts[-1]):
            return team
    if len(key) >= 2:
        hits = {team for k, team in owners.items()
                if " " not in k and _norm(k).startswith(key)}
        if len(hits) == 1:
            return hits.pop()
    return None


def scrub_roster_headers(body, owners, founding):
    """Replace the original rosters' owner column headers with team names.

    Four of the fourteen do not match on a first name: two give a different
    first name with the owner's surname, one is written as the owner label
    itself, and one is a nickname nothing in the mapping spells out. Since the
    page carries exactly one header per founding team, the last is settled by
    elimination.
    """
    def header_like(label):
        if "," in label or label.startswith("Over Def"):
            return False
        return bool(re.fullmatch(r"[A-Z][A-Za-z'\-]+(?:\s+(?:and\s+)?[A-Z][A-Za-z'\-]+){1,2}",
                                 label))

    cells = []
    for m in re.finditer(r"(>)([^<>]{3,40}?)(<)", body):
        label = html.unescape(m.group(2)).strip()
        if header_like(label):
            cells.append(label)
    headers = list(dict.fromkeys(cells))

    resolved, used = {}, set()
    for label in headers:
        parts = label.split()
        team = (team_for(label, owners) or team_for(parts[0], owners)
                or team_for(parts[-1], owners)
                or team_for_annotation(label, owners))
        if team:
            resolved[label] = team
            used.add(team)
    # only the founding teams: the two the league expanded with in 2001 are not
    # on a page of the first season's rosters
    left_teams = [t for t in founding.values() if t not in used]
    left_headers = [h for h in headers if h not in resolved]
    if len(left_headers) == 1 and len(left_teams) == 1:
        resolved[left_headers[0]] = left_teams[0]
        left_headers, left_teams = [], []
    for h in left_headers:
        resolved[h] = "Unknown team"

    n = 0
    for label, team in resolved.items():
        pat = re.compile(r"(>)\s*" + re.escape(label) + r"\s*(<)")
        body, k = pat.subn(rf"\g<1>{team}\g<2>", body)
        n += k
    return body, n


def scrub_text_cells(body, owners, counts, founding_owners=None):
    """Rule 4: a cell whose entire text is an owner label becomes the team.

    Resolved against the founding owners first. Two owners share a first name,
    which makes it ambiguous across all sixteen and unusable, but only
    one of them founded the league, and the pages that label teams by owner are
    the inaugural draft boards.
    """
    def repl(m):
        open_tag, inner, close = m.group(1), m.group(2), m.group(3)
        label = html.unescape(inner).strip()
        if not label or len(label) > 24:
            return m.group(0)
        team = (team_for(label, founding_owners or {})
                or team_for(label, owners))
        if team and label.lower() != team.lower():
            counts["cell"] = counts.get("cell", 0) + 1
            return f"{open_tag}{team}{close}"
        return m.group(0)
    # innermost element whose content is pure text
    return re.sub(r"(>)([^<>]{1,40}?)(<)", repl, body)


def scrub(path, owners, pairs, founding, founding_owners, dry=False):
    body = open(path, encoding="utf-8", errors="replace").read()
    original = body
    counts = {}

    # 1. "Team (Owner)" in the owners list
    for owner, team in pairs.items():
        for variant in {owner, html.escape(owner)}:
            pat = re.compile(r"\s*\(\s*" + re.escape(variant) + r"\s*\)")
            body, n = pat.subn("", body)
            if n:
                counts["paren"] = counts.get("paren", 0) + n

    # 2. "Owner's Team" where the remainder is a real team. Done before the
    #    suffix pass so that the team name is bare for it to anchor on.
    teams = sorted(set(pairs.values()), key=len, reverse=True)
    for team in teams:
        pat = re.compile(r"\b[A-Z][A-Za-z]+'s\s+(" + re.escape(team) + r")\b")
        body, n = pat.subn(r"\1", body)
        if n:
            counts["possessive"] = counts.get("possessive", 0) + n

    # 3. "Team -- Owner", anchored on the team name rather than on a list of
    #    owner spellings, because the pages disambiguate two owners who share a
    #    first name (adding an initial), abbreviate, and truncate in narrow
    #    cells to two letters. Anything short after the dashes in that
    #    position is an owner annotation. "at" and "vs" are the words that can
    #    legitimately follow, so they are never eaten.
    tail = r"(?!at\b|vs\b)[A-Za-z/.'&]{1,10}"
    for team in teams:
        pat = re.compile(r"(" + re.escape(team) + r")\s*--\s*" + tail
                         + r"(?:\s+" + tail + r")?")
        body, n = pat.subn(r"\1", body)
        if n:
            counts["suffix"] = counts.get("suffix", 0) + n

    # 3b. any "-- <short tail>" left where the tail resolves to an owner, which
    #     covers team names these pages spell differently from the owners list
    def drop_tail(m):
        if team_for_annotation(m.group(1), owners):
            counts["suffix"] = counts.get("suffix", 0) + 1
            return ""
        return m.group(0)
    body = re.sub(r"\s*--\s*((?!at\b|vs\b)[A-Za-z/.'&]{1,10}(?:\s+(?!at\b|vs\b)[A-Za-z/.'&]{1,10})?)",
                  drop_tail, body)

    # 4. cells that are exactly an owner label
    body = scrub_text_cells(body, owners, counts, founding_owners)

    # 5. owner full names, only on the original rosters page, whose column
    #    headers are the fourteen founding owners. Matching on a bare first name
    #    anywhere else would rewrite NFL players: the 2001 expansion draft lists
    #    Matt Hasselbeck, Keenan McCardell, Mike Vanderjagt and Tony Martin.
    if os.path.basename(path) == ROSTERS_PAGE:
        body, n = scrub_roster_headers(body, owners, founding)
        if n:
            counts["header"] = counts.get("header", 0) + n

    # 6. page and document metadata
    body, n = re.subn(r'(<meta\s+name=["\']keywords["\']\s+content=["\'])[^"\']*(["\'])',
                      rf"\g<1>{NEUTRAL_KEYWORDS}\g<2>", body, flags=re.I)
    counts["meta"] = counts.get("meta", 0) + n
    body, n = re.subn(r"<o:(Author|LastAuthor|Company|Manager)>[^<]*</o:\1>",
                      r"<o:\1></o:\1>", body)
    counts["docmeta"] = counts.get("docmeta", 0) + n
    body, n = re.subn(r'(<meta\s+name=["\'](?:author|Author)["\']\s+content=["\'])[^"\']*(["\'])',
                      r"\g<1>\g<2>", body)
    counts["meta"] = counts.get("meta", 0) + n

    counts = {k: v for k, v in counts.items() if v}
    if body != original and not dry:
        open(path, "w", encoding="utf-8").write(body)
    return counts, body


def full_personal_names(before):
    """Every personal name the pages carried, read before anything is scrubbed.

    Collected in memory so the check never has to write a real name down, which
    is the whole point of this script.
    """
    names = set()
    owners, pairs, _, _ = mapping()
    for owner in pairs:
        for part in re.split(r"\s+and\s+|/|&", owner):
            part = part.strip()
            if len(part) > 2:
                names.add(part)
    names = {n for n in names if " " in n}
    body = before.get(ROSTERS_PAGE, "")
    for m in re.finditer(r"(>)([^<>]{3,40}?)(<)", body):
        label = html.unescape(m.group(2)).strip()
        if "," in label or label.startswith("Over Def"):
            continue
        if re.fullmatch(r"[A-Z][A-Za-z'\-]+(?:\s+(?:and\s+)?[A-Z][A-Za-z'\-]+){1,2}", label):
            names.add(label)
            surname = label.split()[-1]
            if len(surname) > 4 and _norm(surname) not in owners:
                names.add(surname)
    for m in re.finditer(r"<o:(?:Author|LastAuthor)>([^<]+)</o:", "".join(before.values())):
        name = m.group(1).strip()
        if name:
            names.add(name)
            if " " in name:
                names.add(name.split()[-1])
    return names


def main(dry=False):
    owners, pairs, founding, founding_owners = mapping()
    if not pairs:
        print("The owners list is already gone from "
              f"{OWNERS_PAGE}, so there is no mapping to scrub with.\n"
              "This script consumes its own source: run it on a fresh archive "
              "(python3 src/archive_mfl.py --force) or not at all.")
        return
    before = {}
    for name in sorted(os.listdir(LEGACY)):
        if name.endswith((".html", ".htm")):
            before[name] = open(f"{LEGACY}/{name}", encoding="utf-8",
                                errors="replace").read()
    expect_absent = full_personal_names(before)
    print(f"derived {len(pairs)} owner-to-team pairs from {OWNERS_PAGE}\n")
    files = sorted(f for f in os.listdir(LEGACY) if f.endswith((".html", ".htm")))
    # the owners page last, so its mapping is available while the others are done
    files = [f for f in files if f != OWNERS_PAGE] + [OWNERS_PAGE]
    total = {}
    for name in files:
        counts, _ = scrub(f"{LEGACY}/{name}", owners, pairs, founding,
                          founding_owners, dry=dry)
        if counts:
            print(f"  {name:<34} {counts}")
            for k, v in counts.items():
                total[k] = total.get(k, 0) + v
    print(f"\n{'would change' if dry else 'changed'}: {total}")
    print(f"tracking {len(expect_absent)} full names and surnames for the check")
    print("  (bare first names are not tracked: they are also NFL players' first "
          "names, and without the mapping they identify nobody)")
    if not dry:
        verify(expect_absent)


def private_names():
    """Owner name forms, from the private companion repository.

    The checks below look for owner annotations that survived the scrub, which
    means knowing the owners' short labels. Those live in private/owners.json
    (mspinola/pdl-private), so that this public file names nobody. Without it,
    those checks are skipped and the run says so.
    """
    path = f"{BASE}/private/owners.json"
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _alt(words):
    return "|".join(map(re.escape, words))


def verify(expect_absent=None):
    names = private_names()
    if names:
        dash_re = re.compile(r"--\s*(?:" + _alt(names["dash_annotations"]) + r")\b")
        paren_re = re.compile(r"\(\s*(?:" + _alt(names["paren_labels"]) + r")\s*\)")
        kw_re = re.compile(r'name=["\']keywords["\'][^>]*(?:' + _alt(names["keyword_surnames"]) + ")", re.I)
    else:
        dash_re = paren_re = kw_re = None
        print("  private/owners.json not found: the owner-label checks are skipped")
    probe = {}
    for name in sorted(os.listdir(LEGACY)):
        if not name.endswith((".html", ".htm")):
            continue
        body = open(f"{LEGACY}/{name}", encoding="utf-8", errors="replace").read()
        text = html.unescape(re.sub(r"<[^>]+>", "|", body))
        issues = []
        if dash_re and dash_re.search(text):
            issues.append("team--owner remains")
        if re.search(r"<o:(?:Author|LastAuthor)>[^<]+</o:", body):
            issues.append("document author remains")
        if kw_re and kw_re.search(body):
            issues.append("personal name in keywords")
        for sn in sorted(expect_absent or ()):
            if re.search(rf"\b{re.escape(sn)}\b", body):
                issues.append("a tracked full name or surname remains")
                break
        if paren_re and paren_re.search(text):
            issues.append("team(owner) remains")
        if issues:
            probe[name] = sorted(set(issues))
    print("\nverification:")
    if probe:
        print("  problems found:")
        for name, issues in probe.items():
            print(f"    {name}: {', '.join(issues)}")
    else:
        print("  no owner-identifying pattern or personal surname remains")

    # the collision canaries must be untouched
    joined = ""
    for name in os.listdir(LEGACY):
        if name.endswith((".html", ".htm")):
            joined += open(f"{LEGACY}/{name}", encoding="utf-8",
                           errors="replace").read()
    joined = html.unescape(re.sub(r"<[^>]+>", " ", joined))
    missing = [c for c in COLLISION_CANARIES if c not in joined]
    print(f"  player names sharing an owner's first name, still intact: "
          f"{len(COLLISION_CANARIES) - len(missing)} of {len(COLLISION_CANARIES)}")
    for m in missing:
        print(f"    LOST: {m}")
    return not probe and not missing


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    main(dry="--dry-run" in sys.argv)
