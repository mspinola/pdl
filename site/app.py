"""The installable app: the PDL mark as icons, the manifest, and a service worker.

With these served, Chrome on Android offers to install the site (its own window, a launcher
icon, an entry in the app switcher), and Safari on an iPhone adds it to the home screen from
the Share menu. No store and no second codebase: the site's own deploy is the release. The
same route as cot-analyzer's src/pwa.py.

The worker caches nothing. The site is rebuilt every week, and a cached page would keep showing
last week's standings with total confidence. It answers navigations with an offline page when
the network is gone, which installability wants a fetch handler for, and passes everything else
straight through.

The icons are drawn here as SVG, like the MFL banner, and rasterized when rsvg-convert is
installed (the publish workflow installs it). The letters are paths rather than text, so they
do not depend on the fonts of the machine that builds them. Everything sits at the site root,
because a worker's scope cannot be wider than its own folder.
"""
import json, os, shutil, subprocess

# the site's dark ground and ink, and its orange (site.css)
BG, INK, ORANGE = "#0b0b0b", "#ffffff", "#eb6834"
LIGHT_BG = "#f9f9f7"

# P, D and L in strokes 30 wide on a 512 grid, letters between y 176 and 306, an orange rule under
MARK = ("<g fill='none' stroke='{ink}' stroke-width='30' stroke-linejoin='miter'>"
        "<path d='M114 306 V191 H149 A30 30 0 0 1 149 251 H114'/>"
        "<path d='M226 191 H251 A50 50 0 0 1 251 291 H226 Z'/>"
        "<path d='M353 176 V291 H418'/></g>"
        "<rect x='99' y='328' width='319' height='16' fill='{orange}'/>")

# (file, size, corner radius as a share of the side, or None for a square that fills the frame)
ICONS = [("icon-192.png", 192, .18), ("icon-512.png", 512, .18),
         ("icon-maskable-512.png", 512, None),   # full bleed, the mark inside the safe circle
         ("apple-touch-icon.png", 180, None)]    # opaque, iOS rounds it itself

MANIFEST = {
    "name": "Premier Dynasty League",
    "short_name": "PDL",
    "description": "The Premier Dynasty League's record book, rules and history, since 2000.",
    "id": "./",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": BG,
    "theme_color": BG,
    "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
              {"src": "assets/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
              {"src": "assets/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
}

OFFLINE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offline, PDL</title>
<style>
  body {{ margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center;
         background: {BG}; color: #a5a49a; font: 17px/1.5 "Iowan Old Style", Palatino, Georgia, serif; }}
  h1 {{ color: {INK}; font-size: 1.4rem; font-weight: 600; margin: 0 0 .4rem; }}
  p {{ margin: 0; }}
</style></head>
<body><div><h1>You are offline</h1><p>The record book needs a connection. Try again when you have one.</p></div></body></html>"""

WORKER = """// The PDL app's service worker: caches nothing (see site/app.py). Navigations get an offline
// page when the network is gone, and everything else goes straight to the network.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
const OFFLINE = __OFFLINE__;
self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(fetch(event.request).catch(() =>
    new Response(OFFLINE, {status: 503, headers: {"Content-Type": "text/html; charset=utf-8"}})));
});
""".replace("__OFFLINE__", json.dumps(OFFLINE))


def icon_svg(size=512, corner=None):
    ground = (f"<rect width='512' height='512' rx='{512 * corner:.0f}' fill='{BG}'/>" if corner
              else f"<rect width='512' height='512' fill='{BG}'/>")
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 512 512'>"
            f"{ground}{MARK.format(ink=INK, orange=ORANGE)}</svg>")


def head(up):
    """The tags every page's head carries: the manifest, the icons, the bar colour and the worker."""
    return (f'<link rel="manifest" href="{up}manifest.webmanifest">\n'
            f'<link rel="icon" href="{up}assets/icon.svg" type="image/svg+xml">\n'
            f'<link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">\n'
            f'<meta name="apple-mobile-web-app-title" content="PDL">\n'
            f'<meta name="theme-color" content="{LIGHT_BG}" media="(prefers-color-scheme: light)">\n'
            f'<meta name="theme-color" content="{BG}" media="(prefers-color-scheme: dark)">\n'
            f'<script>if ("serviceWorker" in navigator) addEventListener("load", () => '
            f'navigator.serviceWorker.register("{up}sw.js"));</script>\n')


def build(dist):
    os.makedirs(f"{dist}/assets", exist_ok=True)
    with open(f"{dist}/manifest.webmanifest", "w") as f:
        json.dump(MANIFEST, f, indent=1)
    with open(f"{dist}/sw.js", "w") as f:
        f.write(WORKER)
    with open(f"{dist}/assets/icon.svg", "w") as f:
        f.write(icon_svg(corner=.18))
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print("  no rsvg-convert, so the app icons are icon.svg only")
        return 1
    for name, size, corner in ICONS:
        src = f"{dist}/assets/{name}.svg"
        with open(src, "w") as f:
            f.write(icon_svg(size, corner))
        subprocess.run([rsvg, "-w", str(size), "-h", str(size), "-o", f"{dist}/assets/{name}", src], check=True)
        os.remove(src)
    return 1
