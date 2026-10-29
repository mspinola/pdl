"""Remove owner names from the league's legacy website.

A companion to `scrub_owners.py`, which handles the small set of pages copied
into this repository's archive. This one walks the whole site checkout
(mspinola/mspinola) and handles the shapes that only appear there.

As with its sibling, it holds **no names of its own**. Everything is derived at
run time from the site's own pages: the owners list gives label-to-team, the
original rosters page and the MyFantasyLeague-saved pages give full names.

Six shapes carry owner names on that site:

1. `title="Owner: <Full Name>"` on the pages saved from MyFantasyLeague, which
   is far and away the most common
2. `<meta name="keywords">`, which repeats the site author on nearly every page
3. document authorship Word left in exported spreadsheets and draft boards
4. `Team (Owner)` in the owners list
5. `Team -- Owner`, `Owner's Team`, and cells that are exactly an owner label,
   as handled for the archived copies
6. owner full names as column headers on the original rosters page

**The FFL directory is left alone, deliberately.** That is a different league
whose team names are built from its owners' surnames: "Farmerie's Farmers",
"Arenth's Armada". There is no way to remove the names without renaming the
teams, which would destroy the content rather than anonymise it. Scrubbing it
is a separate decision, so this script refuses to touch it unless asked.

The same hazard as the sibling script applies and is checked the same way:
owner surnames collide with NFL players, and the pages list players as
"McCardell, Keenan". Nothing is matched on a bare name in running text.
"""
import html, os, re, sys

TEXT_EXT = {".html", ".htm", ".mht", ".xml", ".txt", ".css", ".js", ".yml"}
NEUTRAL_KEYWORDS = "fantasy football, PDL, dynasty league"

CANARIES = ["McCardell, Keenan", "Hasselbeck, Matt", "Vanderjagt, Mike"]


def read(path):
    return open(path, encoding="utf-8", errors="replace").read()


def derive(root):
    """owner label -> team, and the set of owner full names, from the site."""
    misc = os.path.join(root, "pdl/history/misc.html")
    pairs, founding = {}, {}
    if os.path.exists(misc):
        text = html.unescape(re.sub(r"<[^>]+>", "|", read(misc)))
        split = re.search(r"\|[^|]*Expansion Owners[^|]*\|", text)
        head, tail = ((text[:split.start()], text[split.start():]) if split
                      else (text, ""))
        for section, store in ((head, founding), (tail, None)):
            for m in re.finditer(r"\|\s*([A-Za-z][A-Za-z'\- ]+?)\s*\(([^)]+)\)", section):
                team, owner = m.group(1).strip(), m.group(2).strip()
                pairs[owner] = team
                if store is not None:
                    store[owner] = team

    fulls = set()
    # the MFL-saved pages state the owner outright
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, "pdl")):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            body = read(os.path.join(dirpath, name))
            for m in re.finditer(r"Owner:\s*([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,2})",
                                 body):
                fulls.add(m.group(1).strip())
    org = os.path.join(root, "pdl/history/orgrost.html")
    if os.path.exists(org):
        for m in re.finditer(r"(>)([^<>]{3,40}?)(<)", read(org)):
            lab = html.unescape(m.group(2)).strip()
            if "," in lab or lab.startswith("Over Def"):
                continue
            if re.fullmatch(r"[A-Z][A-Za-z'\-]+(?:\s+(?:and\s+)?[A-Z][A-Za-z'\-]+){1,2}", lab):
                fulls.add(lab)
    # surnames, and the first names that appear beside them. The owners list
    # gives first names only, so a full name it never spelled out ("<first>
    # <surname>" for the pair who share a franchise) is only reachable this way.
    surnames = {f.split()[-1] for f in fulls if len(f.split()[-1]) > 4}
    # A surname that NFL players also carry cannot be redacted on its own: one
    # of these owners shares a surname with a receiver who appears on hundreds
    # of pages. Detected by looking for the surname in the "Lastname, Firstname"
    # position the player tables use, with page metadata stripped first because
    # the author's own name sits in every keywords tag.
    meta = re.compile(r"<meta[^>]*>|<title>[^<]*</title>"
                      r"|<o:(?:Author|LastAuthor|Company|Manager)>[^<]*</o:[^>]*>", re.I)
    sample = ""
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, "pdl")):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in TEXT_EXT:
                sample += meta.sub(" ", read(os.path.join(dirpath, name)))
    # three or more, so that one incidental match does not needlessly spare a
    # surname. The one real collision runs to the hundreds.
    colliding = {sn for sn in surnames
                 if len(re.findall(r",\s*" + re.escape(sn) + r"\b", sample)) >= 3}
    surnames_alone = surnames - colliding
    firsts = set()
    for owner in pairs:
        for part in re.split(r"\s+and\s+|/|&", owner):
            part = part.strip()
            if len(part) > 2:
                firsts.add(part)
    return pairs, founding, fulls, surnames, surnames_alone, firsts


