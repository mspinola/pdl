"""Parse the 2006 rule book into structured sections: rules/baseline.json.

The baseline is the 2006 edition. `rulebook_editions.py` shows the Word file and
the PDF carry the same words, and that both supersede the 2004 text. The PDF's
layout extraction is parsed here because it keeps the scoring tables' rows
intact, where the Word extraction flattens them to one cell per line.

Each section becomes a list of blocks:

    {"type": "p", "text": ...}                      a paragraph
    {"type": "h", "text": ...}                      an unnumbered sub-heading
    {"type": "list", "ordered": bool, "items": [{"n": 5, "text": ...}]}
    {"type": "table", "title": ..., "columns": [...], "groups": [{"label", "rows": [{"label", "values"}]}]}

List numbers are kept as printed. 6.2 reads 1, 2, 5 because the 2002 meeting
removed items 3 and 4 and the list was never renumbered.

    python3 src/rulebook_baseline.py      # writes rules/baseline.json, then checks it
"""
import json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulebook_editions as editions

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = "rules_PDL_Rules_pdf.txt"
OUT = f"{BASE}/rules/baseline.json"

COLUMNS = ["QB", "RB", "WR", "TE", "K", "Def"]
TABLE_HEAD = re.compile(r"^\s*(\S.*?)\s+QB\s+RB\s+WR\s+TE\s+K\s+Def\s*$")
TABLE_ROW = re.compile(r"^\s*(\S.*?)\s+((?:(?:-?\d+(?:\.\d+)?|x)\s+){5}(?:-?\d+(?:\.\d+)?|x))\s*$")
FOOTER = re.compile(r"^\s*www\.pdlreport\.com\s+\d+\s*$")
ITEM = re.compile(r"^\s+(?:(\d{1,2})\.|•)\s+(.*)$")


def body_lines():
    lines = open(f"{editions.LEG}/{SOURCE}", encoding="utf-8").read().replace("\f", "\n").split("\n")
    # the contents page lists "1.0 Introduction" with leader dots, the body without
    start = next(i for i, l in enumerate(lines) if l.strip() == "1.0 Introduction")
    return [("" if FOOTER.match(l) else l.rstrip()) for l in lines[start:]]


def split_sections(lines, titles):
    heads = {f"{n} {t}": n for n, t in titles.items()}
    out, cur = {}, None
    for l in lines:
        key = re.sub(r"\s+", " ", l.strip())
        if key in heads:
            cur = heads[key]
            out[cur] = []
            continue
        if cur:
            out[cur].append(l)
    return out


def paragraphs(lines):
    """Blocks of lines separated by blank lines."""
    block, out = [], []
    for l in lines + [""]:
        if l.strip():
            block.append(l)
        elif block:
            out.append(block)
            block = []
    return out


def join(lines):
    return re.sub(r"\s+", " ", " ".join(l.strip() for l in lines)).strip()


def is_subheading(first, rest):
    s = first.strip()
    return bool(rest) and len(s) < 60 and not re.search(r"[.:;,]$", s) and not ITEM.match(first)


def text_blocks(lines):
    blocks = []
    for para in paragraphs(lines):
        if is_subheading(para[0], para[1:]):
            blocks.append({"type": "h", "text": para[0].strip()})
            para = para[1:]
        prose, items, ordered = [], [], None
        for l in para:
            m = ITEM.match(l)
            if m:
                ordered = m.group(1) is not None
                items.append({"n": int(m.group(1)), "text": m.group(2).strip()} if ordered
                             else {"text": m.group(2).strip()})
            elif items:
                items[-1]["text"] = join([items[-1]["text"], l])
            else:
                prose.append(l)
        if prose and blocks and blocks[-1]["type"] == "list" and prose[0].strip()[:1].islower():
            # a list item the page break split, as in 10.8
            last = blocks[-1]["items"][-1]
            last["text"] = join([last["text"]] + prose)
            prose = []
        if prose:
            blocks.append({"type": "p", "text": join(prose)})
        if items and not prose and blocks and blocks[-1]["type"] == "list" and blocks[-1]["ordered"] == ordered:
            blocks[-1]["items"] += items
        elif items:
            blocks.append({"type": "list", "ordered": ordered, "items": items})
    return blocks


