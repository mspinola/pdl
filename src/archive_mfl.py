"""Take a complete, self-sufficient snapshot of the league's MyFantasyLeague data.

The point is independence: once this has run, nothing here needs MyFantasyLeague
again. The league's own 2000 to 2002 seasons already survive only because they
were archived, since the spinola.co links MFL's history block points at no
longer resolve, so the risk is not hypothetical.

Layout, one directory per season:

    mfl_archive/leagues.json          year -> league id, which MFL itself only
                                      exposes through the current season
    mfl_archive/<year>/<kind>.json    the response exactly as MFL returned it
    mfl_archive/manifest.json         every file with its size, sha256 and when
                                      it was captured

Responses are stored verbatim, never reshaped. Everything the site and the
analysis show is derived from these files, so a change in how we read the data
never costs us the data. The manifest's hashes make a silent change or a
truncated download detectable later.

What MFL will not give up, and so is not here: the message board, the league
calendar and polls all require a logged-in commissioner. If that history
matters it has to be saved from the site by hand while the league still exists.
"""
import hashlib, json, os, shutil, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_mfl import LEAGUES, UA

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{BASE}/raw"
ARCHIVE = f"{BASE}/mfl_archive"

# kind -> export parameters. Everything that is league history; nothing that is
# transient NFL-wide data (injuries, free agents, MFL's own news feed).
KINDS = {
    "league": {"TYPE": "league"},
    "standings": {"TYPE": "standings"},
    "schedule": {"TYPE": "schedule"},
    "rosters": {"TYPE": "rosters"},
    "transactions": {"TYPE": "transactions"},
    "transactions_trade": {"TYPE": "transactions", "TRANS_TYPE": "TRADE"},
    "draft_results": {"TYPE": "draftResults"},
    "future_draft_picks": {"TYPE": "futureDraftPicks"},
    "player_scores": {"TYPE": "playerScores"},
    "weekly_results": {"TYPE": "weeklyResults", "W": "ALL"},
    "rules": {"TYPE": "rules"},
    "players": {"TYPE": "players", "DETAILS": 0},
    "playoff_bracket_1": {"TYPE": "playoffBracket", "BRACKET_ID": 1},
    "playoff_bracket_2": {"TYPE": "playoffBracket", "BRACKET_ID": 2},
    "playoff_bracket_3": {"TYPE": "playoffBracket", "BRACKET_ID": 3},
}

# files already fetched by the other scripts, reused rather than asked for again
REUSE = {
    "league": "league_{y}.json",
    "schedule": "schedule_{y}.json",
    "rosters": "rosters_{y}.json",
    "transactions_trade": "trades_{y}.json",
    "players": "players_{y}.json",
    "playoff_bracket_1": "bracket_{y}_1.json",
    "playoff_bracket_2": "bracket_{y}_2.json",
    "playoff_bracket_3": "bracket_{y}_3.json",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(year, params):
    url = f"https://api.myfantasyleague.com/{year}/export?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace"), url


def capture(year, lid, kind, params, force=False):
    out_dir = f"{ARCHIVE}/{year}"
    os.makedirs(out_dir, exist_ok=True)
    dest = f"{out_dir}/{kind}.json"
    if os.path.exists(dest) and os.path.getsize(dest) > 2 and not force:
        return "have", None

    reuse = REUSE.get(kind)
    src = f"{RAW}/{reuse.format(y=year)}" if reuse else None
    if src and os.path.exists(src) and os.path.getsize(src) > 2:
        shutil.copyfile(src, dest)
        return "reused", None

    body, url = fetch(year, {**params, "L": lid, "JSON": 1})
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return "badjson", str(e)
    note = None
    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        note = err.get("$t") if isinstance(err, dict) else str(err)
    with open(dest, "w") as f:
        f.write(body)
    time.sleep(1.0)
    return ("error" if note else "fetched"), note


