// The Tally Wackers' tank. See site/eggs.json "tank": loaded only on their franchise page.
// A tank flying the tank season's flag rolls in from the left, stops mid-screen under a report
// card on that season (from eggs.tank_card()), then charges a brick wall at the right edge,
// bounces off it and burns. Reduced motion gets it parked at the left with the card up.
(function () {
  // 240 by 150, facing right, the flag's words filled in
  function tank(flag) {
    return "<svg viewBox='0 0 240 150' aria-hidden='true'>" +
      "<line x1='100' y1='4' x2='100' y2='58' stroke='#222' stroke-width='2'/>" +
      "<path d='M101 4 H226 L218 18 L226 32 H101 Z' fill='#ffd400'/>" +
      "<text x='160' y='22' text-anchor='middle' font-size='9' font-weight='700' font-family='Arial, sans-serif' fill='#111'>" +
      flag + "</text>" +
      "<rect x='85' y='56' width='70' height='26' rx='8' fill='#6b7d45'/>" +
      "<rect x='108' y='50' width='22' height='8' rx='3' fill='#4a5730'/>" +
      "<rect x='150' y='63' width='80' height='8' rx='2' fill='#4a5730'/>" +
      "<path d='M30 106 L48 80 H192 L210 106 Z' fill='#5b6b3a'/>" +
      "<rect x='18' y='104' width='200' height='36' rx='18' fill='#2f3326'/>" +
      [38, 70, 102, 134, 166, 198].map(function (x) {
        return "<g class='tank-wheel' style='transform-origin: " + x + "px 122px'>" +
          "<circle cx='" + x + "' cy='122' r='11' fill='#5c6148'/>" +
          "<path d='M" + x + " 113 V131 M" + (x - 9) + " 122 H" + (x + 9) + "' stroke='#2f3326' stroke-width='2'/></g>";
      }).join("") +
      // the fire after the crash: three flames and their smoke, at the front of the tank
      "<g class='tank-fire'>" +
      "<g class='tank-smoke'><circle cx='170' cy='34' r='12'/><circle cx='190' cy='24' r='10'/><circle cx='150' cy='22' r='9'/></g>" +
      "<path d='M150 104 C140 80 160 70 156 46 C176 64 182 84 172 104 Z' fill='#ff7a1a'/>" +
      "<path d='M178 104 C168 74 192 62 186 30 C210 58 214 86 200 104 Z' fill='#ff4d1a'/>" +
      "<path d='M120 104 C114 86 128 78 126 60 C142 74 146 90 138 104 Z' fill='#ff9a1a'/>" +
      "<path d='M184 104 C178 86 192 78 190 60 C202 76 204 92 196 104 Z' fill='#ffd84a'/>" +
      "<path d='M154 104 C150 90 160 84 158 72 C168 82 170 94 164 104 Z' fill='#ffd84a'/>" +
      "</g>" +
      "</svg>";
  }

  function roll(c) {
    if (document.querySelector(".tank")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "tank" + (calm ? " tank-calm" : "");
    el.setAttribute("role", "status");
    var card = document.createElement("div");
    card.className = "tank-card";
    var h = document.createElement("b");
    h.textContent = c.title;
    var grade = document.createElement("span");
    grade.className = "tank-grade";
    grade.textContent = c.grade;
    var ul = document.createElement("ul");
    c.lines.forEach(function (t) { var li = document.createElement("li"); li.textContent = t; ul.appendChild(li); });
    card.appendChild(h);
    card.appendChild(ul);
    card.appendChild(grade);
    // a heckle stuck to the card, if there is one
    if (c.heckle) {
      var hk = document.createElement("p");
      hk.className = "tank-heckle";
      hk.textContent = c.heckle.text;
      var by = document.createElement("i");
      by.textContent = c.heckle.by;
      hk.appendChild(by);
      card.appendChild(hk);
    }
    el.appendChild(card);
    el.insertAdjacentHTML("beforeend", tank(c.flag));
    document.body.appendChild(el);
    // the page and its styles can be a deploy apart for a few minutes: skip this visit rather than show it unstyled
    if (getComputedStyle(el).position !== "fixed") { el.remove(); return; }
    // the wall it hits, at the right edge (none for reduced motion, which never drives off)
    var wall = null;
    if (!calm) {
      wall = document.createElement("div");
      wall.className = "tank-wall";
      document.body.appendChild(wall);
    }
    function done() { el.remove(); if (wall) wall.remove(); }
    el.addEventListener("click", done);
    el.addEventListener("animationend", function (e) { if (e.target === el) done(); });
    if (calm) setTimeout(done, 14000);
  }
  window.pdlTank = roll;
})();