def label_keys(owner):
    keys = {owner}
    parts = [p.strip() for p in re.split(r"\s+and\s+|/|&", owner) if p.strip()]
    keys.update(parts)
    keys.add(" / ".join(parts))
    keys.add(" and ".join(parts))
    if len(parts) == 1 and " " in owner:
        first, last = owner.split()[0], owner.split()[-1]
        keys.update({f"{first} {last[0]}", last, first})
    return keys


def label_map(pairs):
    out = {}
    for owner, team in pairs.items():
        for k in label_keys(owner):
            k = k.lower()
            if k in out and out[k] != team:
                out[k] = None
            else:
                out.setdefault(k, team)
    return {k: v for k, v in out.items() if v}


def truncatable(team, min_len=8):
    """A pattern matching the team name or any prefix of it at least min_len long.

    These pages truncate team names to fit fixed-width cells, so the possessive
    and double-dash shapes appear against "Karpet Muncher" as well as the full
    "Karpet Munchers". Without this the owner's name survives beside the
    shortened team name.
    """
    if len(team) <= min_len:
        return re.escape(team)
    head = re.escape(team[:min_len])
    tail = team[min_len:]
    return head + "".join(f"(?:{re.escape(c)}" for c in tail) + ")?" * len(tail)


def team_for(label, owners):
    """An exact label match at any length, or a prefix match at four or more.

    The length floor is what keeps NFL team abbreviations out of it. These
    pages are full of three-letter codes, and a prefix rule without the floor
    reads "Phi" as Philadelphia's owner and "Sea" as Seattle's, which would
    rewrite every abbreviation on the site. Four characters is enough for the
    truncations that do appear in fixed-width tables, where an owner's label is
    cut to its first four letters.
    """
    key = re.sub(r"[.\s]+", " ", label).strip().lower().strip("'")
    if not key:
        return None
    if key in owners:
        return owners[key]
    if " " in key or len(key) < 4:
        return None
    for k, team in owners.items():
        if " " in k or len(k) < 4:
            continue
        if (k.startswith(key) or key.startswith(k)) and abs(len(key) - len(k)) <= 2:
            return team
    return None


