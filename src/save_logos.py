"""Save a copy of every franchise logo and icon MFL has on file, 2003 on.

MFL keeps only addresses, and the images behind them live on MFL's own servers,
which come and go: in 2026 every image uploaded in 2015 (on www55) and one of
MFL's stock helmets stopped loading. This fetches each address any season's
league.json names and keeps what still loads in private/logos/, beside a
manifest of which teams used it and when. The images go to the private repo
because a custom logo can carry anything, an owner's name included.

    python3 src/save_logos.py           # fetch what is not saved yet
    python3 src/save_logos.py --retry   # also retry the addresses that failed before
    python3 src/save_logos.py --from ../mspinola/images/logos
                                        # fill gaps from a folder of copies, matched by file name

A saved file is never fetched again, so a later run cannot overwrite a good copy
with whatever MFL serves in its place.
"""
import argparse, hashlib, json, os, sys, time, urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{BASE}/src")
import identities as I
from fetch_mfl import LEAGUES, UA

OUT = f"{BASE}/private/logos"
MANIFEST = f"{OUT}/manifest.json"


def addresses():
    """address -> {"teams": {team: [seasons]}, "kinds": [icon/logo]}, from every archived season."""
    slots = I.slot_index()
    out = defaultdict(lambda: {"teams": defaultdict(set), "kinds": set()})
    for y in sorted(LEAGUES):
        p = f"{BASE}/mfl_archive/{y}/league.json"
        if not os.path.exists(p):
            continue
        for f in json.load(open(p))["league"]["franchises"]["franchise"]:
            team = slots.get((y, f["id"]))
            for kind in ("icon", "logo"):
                u = (f.get(kind) or "").strip()
                if u.startswith("http"):
                    out[u]["teams"][I.label_for(team, y) if team else f"franchise {f['id']}"].add(y)
                    out[u]["kinds"].add(kind)
    return out


def local_path(url):
    host, path = url.split("://", 1)[1].split("/", 1)
    return f"{OUT}/{host.split('.')[0]}/{path}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retry", action="store_true", help="retry addresses that failed on an earlier run")
    ap.add_argument("--from", dest="copies", help="a folder of old copies (the legacy site's images/logos) "
                    "to fill addresses MFL no longer serves, matched by file name")
    args = ap.parse_args()
    copies = {n: f"{args.copies}/{n}" for n in os.listdir(args.copies)} if args.copies else {}
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    dead_hosts = set()   # a host that times out once is not asked again this run
    counts = defaultdict(int)
    for url, info in sorted(addresses().items()):
        entry = manifest.get(url, {})
        entry.update({"teams": {t: sorted(ys) for t, ys in sorted(info["teams"].items())},
                      "kinds": sorted(info["kinds"])})
        manifest[url] = entry
        dest = local_path(url)
        if os.path.exists(dest):
            if "sha256" not in entry:   # the same file under http and https, or saved before this field
                body = open(dest, "rb").read()
                entry.pop("error", None)
                entry.update({"file": os.path.relpath(dest, OUT), "bytes": len(body),
                              "sha256": hashlib.sha256(body).hexdigest()})
            counts["already saved"] += 1
            continue
        name = url.rsplit("/", 1)[1]
        if entry.get("error") and name in copies:
            body = open(copies[name], "rb").read()
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(body)
            entry.update({"file": os.path.relpath(dest, OUT), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                          "saved": time.strftime("%Y-%m-%d"), "source": "copy, not MFL: " + os.path.basename(os.path.normpath(args.copies))})
            counts["filled from copies"] += 1
            continue
        if entry.get("error") and not args.retry:
            counts["failed before"] += 1
            continue
        host = url.split("/")[2]
        if host in dead_hosts:
            entry.update({"error": "host not answering", "tried": time.strftime("%Y-%m-%d")})
            counts["failed"] += 1
            continue
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20)
            body, ctype = r.read(), r.headers.get("Content-Type", "")
            if not ctype.startswith("image/"):
                raise ValueError(f"not an image: {ctype}")
        except Exception as e:
            if "timed out" in str(e):
                dead_hosts.add(host)
            entry.update({"error": str(e)[:200], "tried": time.strftime("%Y-%m-%d")})
            counts["failed"] += 1
            time.sleep(1)
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(body)
        entry.pop("error", None)
        entry.update({"file": os.path.relpath(dest, OUT), "bytes": len(body), "type": ctype,
                      "sha256": hashlib.sha256(body).hexdigest(), "saved": time.strftime("%Y-%m-%d")})
        counts["saved"] += 1
        time.sleep(1)
    os.makedirs(OUT, exist_ok=True)
    with open(MANIFEST, "w") as f:
        json.dump(dict(sorted(manifest.items())), f, indent=1)
    print(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    missing = {}   # http and https name the same file, so list each once
    for url, e in sorted(manifest.items()):
        if e.get("error") and not os.path.exists(local_path(url)):
            missing[url.split("://")[1]] = e
    for addr, e in missing.items():
        print(f"  missing  {', '.join(e['teams'])}  {addr}  ({e['error'][:40]})")


if __name__ == "__main__":
    main()
