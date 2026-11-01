// Hover peeks: something small appears beside the cursor while it rests on a team's name, on links to
// the team's page and on the plain-text mentions, which get a span to hover on, and on a few players'
// names. The words and figures are eggs.peeks(), written in below at build (site/eggs.json "peeks"):
// each team's peeks are picked by weight, and its logo, where it has one, now and then instead.
// Mouse only, touch has no hover.
(function () {
  var data = null;
  if (!data || !matchMedia("(hover: hover)").matches) return;
  var asset = function (file) {
    return document.querySelector("link[rel=stylesheet]").href.replace(/site\.css.*$/, file);
  };
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  // a card's title, lines and foot, in that order, each only if given
  function words(box, p) {
    if (p.title) box.appendChild(el("b", null, p.title));
    (p.lines || []).forEach(function (line) { box.appendChild(el("span", null, line)); });
    if (p.text) box.appendChild(el("span", null, p.text));
    if (p.foot) box.appendChild(el("small", null, p.foot));
    return box;
  }
  var svg = function (s) { var d = el("div"); d.innerHTML = s; return d.firstChild; };
  var draw = {
    img: function (p) { var i = new Image(); i.src = asset(p.src); i.alt = ""; i.className = "peek peek-img"; return i; },
    note: function (p) { return words(el("div", "peek peek-note peek-" + (p.style || "plain")), p); },
    // the tank's flag on its pole, 130 by 40
    flag: function (p) {
      var box = el("div", "peek peek-flag");
      box.appendChild(svg("<svg viewBox='0 0 130 40' aria-hidden='true'>" +
        "<line x1='2' y1='2' x2='2' y2='40' stroke='#222' stroke-width='2.5'/>" +
        "<path d='M3 2 H128 L120 16 L128 30 H3 Z' fill='#ffd400' stroke='#b89a00' stroke-width='.8'/>" +
        "<text x='62' y='20' text-anchor='middle' font-size='11' font-weight='700' font-family='Arial, sans-serif' fill='#111'></text></svg>"));
      box.querySelector("text").textContent = p.text;
      if (p.foot) box.appendChild(el("small", null, p.foot));
      return box;
    },
    pennant: function (p) {
      var box = el("div", "peek peek-flag");
      box.appendChild(svg("<svg viewBox='0 0 130 40' aria-hidden='true'>" +
        "<line x1='2' y1='2' x2='2' y2='40' stroke='#222' stroke-width='2.5'/>" +
        "<path d='M3 3 L128 18 L3 33 Z' fill='#008e97' stroke='#fc4c02' stroke-width='2'/>" +
        "<text x='46' y='22' text-anchor='middle' font-size='11' font-weight='700' font-family='Arial, sans-serif' fill='#fff'></text></svg>"));
      box.querySelector("text").textContent = p.text;
      return box;
    },
    missing: function (p) {
      var box = el("div", "peek peek-missing");
      box.appendChild(el("b", null, p.title));
      box.appendChild(el("i", null, "🏆"));
      box.appendChild(el("span", null, p.text));
      return box;
    },
    sms: function (p) {
      var box = el("div", "peek peek-sms");
      box.appendChild(el("span", null, p.text));
      box.appendChild(el("small", null, p.foot));
      return box;
    },
    // a moose-crossing sign over a plate of the Moose's two numbers
    moose: function (p) {
      var box = el("div", "peek peek-moose");
      box.appendChild(svg("<svg viewBox='0 0 100 100' aria-hidden='true'>" +
        "<path d='M50 3 L97 50 L50 97 L3 50 Z' fill='#ffd400' stroke='#111' stroke-width='3' stroke-linejoin='round'/>" +
        "<g fill='#111'><path d='M38 47 C44 41 62 40 70 45 C74 48 74 56 71 60 L70 74 H67 L66 61 C60 63 50 63 45 61 " +
        "L44 74 H41 L40 60 C38 57 37 53 38 47 Z'/>" +
        "<path d='M40 50 L31 48 C28 48 26 51 25 54 L23 59 C23 61 25 62 27 61 L31 58 L36 59 L42 55 Z'/>" +
        "<path d='M34 47 C31 41 26 39 22 39 L24 37 L22 34 L26 36 L26 31 L29 35 L31 31 L32 36 L35 33 L35 38 " +
        "C37 40 37 44 36 47 Z'/>" +
        "<path d='M27 58 C27 62 28 64 30 64 C31 62 31 60 30 58 Z'/></g></svg>"));
      box.appendChild(words(el("div", "peek-plate"), p));
      return box;
    },
    tv: function (p) {
      var box = el("div", "peek peek-tv");
      var screen = el("div", "peek-screen");
      screen.appendChild(el("span", null, p.text));
      box.appendChild(screen);
      return box;
    },
    // the Commandos' giant-killer cup, as on their page
    trophy: function (p) {
      var box = el("div", "peek peek-trophy");
      box.appendChild(svg("<svg viewBox='0 0 48 60' aria-hidden='true'><path d='M12 6 H36 V20 C36 30 30 35 24 35 C18 35 12 30 12 20 Z' fill='#d4a017'/>" +
        "<path d='M12 10 H5 C5 20 9 24 13 25 M36 10 H43 C43 20 39 24 35 25' fill='none' stroke='#d4a017' stroke-width='3'/>" +
        "<rect x='21' y='35' width='6' height='10' fill='#b8860b'/><rect x='13' y='45' width='22' height='8' rx='1' fill='#5a3a1a'/></svg>"));
      box.appendChild(words(el("div"), p));
      return box;
    },
    // a split-flap departure board's one row
    board: function (p) {
      var box = el("div", "peek peek-board");
      box.appendChild(el("span", null, p.line));
      box.appendChild(el("b", p.status === "ARRIVED" ? "peek-ok" : "peek-late", p.status));
      return box;
    }
  };

  // every name to watch: teams first, then players, each with its peeks and the logo's share
  var who = data.teams.map(function (t) {
    var peeks = t.peeks.slice();
    if (t.logo) {
      var rest = peeks.reduce(function (s, p) { return s + p.w; }, 0);
      peeks.push({ kind: "img", src: t.logo, w: rest ? rest * data.logo_share / (1 - data.logo_share) : 1 });
    }
    return { names: [t.name], key: t.slug, href: "franchises/" + t.slug, peeks: peeks };
  }).concat(data.players.map(function (x, i) {
    return { names: x.names, key: "player-" + i, peeks: x.peeks };
  })).filter(function (w) { return w.peeks.length; });
  var sel = function (w) { return (w.href ? "a[href*='" + w.href + ".html'], " : "") + ".peek-name-" + w.key; };
  var all = who.map(sel).join(", ");

  function wrap() {
    who.forEach(function (w) {
      w.names.forEach(function (name) {
        var walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
          acceptNode: function (n) {
            return n.nodeValue.indexOf(name) < 0 ||
              n.parentNode.closest("script, style, textarea, select, option, svg, .peek, " + all)
              ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
          }
        });
        var hits = [];
        while (walk.nextNode()) hits.push(walk.currentNode);
        hits.forEach(function (n) {
          var frag = document.createDocumentFragment();
          n.nodeValue.split(name).forEach(function (part, i) {
            if (i) frag.appendChild(el("span", "peek-name-" + w.key, name));
            if (part) frag.appendChild(document.createTextNode(part));
          });
          n.parentNode.replaceChild(frag, n);
        });
      });
    });
  }
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", wrap); else wrap();

  function pick(w) {
    var total = w.peeks.reduce(function (s, p) { return s + p.w; }, 0), r = Math.random() * total;
    for (var i = 0; i < w.peeks.length; i++) if ((r -= w.peeks[i].w) < 0) return i;
    return w.peeks.length - 1;
  }
  var made = {};
  function place(e, m) {
    // below right of the cursor, flipped to the other side near an edge
    var w = e.offsetWidth, h = e.offsetHeight;
    var x = m.clientX + 18, y = m.clientY + 18;
    if (x + w > innerWidth - 8) x = m.clientX - w - 18;
    if (y + h > innerHeight - 8) y = m.clientY - h - 18;
    e.style.left = Math.max(8, x) + "px";
    e.style.top = Math.max(8, y) + "px";
  }
  addEventListener("mouseover", function (ev) {
    if (!ev.target.closest) return;
    var w = who.filter(function (x) { return ev.target.closest(sel(x)); })[0];
    if (!w) return;
    var target = ev.target.closest(sel(w));
    if (ev.relatedTarget && target.contains(ev.relatedTarget)) return;
    var i = pick(w), id = w.key + "-" + i;
    var e = made[id] || (made[id] = document.body.appendChild(draw[w.peeks[i].kind](w.peeks[i])));
    place(e, ev);
    e.classList.add("up");
    var move = function (m) { place(e, m); };
    var out = function (o) {
      if (o.relatedTarget && target.contains(o.relatedTarget)) return;
      e.classList.remove("up");
      target.removeEventListener("mousemove", move);
      target.removeEventListener("mouseout", out);
    };
    target.addEventListener("mousemove", move);
    target.addEventListener("mouseout", out);
  });
})();