# The league's own pages, which are the only source for the seasons MFL has
# nothing for. These matter more than the MFL half: the spinola.co copies MFL
# links to are already gone. The whole legacy site lives in the mspinola/mspinola
# repository; captured here are the pages this pipeline actually reads, plus the
# few that are the sole record of something.
LEGACY_BASE = "https://mspinola.github.io/mspinola/pdl"
LEGACY = [
    "history/trades.html",        # the only pre-2008 trade log
    "history/misc.html",          # champions 2000-2019, and the original owners
    "history/recbook.html",       # record book
    "history/history.html",       # the index of yearly archives
    "history/orgdrft.html",       # the inaugural draft
    "history/orgrost.html",       # the original rosters
    "pdl2000/schedule.html",      # the only source for 2000-2002 results
    "pdl2001/schedule.html",
    "pdl2002/schedule.html",
    "pdl2000/standings.html",     # confirms the 14-team first season
    "pdl2001/standings.html",
    "pdl2002/standings.html",
    "pdl2001/setup/expansion.html",   # the 2001 expansion rules
    "pdl2001/setup/expdraft.html",    # the expansion draft
    "pdl2000/setup/draft.html",       # the drafts MFL has nothing for
    "pdl2001/setup/draft.html",
    "pdl2002/setup/draft.html",
    "pdl2003/setup/draft.html",
    "pdl2004/setup/draft.html",
    "pdl2006/setup/draft.html",
    # The rules record, which matters most of anything here. changes.html is
    # the proposals log, 2002 to the 2023 summer meeting. PDL_Rules.htm is the
    # rule book as Word exported it in 2004.
    "setup/changes.html",
    "pdl2002/setup/changes2002.html",
    "setup/PDL_Rules.htm",
]

# The rule book's Word and PDF editions. Only their text is kept, extracted
# here: the files themselves carry an author in their metadata, and this
# repository is public. The manifest records each source file's hash and its
# own dates, so the provenance survives even though the file does not.
RULE_BOOKS = [
    ("setup/PDL_Rules.pdf", "rules_PDL_Rules_pdf.txt"),     # 2006, the edition the season pages link
    ("setup/PDL_Rules.doc", "rules_PDL_Rules_doc.txt"),
    ("setup/old_PDL_Rules.doc", "rules_old_PDL_Rules_doc.txt"),
]


def capture_legacy(force=False):
    out_dir = f"{ARCHIVE}/legacy"
    os.makedirs(out_dir, exist_ok=True)
    tally, notes = {}, []
    for rel in LEGACY:
        dest = f"{out_dir}/{rel.replace('/', '_')}"
        if os.path.exists(dest) and os.path.getsize(dest) > 200 and not force:
            tally["have"] = tally.get("have", 0) + 1
            continue
        url = f"{LEGACY_BASE}/{rel}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            notes.append((rel, str(e)))
            tally["failed"] = tally.get("failed", 0) + 1
            continue
        if "Page not found" in body and "GitHub Pages" in body:
            notes.append((rel, "404 on the GitHub Pages site"))
            tally["missing"] = tally.get("missing", 0) + 1
            continue
        open(dest, "w", encoding="utf-8").write(body)
        tally["fetched"] = tally.get("fetched", 0) + 1
        time.sleep(0.8)
    return tally, notes


def capture_rule_books(force=False):
    """Download each rule book edition, keep its text, discard the file."""
    import subprocess, tempfile
    out_dir = f"{ARCHIVE}/legacy"
    os.makedirs(out_dir, exist_ok=True)
    provenance, notes = {}, []
    for rel, dest_name in RULE_BOOKS:
        dest = f"{out_dir}/{dest_name}"
        url = f"{LEGACY_BASE}/{rel}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                blob = r.read()
        except Exception as e:  # noqa: BLE001
            notes.append((rel, str(e)))
            continue
        info = {"source": url, "source_bytes": len(blob),
                "source_sha256": hashlib.sha256(blob).hexdigest()}
        if os.path.exists(dest) and os.path.getsize(dest) > 200 and not force:
            provenance[dest_name] = {**info, **_dates(blob, rel)}
            continue
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, os.path.basename(rel))
            with open(src, "wb") as f:
                f.write(blob)
            txt = os.path.join(tmp, "out.txt")
            if rel.endswith(".pdf"):
                cmd = ["pdftotext", "-layout", src, txt]
            else:
                # textutil ships with macOS; elsewhere use antiword or LibreOffice
                cmd = ["textutil", "-convert", "txt", "-output", txt, src]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except (OSError, subprocess.CalledProcessError) as e:
                notes.append((rel, f"text extraction failed ({cmd[0]}): {e}"))
                continue
            text = open(txt, encoding="utf-8", errors="replace").read()
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        provenance[dest_name] = {**info, **_dates(blob, rel), "words": len(text.split())}
        time.sleep(0.8)
    return provenance, notes


def _dates(blob, rel):
    """The edition's own dates, which are not the date it was committed."""
    import re as _re
    out = {}
    if rel.endswith(".pdf"):
        for key in ("CreationDate", "ModDate"):
            m = _re.search(rb"/" + key.encode() + rb"\s*\(D:(\d{8})", blob)
            if m:
                d = m.group(1).decode()
                out[key] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return out