def scrub_file(path, owners, founding_owners, pairs, fulls, surnames,
               surnames_alone, firsts, is_rosters):
    body = read(path)
    original = body
    counts = {}

    def bump(k, n=1):
        if n:
            counts[k] = counts.get(k, 0) + n

    # 1. "Owner: <Full Name>" wherever it appears, including inside attributes.
    #    The whole clause goes, with its separator, so a tooltip reads
    #    "Record: 6-7-0" rather than "Owner:, Record: 6-7-0".
    name = r"[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,2}"
    body, n = re.subn(rf"Owner:\s*{name},\s*", "", body)
    bump("ownerAttr", n)
    body, n = re.subn(rf"Owner:\s*{name}", "", body)
    bump("ownerAttr", n)

    # 2. page keywords, which repeat the author on nearly every page
    body, n = re.subn(r'(<meta\s+name=["\']keywords["\']\s+content=["\'])[^"\']*(["\'])',
                      rf"\g<1>{NEUTRAL_KEYWORDS}\g<2>", body, flags=re.I)
    bump("meta", n)
    body, n = re.subn(r'(<meta\s+name=["\']author["\']\s+content=["\'])[^"\']*(["\'])',
                      r"\g<1>\g<2>", body, flags=re.I)
    bump("meta", n)

    # 3. document authorship from Word exports
    body, n = re.subn(r"<o:(Author|LastAuthor|Company|Manager)>[^<]*</o:\1>",
                      r"<o:\1></o:\1>", body)
    bump("docmeta", n)

    # 4. "Team (Owner)" in the owners list
    for owner in pairs:
        for variant in {owner, html.escape(owner)}:
            body, n = re.subn(r"\s*\(\s*" + re.escape(variant) + r"\s*\)", "", body)
            bump("paren", n)

    # 4b. a parenthetical that holds an owner reference, whatever the team
    #     beside it is spelled like
    if surnames:
        sur = "|".join(re.escape(x) for x in sorted(surnames, key=len, reverse=True))
        firstalt = "|".join(re.escape(x) for x in sorted(firsts, key=len, reverse=True))
        body, n = re.subn(rf"\s*\(\s*(?:(?:{firstalt})\s+)?(?:{sur})\s*\)", "", body)
        bump("paren", n)

    # 5a. a possessive prefix on a real team name, which may be truncated
    teams = sorted(set(pairs.values()), key=len, reverse=True)
    for team in teams:
        body, n = re.subn(r"\b[A-Z][A-Za-z]+'s\s+(" + truncatable(team) + r")",
                          r"\1", body)
        bump("possessive", n)

    # 5a2. "<Owner surname> - <Team>", which is how one Word-exported page
    #      writes the mapping outright. This runs for every surname, the
    #      colliding one included, because a team name beside it settles that
    #      it is the owner and not a player.
    if surnames:
        sur = "|".join(re.escape(x) for x in sorted(surnames, key=len, reverse=True))
        for team in teams:
            body, n = re.subn(rf"\b(?:{sur})\s*[^\w<>]{{1,4}}\s*({truncatable(team)})",
                              r"\1", body)
            bump("mapping", n)

    # 5b. "Team -- Owner", anchored on the team name
    tail = r"(?!at\b|vs\b)[A-Za-z/.'&]{1,10}"
    for team in teams:
        body, n = re.subn(r"(" + truncatable(team) + r")\s*--\s*" + tail
                          + r"(?:\s+" + tail + r")?", r"\1", body)
        bump("suffix", n)

    # 5c. a cell whose whole text is an owner label
    def cell(m):
        label = html.unescape(m.group(2)).strip()
        if not label or len(label) > 24:
            return m.group(0)
        team = team_for(label, founding_owners) or team_for(label, owners)
        if team and label.lower() != team.lower():
            bump("cell")
            return f"{m.group(1)}{team}{m.group(3)}"
        return m.group(0)
    body = re.sub(r"(>)([^<>]{1,40}?)(<)", cell, body)

    # 6. owner full names as headers on the original rosters page
    if is_rosters:
        for full in sorted(fulls, key=len, reverse=True):
            team = (team_for(full.split()[0], owners)
                    or team_for(full.split()[-1], owners))
            if team:
                body, n = re.subn(r"(>)\s*" + re.escape(full) + r"\s*(<)",
                                  rf"\g<1>{team}\g<2>", body)
                bump("header", n)

    # The tail: any owner name still standing, in any position. Table cells and
    # the rosters headers are already teams by now, so what is left is running
    # text, where a team name would read wrong ("F-Jackie coach F-Jacki said").
    # So these are redacted visibly instead. A first name is only taken when it
    # sits directly before a surname, never on its own, because owner first
    # names are also NFL players' first names.
    for full in sorted(fulls, key=len, reverse=True):
        body, n = re.subn(r"\b" + re.escape(full) + r"\b", "[owner]", body)
        bump("redacted", n)
    first = "|".join(re.escape(x) for x in sorted(firsts, key=len, reverse=True))
    if surnames:
        sur = "|".join(re.escape(x) for x in sorted(surnames, key=len, reverse=True))
        # a first name immediately before a surname: safe even for the
        # colliding one, since no player is named that way here
        body, n = re.subn(rf"\b(?:{first})\s+(?:{sur})\b", "[owner]", body)
        bump("redacted", n)
    if surnames_alone:
        sur = "|".join(re.escape(x) for x in sorted(surnames_alone, key=len, reverse=True))
        body, n = re.subn(rf"\b(?:{sur})\b", "[owner]", body)
        bump("redacted", n)
        # The colliding surname is spared on its own, which leaves it standing
        # in a list of owners whose other names have already gone, as in a vote
        # tally. Beside an existing redaction it is plainly the owner, not the
        # receiver, so take it too. The span cannot cross a tag, which keeps
        # player tables out of it.
        sur_all = "|".join(re.escape(x) for x in sorted(surnames, key=len, reverse=True))
        body, n = re.subn(rf"\b(?:{sur_all})\b(?=[^<>]{{0,30}}\[owner\])", "[owner]", body)
        bump("beside_redaction", n)
        body, n = re.subn(rf"(\[owner\][^<>]{{0,30}}?)\b(?:{sur_all})\b", r"\1[owner]", body)
        bump("beside_redaction", n)

        # "[owner] [owner]" where a first name and a surname were taken apart
        body, n = re.subn(r"\[owner\](?:[\s,]+\[owner\])+", "[owner]", body)
        bump("tidied", n)

    changed = body != original
    return body if changed else None, counts


