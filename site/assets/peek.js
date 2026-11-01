// Hover peeks: something small appears beside the cursor while it rests on a team's name, on links to
// the team's page and on the plain-text mentions, which get a span to hover on. Barney for F-Jackie
// (the barney egg's logo), the tank's SUCK FOR LUCK flag for the Tally Wackers (the tank egg's season),
// or now and then the title they have never won, asking after itself.
// See site/eggs.json "barney" and "tank". Mouse only, touch has no hover.
(function () {
  if (!matchMedia("(hover: hover)").matches) return;
  var asset = function (file) {
    return document.querySelector("link[rel=stylesheet]").href.replace(/site\.css.*$/, file);
  };
  var teams = [
    { name: "F-Jackie", slug: "f-jackie", make: function () {
      var img = new Image();
      img.src = asset("barney.jpg");
      img.alt = "";
      img.className = "peek peek-barney";
      return img;
    } },
    { name: "Tally Wackers", slug: "tally-wackers", make: function () {
      // the tank's flag on its pole, 130 by 40
      var el = document.createElement("div");
      el.className = "peek peek-flag";
      el.innerHTML = "<svg viewBox='0 0 130 40' aria-hidden='true'>" +
        "<line x1='2' y1='2' x2='2' y2='40' stroke='#222' stroke-width='2.5'/>" +
        "<path d='M3 2 H128 L120 16 L128 30 H3 Z' fill='#ffd400' stroke='#b89a00' stroke-width='.8'/>" +
        "<text x='62' y='20' text-anchor='middle' font-size='11' font-weight='700' font-family='Arial, sans-serif' fill='#111'>" +
        "SUCK FOR LUCK</text></svg>" +
        "<div class='peek-missing'><b>Missing</b><span class='peek-trophy'>\uD83C\uDFC6</span>" +
        "Has anyone seen me in the last couple of decades? The Tally Wackers have been looking since 2000.</div>";
      return el;
    }, show: function (el) {
      // the flag mostly, the poster about one time in three
      el.classList.toggle("peek-alt", Math.random() < 1 / 3);
    } }
  ];
  var sel = function (t) { return "a[href*='franchises/" + t.slug + "'], .peek-name-" + t.slug; };
  var all = teams.map(sel).join(", ");

  function wrap() {
    teams.forEach(function (t) {
      var walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
          return n.nodeValue.indexOf(t.name) < 0 || n.parentNode.closest("script, style, textarea, " + all)
            ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        }
      });
      var hits = [];
      while (walk.nextNode()) hits.push(walk.currentNode);
      hits.forEach(function (n) {
        var frag = document.createDocumentFragment();
        n.nodeValue.split(t.name).forEach(function (part, i) {
          if (i) {
            var span = document.createElement("span");
            span.className = "peek-name-" + t.slug;
            span.textContent = t.name;
            frag.appendChild(span);
          }
          if (part) frag.appendChild(document.createTextNode(part));
        });
        n.parentNode.replaceChild(frag, n);
      });
    });
  }
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", wrap); else wrap();

  var made = {};
  function place(el, e) {
    // below right of the cursor, flipped to the other side near an edge
    var w = el.offsetWidth, h = el.offsetHeight;
    var x = e.clientX + 18, y = e.clientY + 18;
    if (x + w > innerWidth - 8) x = e.clientX - w - 18;
    if (y + h > innerHeight - 8) y = e.clientY - h - 18;
    el.style.left = x + "px";
    el.style.top = y + "px";
  }
  addEventListener("mouseover", function (e) {
    if (!e.target.closest) return;
    var team = teams.filter(function (t) { return e.target.closest(sel(t)); })[0];
    if (!team) return;
    var target = e.target.closest(sel(team));
    if (e.relatedTarget && target.contains(e.relatedTarget)) return;
    var el = made[team.slug] || (made[team.slug] = document.body.appendChild(team.make()));
    if (team.show) team.show(el);
    place(el, e);
    el.classList.add("up");
    var move = function (m) { place(el, m); };
    var out = function (o) {
      if (o.relatedTarget && target.contains(o.relatedTarget)) return;
      el.classList.remove("up");
      target.removeEventListener("mousemove", move);
      target.removeEventListener("mouseout", out);
    };
    target.addEventListener("mousemove", move);
    target.addEventListener("mouseout", out);
  });
})();
