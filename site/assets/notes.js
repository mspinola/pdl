// The Beers egg. See site/eggs.json "beers": loaded only on their franchise page.
// Dozens of messy legal-pad pages flutter down and land in a heap, one per trading partner
// (from eggs.beers_notes()) and a few more, and last of all the switchboard: Beers in the middle
// of every franchise, a line to each as thick as their trades. A click, Escape, or 20 seconds
// sweeps the pile away.
(function () {
  function esc(t) { return String(t).replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; }); }
  // "~words~" is crossed out
  function line(t) { return esc(t).replace(/~([^~]+)~/g, "<s>$1</s>"); }
  function rand(a, b) { return a + Math.random() * (b - a); }

  function board(c) {
    // labels in two columns, alternating sides down the ranking, so none can collide
    var w = 460, h = 300, cx = 230, cy = 158;
    var max = Math.max.apply(null, c.partners.map(function (p) { return p.n; }));
    var right = c.partners.filter(function (p, i) { return i % 2 === 0; });
    var left = c.partners.filter(function (p, i) { return i % 2 === 1; });
    var out = "<svg viewBox='0 0 " + w + " " + h + "' aria-hidden='true'>" +
      "<text x='" + cx + "' y='20' text-anchor='middle' class='nb-title'>WHO'S WHO</text>";
    var k = 0;
    [[right, 1], [left, -1]].forEach(function (side) {
      side[0].forEach(function (p, i) {
        var m = side[0].length;
        var a = (m === 1 ? 0 : -64 + 128 * i / (m - 1)) * Math.PI / 180;
        var ex = cx + side[1] * 88 * Math.cos(a), ey = cy + 112 * Math.sin(a);
        out += "<line pathLength='1' x1='" + cx + "' y1='" + cy + "' x2='" + ex.toFixed(1) + "' y2='" + ey.toFixed(1) +
          "' stroke-width='" + (1 + 6 * p.n / max).toFixed(1) + "' style='animation-delay:" + (0.3 + (k++) * 0.12).toFixed(2) + "s'/>" +
          "<text x='" + (ex + side[1] * 6).toFixed(1) + "' y='" + (ey + 4).toFixed(1) + "' text-anchor='" +
          (side[1] > 0 ? "start" : "end") + "'>" + esc(p.team) + " (" + p.n + ")</text>";
      });
    });
    return out + "<circle cx='" + cx + "' cy='" + cy + "' r='26'/>" +
      "<text x='" + cx + "' y='" + (cy + 5) + "' text-anchor='middle' class='nb-me'>" + esc(c.team) + "</text>" +
      "<text x='" + cx + "' y='292' text-anchor='middle' class='nb-total'>" + esc(c.total) + "</text>" +
      "<ellipse cx='" + cx + "' cy='287' rx='118' ry='13'/><ellipse cx='" + (cx + 1) + "' cy='286' rx='122' ry='15' transform='rotate(-2 " +
      (cx + 1) + " 286)'/></svg>";
  }

  function pile(c) {
    if (document.querySelector(".notes")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "notes" + (calm ? " notes-calm" : "");
    el.title = "Click to sweep the notes away";
    var pages = c.pages.slice().sort(function () { return Math.random() - 0.5; });
    var vw = innerWidth, vh = innerHeight, pw = Math.min(170, vw * 0.42), html = "";
    pages.forEach(function (p, i) {
      var x = rand(-10, vw - pw + 10), y = rand(40, Math.max(60, vh - 210));
      html += "<div class='note" + (Math.random() < 0.3 ? " ring" : "") + "' style='left:" + x.toFixed(0) + "px;top:" +
        y.toFixed(0) + "px;width:" + pw.toFixed(0) + "px;--r:" + rand(-18, 18).toFixed(1) + "deg;--d:" + (i * 0.08).toFixed(2) +
        "s;--s:" + rand(0, 0.25).toFixed(2) + "s'>" + p.map(function (t, j) { return (j ? "<p>" : "<b>") + line(t) + (j ? "</p>" : "</b>"); }).join("") +
        "</div>";
    });
    // the switchboard lands last, on top, in the middle
    html += "<div class='note note-board' style='--r:-2deg;--d:" + (pages.length * 0.08 + 0.2).toFixed(2) + "s;--s:0s'>" + board(c) + "</div>";
    el.innerHTML = html;
    document.body.appendChild(el);
    var gone = false;
    function sweep() {
      if (gone) return;
      gone = true;
      removeEventListener("keydown", key);
      el.classList.add("sweep");
      setTimeout(function () { el.remove(); }, calm ? 0 : 1100);
    }
    function key(e) { if (e.key === "Escape") sweep(); }
    el.addEventListener("click", sweep);
    addEventListener("keydown", key);
    setTimeout(sweep, c.seconds * 1000);
  }
  window.pdlNotes = pile;
})();
