"""The page frame every site page shares, and small formatting helpers."""
import hashlib, html, os, re, urllib.parse
from functools import lru_cache

import app

E = html.escape
SITE = os.path.dirname(os.path.abspath(__file__))

# GoatCounter, page counts without cookies or personal data: the site's code at goatcounter.com
# (the CODE in CODE.goatcounter.com), or "" to count nothing. Its dashboard is at that address.
GOATCOUNTER = "pdl"

# The suggestion box in every page's footer: mailto links to the commissioner's office, one per
# subject. The address is the send-as alias the notifier mails from ("from" in
# private/notify/config.json); build.py refuses to build if the two disagree. It is the one
# address src/check_no_owner_names.py allows on the site, by name, because the commissioner
# chose to publish it. The subject prefix is the contract with `notify.py suggestions`, which
# picks up every message to this address whose subject starts with it.
COMMISSIONER = "matt.spinola+pdl@gmail.com"
SUGGESTION_SUBJECT = "PDL suggestion"
SUGGESTION_TOPICS = (("Doreen", "Doreen"), ("Swami", "the Swami"), ("website", "the website"))


def suggestion_link(topic):
    """A mailto link to the commissioner's office with the subject prefilled, so a reply lands in
    the right bucket: mailto:...?subject=PDL%20suggestion%3A%20Doreen."""
    q = urllib.parse.urlencode({"subject": f"{SUGGESTION_SUBJECT}: {topic}"}, quote_via=urllib.parse.quote)
    return f"mailto:{E(COMMISSIONER)}?{q}"


def suggestion_box():
    """The footer's suggestion box: one link per topic, and the line that says who reads them."""
    links = ", ".join(f'<a href="{suggestion_link(t)}">{E(label)}</a>' for t, label in SUGGESTION_TOPICS)
    links = " or ".join(links.rsplit(", ", 1))
    return (f'<p class="suggest"><strong>Suggestion box.</strong> Something to say about {links}? '
            "Each link opens an email to the commissioner's office. The commissioner reads every one.</p>\n")


def counter():
    """The GoatCounter script for every page's head, or nothing when no code is set."""
    if not GOATCOUNTER:
        return ""
    return (f'<script data-goatcounter="https://{E(GOATCOUNTER)}.goatcounter.com/count" async '
            f'src="https://gc.zgo.at/count.js"></script>\n')


@lru_cache(maxsize=None)
def ver(path):
    """A fingerprint of a site/ source file, for its link: GitHub Pages lets a browser keep
    an asset ten minutes, so a page could otherwise run with the previous script or styles."""
    return hashlib.sha1(open(f"{SITE}/{path}", "rb").read()).hexdigest()[:8]


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



def page(title, body, depth=1, description="", light=False):
    """light: this page is always the light theme, whatever the visitor's setting."""
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"{' data-theme="light"' if light else ""}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<!-- the site has its own light and dark themes, so a browser's automatic dark mode (Chrome's,
     Dark Reader) must not repaint it: it turns the eggs' paper and cards dark and their ink light -->
<meta name="color-scheme" content="{"light" if light else "light dark"}">
<meta name="darkreader-lock">
{counter()}{app.head(up)}<link rel="stylesheet" href="{up}assets/site.css?v={ver("site.css")}">
<script>addEventListener("beforeprint", () => document.querySelectorAll("details").forEach(d => d.open = true));</script>
<script src="{up}assets/moose.js?v={ver("assets/moose.js")}" defer></script>
<script src="{up}assets/barney.js?v={ver("assets/barney.js")}" defer></script>
<script src="{up}assets/peek.js?v={ver("assets/peek.js")}" defer></script>
</head>
<body>
<header class="masthead">
  <a class="brand" href="{up}index.html">Premier Dynasty League</a>
  <nav><a href="{up}seasons/index.html">Seasons</a><a href="{up}franchises/index.html">Franchises</a><a href="{up}h2h/index.html">Head to head</a><a href="{up}trades/index.html">Trades</a><a href="{up}drafts/index.html">Drafts</a><a href="{up}records/index.html">Records</a><a href="{up}shame/index.html">Wall of shame</a><a href="{up}swami/index.html">Swami Says</a><a href="{up}analysis/index.html">Analysis</a><a href="{up}rules/index.html">Rule book</a></nav>
</header>
<main>
{body}
</main>
<footer class="foot">{suggestion_box()}Built from the league's own records: the 2006 rule book, the rule-change page,
the meeting emails, the league polls and the MyFantasyLeague archive.
<a href="https://github.com/mspinola/pdl">Sources and code</a>.</footer>
</body>
</html>
"""


