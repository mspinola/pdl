// The Otters' otter. See site/eggs.json "otter": loaded only on their franchise page.
// An otter floats on its back across the bottom of the screen, a waiver claim on its belly,
// under a bubble whose count of the team's waiver adds runs up from zero (eggs.otter() gives
// the count and the lines). Reduced motion gets it parked at the left with the count in full.
(function () {
  window.pdlOtter = function (o) {
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "otter" + (calm ? " otter-calm" : "");
    el.title = "Click to close";
    var bubble = document.createElement("div");
    bubble.className = "otter-bubble";
    var head = document.createElement("p");
    head.className = "otter-count";
    var n = document.createElement("b");
    n.textContent = calm ? o.count : "0";
    head.appendChild(document.createTextNode(o.label + ": "));
    head.appendChild(n);
    bubble.appendChild(head);
    o.lines.forEach(function (line) {
      var p = document.createElement("p");
      p.textContent = line;
      bubble.appendChild(p);
    });
    el.appendChild(bubble);
    // on its back in the water: head left, tail right, paws up holding the claim
    el.insertAdjacentHTML("beforeend",
      "<svg class='otter-art' viewBox='0 0 220 90' aria-hidden='true'>" +
      "<path d='M0 70 Q15 62 30 70 T60 70 T90 70 T120 70 T150 70 T180 70 T210 70 V90 H0 Z' fill='#4fa3d9' opacity='.85'/>" +
      "<path d='M160 58 C185 56 205 50 214 40 C206 58 186 66 162 66 Z' fill='#6b4428'/>" +
      "<ellipse cx='105' cy='58' rx='62' ry='17' fill='#7a4e2e'/>" +
      "<ellipse cx='105' cy='52' rx='44' ry='9' fill='#a8784f'/>" +
      "<circle cx='40' cy='48' r='19' fill='#7a4e2e'/><circle cx='36' cy='50' r='12' fill='#c9a17a'/>" +
      "<circle cx='29' cy='31' r='5' fill='#6b4428'/><circle cx='50' cy='32' r='5' fill='#6b4428'/>" +
      "<circle cx='33' cy='44' r='2.4' fill='#1d1d1d'/><circle cx='44' cy='44' r='2.4' fill='#1d1d1d'/>" +
      "<ellipse cx='38' cy='51' rx='3.4' ry='2.4' fill='#1d1d1d'/>" +
      "<path d='M30 55 Q38 60 46 55' fill='none' stroke='#1d1d1d' stroke-width='1.4'/>" +
      "<path d='M22 52 H12 M22 55 H11 M54 52 H64 M54 55 H65' stroke='#f4ead2' stroke-width='1'/>" +
      "<g class='otter-claim'><rect x='84' y='22' width='34' height='24' rx='2' fill='#ffffff' stroke='#9aa4ab'/>" +
      "<path d='M89 29 H113 M89 34 H110 M89 39 H106' stroke='#9aa4ab' stroke-width='1.5'/></g>" +
      "<ellipse cx='86' cy='44' rx='6' ry='5' fill='#6b4428'/><ellipse cx='116' cy='44' rx='6' ry='5' fill='#6b4428'/>" +
      "</svg>");
    document.body.appendChild(el);
    // the page and its styles can be a deploy apart for a few minutes: skip this visit rather than show it unstyled
    if (getComputedStyle(el).position !== "fixed") { el.remove(); return; }
    function done() { el.remove(); }
    el.addEventListener("click", done);
    el.addEventListener("animationend", function (e) { if (e.target === el) done(); });
    if (calm) { setTimeout(done, 12000); return; }
    // the count runs up over the first few seconds
    var t0 = null;
    function tick(t) {
      t0 = t0 || t;
      var f = Math.min(1, (t - t0) / 3500);
      n.textContent = Math.round(o.count * f);
      if (f < 1 && el.isConnected) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  };
})();
