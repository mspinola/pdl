// The F-Jackie egg. See site/eggs.json: type "barney" anywhere on the site.
(function () {
  function barney() {
    if (document.querySelector(".barney-pop")) return;
    document.documentElement.classList.add("barney-mode");
    var img = new Image();
    img.src = document.querySelector("link[rel=stylesheet]").href.replace(/site\.css.*$/, "barney.jpg");
    img.alt = "";
    img.className = "barney-pop";
    document.body.appendChild(img);
    requestAnimationFrame(function () { requestAnimationFrame(function () { img.classList.add("up"); }); });
    // rename the innermost element, as Moose mode does, so markup inside a link survives
    var names = Array.prototype.map.call(document.querySelectorAll(".data a[href*='franchises/f-jackie']"),
      function (a) { return a.querySelector("span") || a; });
    var was = names.map(function (n) { return n.textContent; });
    names.forEach(function (n) { n.textContent = "Barney"; });
    setTimeout(function () {
      img.classList.remove("up");
      names.forEach(function (n, i) { n.textContent = was[i]; });
      document.documentElement.classList.remove("barney-mode");
      setTimeout(function () { img.remove(); }, 700);
    }, 4500);
  }
  // the trades page's team filter calls him too
  window.pdlBarney = barney;

  // and he peeks out beside the cursor whenever it rests on F-Jackie's name: links to the team's page,
  // and the plain-text mentions, which get a span to hover on. Mouse only, touch has no hover.
  if (matchMedia("(hover: hover)").matches) {
    var name = "F-Jackie", sel = "a[href*='franchises/f-jackie'], .barney-name";
    var wrap = function () {
      var walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
          return n.nodeValue.indexOf(name) < 0 || n.parentNode.closest("script, style, textarea, " + sel)
            ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        }
      });
      var hits = [];
      while (walk.nextNode()) hits.push(walk.currentNode);
      hits.forEach(function (n) {
        var parts = n.nodeValue.split(name), frag = document.createDocumentFragment();
        parts.forEach(function (part, i) {
          if (i) {
            var span = document.createElement("span");
            span.className = "barney-name";
            span.textContent = name;
            frag.appendChild(span);
          }
          if (part) frag.appendChild(document.createTextNode(part));
        });
        n.parentNode.replaceChild(frag, n);
      });
    };
    if (document.readyState === "loading") addEventListener("DOMContentLoaded", wrap); else wrap();
    var peek = null;
    var place = function (e) {
      // below right of the cursor, flipped to the other side near an edge
      var w = peek.offsetWidth || 120, h = peek.offsetHeight || 120;
      var x = e.clientX + 18, y = e.clientY + 18;
      if (x + w > innerWidth - 8) x = e.clientX - w - 18;
      if (y + h > innerHeight - 8) y = e.clientY - h - 18;
      peek.style.left = x + "px";
      peek.style.top = y + "px";
    };
    addEventListener("mouseover", function (e) {
      var t = e.target.closest && e.target.closest(sel);
      if (!t || (e.relatedTarget && t.contains(e.relatedTarget))) return;
      if (!peek) {
        peek = new Image();
        peek.src = document.querySelector("link[rel=stylesheet]").href.replace(/site\.css.*$/, "barney.jpg");
        peek.alt = "";
        peek.className = "barney-peek";
        document.body.appendChild(peek);
      }
      place(e);
      peek.classList.add("up");
      var move = function (m) { place(m); };
      var out = function (o) {
        if (o.relatedTarget && t.contains(o.relatedTarget)) return;
        peek.classList.remove("up");
        t.removeEventListener("mousemove", move);
        t.removeEventListener("mouseout", out);
      };
      t.addEventListener("mousemove", move);
      t.addEventListener("mouseout", out);
    });
  }

  var word = "barney";
  var typed = "";
  addEventListener("keydown", function (e) {
    var t = e.target;
    if (t && (t.isContentEditable || /^(input|textarea|select)$/i.test(t.tagName))) return;
    if (e.key.length !== 1) return;
    typed = (typed + e.key.toLowerCase()).slice(-word.length);
    if (typed !== word) return;
    typed = "";
    barney();
  });
})();
