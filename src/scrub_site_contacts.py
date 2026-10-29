"""Remove owners' contact details and bare first names from the legacy site.

The first scrub (scrub_site.py) removed owner names in the shapes they take on
the league pages. It left three things this one handles:

1. pdl/setup/contact.html, the owner directory: every line of it is a name, an
   email address or a phone number, so it is replaced by a short notice. The
   original goes to the private repository, private/legacy_site/.
2. Email addresses and phone numbers anywhere else. The saved MyFantasyLeague
   pages from 2009 and 2013 to 2015 carry the whole league's addresses in their
   "Email to Entire League" menu links. MyFantasyLeague's own addresses stay.
3. Owner first names in prose ("Thanks <name>!") and owner labels in brackets
   after a team name, as the 2002 waiver page writes them.

Names come from private/owners.json, so this file names nobody. ffl/ is left
alone, as before.

    python3 src/scrub_site_contacts.py ~/code/mspinola-site --dry-run
    python3 src/scrub_site_contacts.py ~/code/mspinola-site --apply
"""
import glob, json, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_no_owner_names import TEAMS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTACT = "pdl/setup/contact.html"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\b\d{3}[-. )]\d{3}[-.]\d{4}\b")
KEEP_DOMAINS = ("myfantasyleague.com",)

NOTICE = """<!doctype html>
<html><head><meta charset="utf-8"><title>PDL contacts</title></head>
<body style="font-family: Arial, sans-serif; margin: 2em;">
<h2>PDL owner contacts</h2>
<p>The owner contact list has been removed from the public site.
League members can get it from the commissioner.</p>
<p><a href="../../index.html">Back to the PDL site</a></p>
</body></html>
"""


def names():
    with open(f"{BASE}/private/owners.json") as f:
        return json.load(f)


def patterns(n):
    parts = {w for o in n["owners"] for w in re.split(r"[\s/&]+", o)
             if len(w) >= 3 and w[0].isupper()} | set(n.get("later_first_names", []))
    alt = "|".join(map(re.escape, sorted(parts)))
    # the same player-form exclusions as check_no_owner_names.py
    bare = re.compile(rf"(?<![A-Za-z],)(?<![A-Za-z], )(?<!\b[A-Z] )(?<!\b[A-Z]\. )\b(?:{alt})\b"
                      r"(?!\s+[A-Z][a-z]+)(?!\s*[A-Z]\.)(?!\s*,\s*[A-Z])(?!-)(?!\s+[A-Z]\s)")
    labels = sorted(parts | set(n["paren_labels"]) | set(n["dash_annotations"]), key=len, reverse=True)
    paren = re.compile(rf"((?:{TEAMS})\s*)\(\s*(?:{'|'.join(map(re.escape, labels))})(?:\s+[A-Z])?\s*(?=[)/])")
    allowed = re.compile("|".join(map(re.escape, n.get("allowed_phrases", []))) or r"(?!)")
    return bare, paren, allowed, alt


def personal(addr):
    return not addr.lower().endswith(KEEP_DOMAINS)


def strip_contacts(body, counts):
    def mailto(m):
        addrs = [a for a in re.split(r"[,;]", m.group(1)) if a]
        kept = [a for a in addrs if not EMAIL.fullmatch(a) or not personal(a)]
        counts["email"] = counts.get("email", 0) + len(addrs) - len(kept)
        return "mailto:" + ",".join(kept)
    body = re.sub(r"mailto:([^?\"';\s<>]*)", mailto, body)

    def loose(m):
        if not personal(m.group(0)):
            return m.group(0)
        counts["email"] = counts.get("email", 0) + 1
        return "[email removed]"
    body = EMAIL.sub(loose, body)
    body, n = PHONE.subn("[phone removed]", body)
    if n:
        counts["phone"] = counts.get("phone", 0) + n
    return body


def redact_text(body, bare, paren, allowed, alt, counts):
    """Owner names in the page text only, never inside tags or scripts."""
    out, pos = [], 0
    for m in re.finditer(r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>", body, re.S | re.I):
        out.append(("text", body[pos:m.start()]))
        out.append(("tag", m.group(0)))
        pos = m.end()
    out.append(("text", body[pos:]))
    done = []
    for kind, chunk in out:
        if kind == "text" and chunk.strip():
            keep = {}

            def protect(m):
                k = f"\x00{len(keep)}\x00"
                keep[k] = m.group(0)
                return k
            chunk = allowed.sub(protect, chunk)
            chunk, a = paren.subn(lambda m: m.group(1) + "([owner]", chunk)
            chunk, b = bare.subn("[owner]", chunk)
            # a first name an earlier pass left beside its redacted surname
            chunk, c = re.subn(rf"\b(?:{alt})-\[owner\]", "[owner]", chunk)
            b += c
            for k, v in keep.items():
                chunk = chunk.replace(k, v)
            if a or b:
                counts["name"] = counts.get("name", 0) + a + b
        done.append(chunk)
    return "".join(done)


def main(site, apply):
    n = names()
    bare, paren, allowed, alt = patterns(n)
    changed, total = {}, {}
    for path in sorted(glob.glob(f"{site}/**/*.htm*", recursive=True)):
        rel = os.path.relpath(path, site)
        if rel.startswith("ffl/") or rel == CONTACT:
            continue
        body = open(path, encoding="utf-8", errors="surrogateescape").read()
        counts = {}
        new = redact_text(strip_contacts(body, counts), bare, paren, allowed, alt, counts)
        if new != body:
            changed[rel] = counts
            for k, v in counts.items():
                total[k] = total.get(k, 0) + v
            if apply:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(new)
    contact = f"{site}/{CONTACT}"
    if os.path.exists(contact) and open(contact, errors="replace").read() != NOTICE:
        changed[CONTACT] = {"replaced with a notice": 1}
        if apply:
            keep = f"{BASE}/private/legacy_site/{CONTACT.replace('/', '_')}"
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            if not os.path.exists(keep):   # never replace the original with a notice
                shutil.copy2(contact, keep)
            with open(contact, "w", encoding="utf-8") as f:
                f.write(NOTICE)
    for rel, c in changed.items():
        print(f"  {rel}: {c}")
    print(f"{'changed' if apply else 'would change'} {len(changed)} files: {total}")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] not in ("--dry-run", "--apply"):
        print(__doc__)
        sys.exit(2)
    main(os.path.expanduser(sys.argv[1]), sys.argv[2] == "--apply")