def main(root, apply=False, include_ffl=False):
    pairs, founding, fulls, surnames, surnames_alone, firsts = derive(root)
    owners = label_map(pairs)
    founding_owners = label_map(founding)
    print(f"derived {len(pairs)} owner labels, {len(fulls)} full names and "
          f"{len(surnames)} surnames from the site itself")
    print(f"  {len(surnames) - len(surnames_alone)} surname(s) are also NFL "
          f"players' names and so are only removed as part of a full name")
    if not pairs and not fulls:
        print("Nothing to derive: this site may already be scrubbed. Stopping.")
        return 1

    total, touched = {}, []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel = os.path.relpath(dirpath, root)
        if not include_ffl and (rel == "ffl" or rel.startswith("ffl" + os.sep)):
            continue
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, name)
            is_rosters = os.path.relpath(path, root) == os.path.join(
                "pdl", "history", "orgrost.html")
            new, counts = scrub_file(path, owners, founding_owners, pairs,
                                     fulls, surnames, surnames_alone, firsts,
                                     is_rosters)
            if counts and new is not None:
                touched.append((os.path.relpath(path, root), counts))
                for k, v in counts.items():
                    total[k] = total.get(k, 0) + v
                if apply:
                    open(path, "w", encoding="utf-8").write(new)

    print(f"\n{'changed' if apply else 'would change'} {len(touched)} files: {total}")
    by_shape = {}
    for rel, counts in touched:
        for k in counts:
            by_shape.setdefault(k, []).append(rel)
    for shape, files in sorted(by_shape.items()):
        print(f"  {shape:<12} {len(files):>4} files, e.g. {files[0]}")
    return 0


if __name__ == "__main__":
    root = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    if not root:
        print("usage: scrub_site.py <site root> [--apply] [--include-ffl]")
        sys.exit(2)
    sys.exit(main(root, apply="--apply" in sys.argv,
                  include_ffl="--include-ffl" in sys.argv))
