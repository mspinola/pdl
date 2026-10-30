// The Ho Train egg. See site/eggs.json "grumpy_train": loaded only on their franchise page.
// A scowling steam engine chugs in from the right, stops mid-screen to grumble one line, and
// chugs off to the left. Reduced motion gets the engine parked in the corner, grumbling.
(function () {
  // 260 by 150, facing left: the face is on the smokebox door at the front
  var ENGINE =
    "<svg viewBox='0 0 260 150' aria-hidden='true'>" +
    "<g class='train-smoke'><circle cx='100' cy='22' r='9'/><circle cx='108' cy='12' r='7'/><circle cx='96' cy='6' r='5'/></g>" +
    "<rect x='92' y='34' width='16' height='26' fill='#333'/><rect x='88' y='28' width='24' height='8' rx='2' fill='#222'/>" +
    "<rect x='70' y='58' width='112' height='56' rx='6' fill='#2e6b4f'/>" +
    "<rect x='110' y='58' width='4' height='56' fill='#c9a227'/><rect x='150' y='58' width='4' height='56' fill='#c9a227'/>" +
    "<path d='M122 58 A12 12 0 0 1 146 58 Z' fill='#c9a227'/>" +
    "<rect x='180' y='40' width='60' height='74' fill='#8b2e2e'/>" +
    "<rect x='192' y='52' width='24' height='20' rx='2' fill='#f5d76e'/>" +
    "<rect x='174' y='34' width='72' height='8' rx='2' fill='#333'/>" +
    "<rect x='40' y='112' width='205' height='8' fill='#222'/>" +
    "<path d='M46 116 L18 140 H62 Z' fill='#666'/>" +
    "<circle cx='55' cy='85' r='34' fill='#d9d6cc' stroke='#555' stroke-width='3'/>" +
    "<path d='M35 66 L51 74 M75 66 L59 74' stroke='#222' stroke-width='4' stroke-linecap='round'/>" +
    "<circle cx='45' cy='80' r='4' fill='#222'/><circle cx='65' cy='80' r='4' fill='#222'/>" +
    "<path d='M42 103 Q55 92 68 103' fill='none' stroke='#222' stroke-width='3.5' stroke-linecap='round'/>" +
    "<g class='train-wheel' style='transform-origin: 90px 130px'><circle cx='90' cy='130' r='16' fill='#222' stroke='#aaa' stroke-width='3'/>" +
    "<path d='M90 116 V144 M76 130 H104' stroke='#aaa' stroke-width='2'/></g>" +
    "<g class='train-wheel' style='transform-origin: 135px 130px'><circle cx='135' cy='130' r='16' fill='#222' stroke='#aaa' stroke-width='3'/>" +
    "<path d='M135 116 V144 M121 130 H149' stroke='#aaa' stroke-width='2'/></g>" +
    "<g class='train-wheel' style='transform-origin: 205px 134px'><circle cx='205' cy='134' r='12' fill='#222' stroke='#aaa' stroke-width='3'/>" +
    "<path d='M205 124 V144 M195 134 H215' stroke='#aaa' stroke-width='2'/></g>" +
    "<line x1='90' y1='136' x2='135' y2='136' stroke='#bbb' stroke-width='4' stroke-linecap='round'/>" +
    "</svg>";

  function grumble(lines) {
    if (document.querySelector(".train")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "train" + (calm ? " train-calm" : "");
    el.setAttribute("role", "status");
    var bubble = document.createElement("p");
    bubble.className = "train-bubble";
    bubble.textContent = lines[Math.floor(Math.random() * lines.length)];
    el.appendChild(bubble);
    el.insertAdjacentHTML("beforeend", ENGINE);
    document.body.appendChild(el);
    // the page and its styles can be a deploy apart for a few minutes: skip this visit rather than show it unstyled
    if (getComputedStyle(el).position !== "fixed") { el.remove(); return; }
    el.addEventListener("click", function () { el.remove(); });
    // the crossing is a CSS animation; when it ends, so does the engine
    el.addEventListener("animationend", function (e) { if (e.target === el) el.remove(); });
    if (calm) setTimeout(function () { el.remove(); }, 6000);
  }
  window.pdlGrumpyTrain = grumble;
})();
