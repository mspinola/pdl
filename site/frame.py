"""The page frame every site page shares, and small formatting helpers."""
import html, re

E = html.escape


def slug(name):
    """A team name as a file name: "Carter's Commandos" -> "carters-commandos"."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")


def num(v, places=1):
    """A score as the league records it: whole numbers before 2018, tenths after."""
    if v is None:
        return ""
    v = float(v)
    return f"{v:.0f}" if v == int(v) else f"{v:.{places}f}"


def record(w, l, t=0):
    w, l, t = (int(x) if float(x) == int(float(x)) else float(x) for x in (w, l, t))
    return f"{w}-{l}" + (f"-{t}" if t else "")



def page(title, body, depth=1, description=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<link rel="stylesheet" href="{up}assets/site.css">
<script>addEventListener("beforeprint", () => document.querySelectorAll("details").forEach(d => d.open = true));</script>
<script src="{up}assets/moose.js" defer></script>
<script src="{up}assets/barney.js" defer></script>
</head>
<body>
<header class="masthead">
  <a class="brand" href="{up}index.html">Premier Dynasty League</a>
  <nav><a href="{up}seasons/index.html">Seasons</a><a href="{up}franchises/index.html">Franchises</a><a href="{up}h2h/index.html">Head to head</a><a href="{up}trades/index.html">Trades</a><a href="{up}drafts/index.html">Drafts</a><a href="{up}records/index.html">Records</a><a href="{up}analysis/index.html">Analysis</a><a href="{up}rules/index.html">Rule book</a></nav>
</header>
<main>
{body}
</main>
<footer class="foot">Built from the league's own records: the 2006 rule book, the rule-change page,
the meeting emails, the league polls and the MyFantasyLeague archive.
<a href="https://github.com/mspinola/pdl">Sources and code</a>.</footer>
</body>
</html>
"""


