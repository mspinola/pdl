"""Refuse to publish anything that identifies an owner.

Run before committing. It checks the structural shapes an owner reference takes
in this archive, rather than a list of names, so the check itself gives nothing
away:

  "Team (Owner)"        the owners list
  "Team -- Owner"       the 2001 and 2002 schedules and standings
  "Owner's Team"        a possessive prefix on a real team name
  document authorship   what Word left in the exported draft boards
  an email address      anywhere at all

It also checks that the MyFantasyLeague half carries no owner or email field,
and that the colliding NFL player names a careless scrub would have eaten are
still present.

Shapes cannot see a bare first name in running prose ("Thanks <name>!"). When
the private companion repository is checked out at private/, its owners.json
supplies the owners' names and this adds that check too, for prose files and the
archived legacy pages. Player names in "Surname, First" or "First Surname" form
are skipped, since owners share first names with NFL players.
"""
import json, glob, html, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CANARIES = ["Matt Hasselbeck", "Keenan McCardell", "Mike Vanderjagt",
            "Tony Martin", "Chris Redman", "Mike Hollis"]

# Team names are public and are the thing we keep; they anchor the patterns so a
# tail that is itself a team name does not read as an owner.
TEAMS = (r"Manic Moose|Karpet Munchers|Da Funk|Dunbar Dogs|Tally Wackers"
         r"|Iron City Pounders|Otters|Ho Train|Bunchalosers|Couchfire"
         r"|Texas Nashvillians|Blitzkrieg|Beers|F-Jacki(?:e)?|Carter's Commandos"
         r"|Scooter's Boozers|Commandos|Boozers|Munchers|Moose|Wackers|Pounders"
         r"|Dogs|OakalDo\w*|Nashvillians|Texans")

SHAPES = [
    # "Team (Owner)", as the owners list wrote it. "(Via Team)" on a draft board
    # is a pick's provenance, not a person.
    ("team(owner)", re.compile(
        rf"(?:{TEAMS})\s*\(\s*(?!Via\b|From\b|via\b|from\b)(?!(?:{TEAMS})\b)"
        r"[A-Z][A-Za-z]{1,12}(?:\s+[A-Z][A-Za-z.]{0,12})?\s*\)")),
    # "Team -- Owner", where the tail is not itself a team name
    ("team--owner", re.compile(
        rf"(?:{TEAMS})\s*--\s*(?!(?:{TEAMS})\b)"
        r"[A-Z][A-Za-z]{1,9}(?:\s+[A-Z]\b)?(?=\s*[\d<]|\s*$)")),
    # a possessive prefix on a team name, excluding the two teams whose own
    # names begin with one
    ("owner'sTeam", re.compile(
        rf"\b[A-Z][A-Za-z]+'s\s+(?:{TEAMS})\b")),
    # document authorship, but not the empty tag the scrub leaves behind
    ("docAuthor", re.compile(r"<o:(?:Author|LastAuthor|Company|Manager)>(?!</)[^<\s]")),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")),
]

# team names that legitimately begin with a possessive
ALLOWED = re.compile(r"\b(?:Carter's Commandos|Scooter's Boozers)\b")


def tracked_files():
    out = []
    for pattern in ("mfl_archive/**/*", "datasets/*", "*.json", "*.md", "src/*"):
        for p in glob.glob(f"{BASE}/{pattern}", recursive=True):
            if os.path.isfile(p) and "/raw/" not in p and "__pycache__" not in p:
                out.append(p)
    return sorted(set(out))


# where a bare first name would be prose rather than a player list
PROSE = re.compile(r"^(mfl_archive/legacy/.*\.html?|.*\.md|docs/.*|rules/.*|src/.*\.py)$")


def private_name_check():
    """Bare owner names in prose, using the private repository's list."""
    path = f"{BASE}/private/owners.json"
    if not os.path.exists(path):
        print("private/owners.json not found: the bare-name check is skipped")
        return []
    names = json.load(open(path))
    parts = {w for o in names["owners"] for w in re.split(r"[\s/&]+", o)
             if len(w) >= 3 and w[0].isupper()} | set(names.get("later_first_names", []))
    parts |= {w for n in names.get("full_names", []) for w in n.split() if len(w) >= 3}
    alt = "|".join(map(re.escape, sorted(parts)))
    # not "Surname, First", "First Surname", "D Name" or "Name, D" (player forms)
    bare = re.compile(rf"(?<![A-Za-z],)(?<![A-Za-z], )(?<!\b[A-Z] )(?<!\b[A-Z]\. )\b(?:{alt})\b"
                      r"(?!\s+[A-Z][a-z]+)(?!\s*[A-Z]\.)(?!\s*,\s*[A-Z])(?!-)(?!\s+[A-Z]\s)")
    allowed = re.compile("|".join(map(re.escape, names.get("allowed_phrases", []))) or r"(?!)")
    found = []
    for p in tracked_files():
        rel = os.path.relpath(p, BASE)
        if not PROSE.match(rel):
            continue
        body = open(p, encoding="utf-8", errors="replace").read()
        if rel.endswith((".html", ".htm")):
            body = html.unescape(re.sub(r"<[^>]+>", " ", body))
        body = allowed.sub(" ", re.sub(r"\s+", " ", body))
        n = len(bare.findall(body))
        if n:
            found.append(f"{rel}: {n} bare owner name{'s' if n > 1 else ''} in prose")
    return found


def main():
    problems = []
    checked = 0
    for p in tracked_files():
        rel = os.path.relpath(p, BASE)
        if rel.startswith("src/check_no_owner_names"):
            continue
        try:
            body = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        checked += 1
        # collapse whitespace first: these shapes wrap across lines in both the
        # archived HTML and this project's own prose
        flat = re.sub(r"\s+", " ", body)
        stripped = ALLOWED.sub("", flat)
        for label, pattern in SHAPES:
            m = pattern.search(stripped)
            if m:
                problems.append(f"{rel}: {label} -> {m.group(0)[:60]!r}")

    franchise_keys = set()
    for p in glob.glob(f"{BASE}/mfl_archive/*/league.json"):
        fr = json.load(open(p))["league"]["franchises"]["franchise"]
        for f in (fr if isinstance(fr, list) else [fr]):
            franchise_keys.update(f.keys())
    leaky = {k for k in franchise_keys
             if re.search(r"owner|email|user|name$", k) and k != "name"}

    joined = ""
    for p in glob.glob(f"{BASE}/mfl_archive/legacy/*.html"):
        joined += open(p, encoding="utf-8", errors="replace").read()
    joined = html.unescape(re.sub(r"<[^>]+>", " ", joined))
    lost = [c for c in CANARIES if c not in joined]

    problems += private_name_check()
    print(f"checked {checked} files")
    print(f"franchise record keys: {sorted(franchise_keys)}")
    print(f"  owner-ish keys: {leaky or 'none'}")
    print(f"player names a careless scrub would eat, intact: "
          f"{len(CANARIES) - len(lost)} of {len(CANARIES)}")
    for c in lost:
        print(f"    LOST: {c}")
    if problems:
        print(f"\nFAIL: {len(problems)} owner-identifying matches")
        for x in problems[:30]:
            print(f"  {x}")
    else:
        print("\nPASS: no owner-identifying shape, no email, in anything publishable")
    return 0 if not problems and not leaky and not lost else 1


if __name__ == "__main__":
    sys.exit(main())
