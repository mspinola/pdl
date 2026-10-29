"""Compare the four surviving editions of the rule book, section by section.

The legacy site kept four copies of the rules, none of them dated in its text:

| Edition | Archived as | Dated by |
|---|---|---|
| web page | `legacy/setup_PDL_Rules.htm` | saved from Word on 2004-06-30 (its own metadata) |
| old Word | `legacy/rules_old_PDL_Rules_doc.txt` | nothing internal |
| Word | `legacy/rules_PDL_Rules_doc.txt` | nothing internal |
| PDF | `legacy/rules_PDL_Rules_pdf.txt` | created 2006-09-24, modified 2006-10-17 |

This splits each into its numbered sections and measures how far each section
differs between editions, which orders the undated ones and says which is the
latest text, the baseline the rule changes are layered onto.

    python3 src/rulebook_editions.py      # writes docs/rulebook/editions.md
"""
import difflib, html, os, re, sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEG = f"{BASE}/mfl_archive/legacy"

EDITIONS = [  # oldest first, as far as the dates say
    ("htm", "web page, 2004", "setup_PDL_Rules.htm"),
    ("old_doc", "old Word", "rules_old_PDL_Rules_doc.txt"),
    ("doc", "Word", "rules_PDL_Rules_doc.txt"),
    ("pdf", "PDF, 2006", "rules_PDL_Rules_pdf.txt"),
]