def table_blocks(lines):
    """The scoring tables of 8.1 to 8.3, with any prose before them."""
    blocks, prose, table, group = [], [], None, None
    for l in lines:
        if not l.strip():
            continue
        h = TABLE_HEAD.match(l)
        r = TABLE_ROW.match(l)
        if h:
            table = {"type": "table", "title": h.group(1).strip(), "columns": COLUMNS, "groups": []}
            blocks.append(table)
            group = None
        elif r and table is not None:
            if group is None:
                group = {"label": None, "rows": []}
                table["groups"].append(group)
            vals = [None if v == "x" else float(v) if "." in v else int(v) for v in r.group(2).split()]
            group["rows"].append({"label": re.sub(r"(?<=\d)\s*[–-]\s*(?=\d)", " - ", r.group(1).strip()), "values": vals})
        elif table is not None:
            group = {"label": l.strip(), "rows": []}
            table["groups"].append(group)
        else:
            prose.append(l)
    if prose:
        blocks.insert(0, {"type": "p", "text": join(prose)})
    return blocks


def words(blocks):
    out = []
    for b in blocks:
        if b["type"] in ("p", "h"):
            out += b["text"].split()
        elif b["type"] == "list":
            for it in b["items"]:
                out += it["text"].split()
        else:
            out += b["title"].split() + b["columns"]
            for g in b["groups"]:
                out += (g["label"] or "").split()
                for r in g["rows"]:
                    out += r["label"].split() + ["x" if v is None else str(v) for v in r["values"]]
    return out


def build():
    titles = editions.toc(editions.text_of("rules_PDL_Rules_doc.txt"))
    raw = split_sections(body_lines(), titles)
    sections = []
    for num, title in titles.items():
        lines = raw.get(num, [])
        blocks = table_blocks(lines) if num.startswith("8.") and num != "8.0" else text_blocks(lines)
        sections.append({"id": num, "chapter": num.split(".")[0], "title": title,
                         "level": 1 if num.endswith(".0") else 2, "blocks": blocks})
    return {
        "edition": "2006",
        "source": f"mfl_archive/legacy/{SOURCE}",
        "source_note": "Text of PDL_Rules.pdf (created 2006-09-24, modified 2006-10-17), "
                       "word for word the same as PDL_Rules.doc. See docs/rulebook/editions.md.",
        "sections": sections,
    }


def check(book):
    """Every word of the PDF's sections, and nothing else, is in the blocks."""
    titles = editions.toc(editions.text_of("rules_PDL_Rules_doc.txt"))
    pdf = editions.sections(editions.text_of(SOURCE), titles)
    def norm(ws):
        ws = (re.sub(r"[^\w$%+-]", "", w.replace("–", "-")).lower() for w in ws)
        return Counter(w for w in ws if w)
    problems = []
    for s in book["sections"]:
        want = norm(pdf[s["id"]][1].split()) if s["id"] in pdf else Counter()
        got = norm(editions.clean(" ".join(words(s["blocks"]))).split())  # the same cleaning on both sides
        if want != got:
            problems.append((s["id"], dict((want - got).most_common(5)), dict((got - want).most_common(5))))
    for s in book["sections"]:
        for b in s["blocks"]:
            if b["type"] == "table":
                for g in b["groups"]:
                    for r in g["rows"]:
                        if len(r["values"]) != len(COLUMNS):
                            problems.append((s["id"], "row", r["label"]))
    return problems


def main():
    book = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(book, f, indent=1, ensure_ascii=False)
        f.write("\n")
    n_words = sum(len(words(s["blocks"])) for s in book["sections"])
    kinds = Counter(b["type"] for s in book["sections"] for b in s["blocks"])
    print(f"wrote rules/baseline.json: {len(book['sections'])} sections, {n_words:,} words, blocks {dict(kinds)}")
    problems = check(book)
    for p in problems:
        print("  MISMATCH", p)
    print("check: every section's words match the PDF" if not problems else f"check: {len(problems)} mismatches")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