def main(force=False):
    os.makedirs(ARCHIVE, exist_ok=True)
    with open(f"{ARCHIVE}/leagues.json", "w") as f:
        json.dump({str(y): l for y, l in sorted(LEAGUES.items())}, f, indent=1)

    ltally, lnotes = capture_legacy(force=force)
    print(f"  legacy pages: {ltally}")
    for rel, note in lnotes:
        print(f"    {rel}: {note}")
    rule_provenance, rnotes = capture_rule_books(force=force)
    print(f"  rule book editions as text: {len(rule_provenance)} of {len(RULE_BOOKS)}")
    for rel, note in rnotes:
        print(f"    {rel}: {note}")

    tally, notes = {}, []
    for year, lid in sorted(LEAGUES.items()):
        marks = []
        for kind, params in KINDS.items():
            try:
                state, note = capture(year, lid, kind, params, force=force)
            except Exception as e:  # noqa: BLE001
                state, note = "failed", str(e)
            tally[state] = tally.get(state, 0) + 1
            marks.append(f"{kind}:{state[0]}")
            if note:
                notes.append((year, kind, state, note))
        print(f"  {year}  " + " ".join(marks))

    manifest = {
        "league": "PDL",
        "captured": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "MyFantasyLeague export API",
        "note": ("Responses stored verbatim. Everything derived is rebuilt from "
                 "these files. Not available without a commissioner login, and "
                 "therefore absent: message board, calendar, polls."),
        "seasons": {},
    }
    total = 0
    for year in sorted(LEAGUES):
        d = f"{ARCHIVE}/{year}"
        if not os.path.isdir(d):
            continue
        files = {}
        for name in sorted(os.listdir(d)):
            p = f"{d}/{name}"
            size = os.path.getsize(p)
            total += size
            files[name] = {"bytes": size, "sha256": sha256(p)}
        manifest["seasons"][str(year)] = {"league_id": LEAGUES[year], "files": files}
    legacy_dir = f"{ARCHIVE}/legacy"
    if os.path.isdir(legacy_dir):
        files = {}
        for name in sorted(os.listdir(legacy_dir)):
            p = f"{legacy_dir}/{name}"
            size = os.path.getsize(p)
            total += size
            files[name] = {"bytes": size, "sha256": sha256(p)}
        manifest["legacy"] = {
            "source": LEGACY_BASE,
            "note": ("The league's own pages, the only source for the seasons "
                     "MFL has nothing for, and the rules record."),
            "files": files,
            "rule_book_provenance": rule_provenance,
        }
    manifest["total_bytes"] = total
    manifest["total_files"] = (sum(len(s["files"]) for s in manifest["seasons"].values())
                               + len(manifest.get("legacy", {}).get("files", {})))
    with open(f"{ARCHIVE}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)

    print(f"\n{tally}")
    print(f"archive: {manifest['total_files']} files, {total / 1024 / 1024:.1f} MB "
          f"across {len(manifest['seasons'])} seasons")
    if notes:
        print(f"\nendpoints MFL declined or has nothing for ({len(notes)}):")
        seen = {}
        for year, kind, state, note in notes:
            seen.setdefault((kind, note[:60]), []).append(year)
        for (kind, note), years in sorted(seen.items()):
            span = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
            print(f"  {kind} [{span}]: {note}")


def verify():
    """Check every archived file against the manifest."""
    m = json.load(open(f"{ARCHIVE}/manifest.json"))
    bad, checked = [], 0
    for year, season in m["seasons"].items():
        for name, rec in season["files"].items():
            p = f"{ARCHIVE}/{year}/{name}"
            if not os.path.exists(p):
                bad.append(f"missing {year}/{name}")
                continue
            checked += 1
            if os.path.getsize(p) != rec["bytes"]:
                bad.append(f"size changed {year}/{name}")
            elif sha256(p) != rec["sha256"]:
                bad.append(f"content changed {year}/{name}")
    for name, rec in m.get("legacy", {}).get("files", {}).items():
        p = f"{ARCHIVE}/legacy/{name}"
        if not os.path.exists(p):
            bad.append(f"missing legacy/{name}")
            continue
        checked += 1
        if os.path.getsize(p) != rec["bytes"]:
            bad.append(f"size changed legacy/{name}")
        elif sha256(p) != rec["sha256"]:
            bad.append(f"content changed legacy/{name}")
    print(f"verified {checked} files against the manifest captured {m['captured']}")
    print("  " + ("all match" if not bad else f"{len(bad)} problems:"))
    for b in bad:
        print(f"    {b}")
    return not bad


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    main(force="--force" in sys.argv)