HEAD_RE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d)\s+([A-Z][A-Za-z/&'(). -]{2,90}?)\s*(?:\.{3,}\s*\d+|\t\s*PAGEREF[^\n]*|\n)")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.skip += 1
        if tag in ("p", "br", "div", "h1", "h2", "h3", "li", "tr"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def text_of(name):
    raw = open(f"{LEG}/{name}", encoding="utf-8", errors="replace").read()
    if name.endswith(".htm"):
        p = _Text()
        p.feed(raw)
        raw = "".join(p.out)
    raw = html.unescape(raw).replace("\xa0", " ").replace("\r", "\n")
    return re.sub(r"[ \t]*\n[ \t]*", "\n", raw)


def toc(text):
    """Section numbers and titles from the table of contents."""
    out = {}
    for m in HEAD_RE.finditer(text):
        num = f"{m.group(1)}.{m.group(2)}"
        if num in out:
            break  # the body has started
        out[num] = re.sub(r"\s+", " ", m.group(3)).strip(" .")
    return out


def sections(text, canonical=None):
    """{number: (title, body words)} for the body, after the contents.

    `canonical` supplies full titles for a contents page that cut one short,
    as the web page's does where 10.1 wraps onto a second line.
    """
    titles = toc(text)
    for num, full in (canonical or {}).items():
        if num in titles and full.startswith(titles[num]) and full != titles[num]:
            titles[num] = full
    first = "1.1"
    starts = [m.start() for m in re.finditer(r"1\.1\s+Purpose", text)]
    body = text[starts[1] if len(starts) > 1 else starts[0]:]
    body = text[text.rfind("1.0", 0, len(text) - len(body)):] if "1.0 Introduction" in text else body
    marks = []
    for num, title in titles.items():
        pat = re.escape(num) + r"\s+" + r"\s+".join(map(re.escape, title.split()))
        m = re.search(pat, body)
        if not m and num.endswith(".0"):
            m = re.search(r"(?<![\d.])" + re.escape(num) + r"\s+" + re.escape(title.split()[0]), body)
        if not m:
            # a heading with no number in the body, as the Word edition's 10.8
            m = re.search(r"\n" + r"\s+".join(map(re.escape, title.split())) + r"\n", body)
        if m:
            marks.append((m.start(), m.end(), num, title))
    marks.sort()
    out = {}
    for i, (s, e, num, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        out[num] = (title, clean(body[e:end]))
    del first
    return out


def clean(chunk):
    """Section text without what only the layout put there."""
    t = re.sub(r'HYPERLINK\s+"[^"]*"', " ", chunk)            # Word field codes
    t = re.sub(r"\bPAGE\s+\d+(\s+PAGE\s+\d+)?", " ", t)
    t = re.sub(r"www\.pdlreport\.com\s+\d+\b", " ", t)        # PDF running footer
    t = re.sub(r"(?m)^\s*www\.pdlreport\.com\s*$", " ", t)
    t = re.sub(r"[\x07\u2022\ufffd\uf0b7]", " ", t)               # Word cell marks, bullets
    t = re.sub(r"(?<![\w.$])\d{1,2}\.(?=\s)", " ", t)           # list numbers, which only some editions kept
    return re.sub(r"\s+", " ", t).strip()


def ratio(a, b):
    return difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False).ratio()


def changed_words(a, b, limit=12):
    """The word-level edits from a to b, as short phrases."""
    sa, sb = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        old, new = " ".join(sa[i1:i2]), " ".join(sb[j1:j2])
        out.append((op, old[:140], new[:140]))
    return out[:limit], len(out)


def main():
    canonical = toc(text_of("rules_PDL_Rules_doc.txt"))
    eds = {k: sections(text_of(f), canonical) for k, _, f in EDITIONS}
    nums = sorted({n for s in eds.values() for n in s}, key=lambda n: tuple(map(int, n.split("."))))
    keys = [k for k, _, _ in EDITIONS]
    label = {k: lab for k, lab, _ in EDITIONS}

    lines = ["# The rule book editions, compared", "",
             "Generated by `python3 src/rulebook_editions.py` from the four editions in",
             "`mfl_archive/legacy/`. Do not edit by hand: re-run the script.", ""]
    lines += ["| Edition | Sections found | Words |", "|---|---|---|"]
    for k in keys:
        lines.append(f"| {label[k]} | {len(eds[k])} | {sum(len(w.split()) for _, w in eds[k].values()):,} |")

    pairs = list(zip(keys, keys[1:]))
    lines += ["", "## How close each pair is", "",
              "Share of words in common, across every section the two share (1.00 means identical).", "",
              "| | " + " | ".join(label[k] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for a in keys:
        row = []
        for b in keys:
            common = [n for n in nums if n in eds[a] and n in eds[b]]
            ta = " ".join(eds[a][n][1] for n in common)
            tb = " ".join(eds[b][n][1] for n in common)
            row.append(f"{ratio(ta, tb):.3f}")
        lines.append(f"| {label[a]} | " + " | ".join(row) + " |")

    lines += ["", "## Section by section", "",
              "Similarity of each section to the previous edition's (a dash: the section is absent).", "",
              "| Section | " + " | ".join(label[k] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for n in nums:
        title = next(eds[k][n][0] for k in reversed(keys) if n in eds[k])
        cells = []
        prev = None
        for k in keys:
            if n not in eds[k]:
                cells.append("-")
            elif prev is None or n not in eds[prev]:
                cells.append(f"{len(eds[k][n][1].split())}w")
            else:
                r = ratio(eds[prev][n][1], eds[k][n][1])
                cells.append("same" if r > 0.995 else f"{r:.2f}")
            prev = k
        lines.append(f"| {n} {title} | " + " | ".join(cells) + " |")

    lines += ["", "## What changed between consecutive editions", ""]
    for a, b in pairs:
        lines += [f"### {label[a]} to {label[b]}", ""]
        for n in nums:
            if n in eds[a] and n in eds[b]:
                edits, total = changed_words(eds[a][n][1], eds[b][n][1])
                real = [(op, o, w) for op, o, w in edits if re.sub(r"\W", "", o.lower()) != re.sub(r"\W", "", w.lower())]
                if not real:
                    continue
                lines.append(f"- **{n} {eds[b][n][0]}** ({total} edit{'s' if total != 1 else ''})")
                for op, o, w in real:
                    o, w = o.replace("|", "/"), w.replace("|", "/")
                    if op == "replace":
                        lines.append(f"  - `{o}` became `{w}`")
                    elif op == "delete":
                        lines.append(f"  - removed `{o}`")
                    else:
                        lines.append(f"  - added `{w}`")
            elif n in eds[b]:
                lines.append(f"- **{n} {eds[b][n][0]}** is new ({len(eds[b][n][1].split())} words)")
            elif n in eds[a]:
                lines.append(f"- **{n} {eds[a][n][0]}** is gone")
        lines.append("")

    out = f"{BASE}/docs/rulebook/editions.md"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {os.path.relpath(out, BASE)}")
    for k in keys:
        print(f"  {label[k]:15} {len(eds[k]):3} sections")
    return eds


if __name__ == "__main__":
    main()
