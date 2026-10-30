// The Tally Wackers' tank. See site/eggs.json "tank": loaded only on their franchise page.
// A tank flying the tank season's flag rolls in from the left, stops mid-screen under a report
// card on that season (from eggs.tank_card()), and rolls off to the right. Reduced motion gets
// it parked at the left with the card up.
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
    el.appendChild(card);
    el.insertAdjacentHTML("beforeend", tank(c.flag));
    document.body.appendChild(el);
    el.addEventListener("click", function () { el.remove(); });
    el.addEventListener("animationend", function (e) { if (e.target === el) el.remove(); });
    if (calm) setTimeout(function () { el.remove(); }, 14000);
  }
  window.pdlTank = roll;
})();
