// The Texas Nashvillians egg. See site/eggs.json "outage": loaded only on their franchise page.
// The page flickers and switches off like an old television, an outage notice comes up, and a
// bucket truck drives in, raises its boom to the pole and puts the power back. A click skips it.
(function () {
  var NOTICE =
    "<div class='outage-notice'>" +
    "<b><span class='o-out'>⚡ Power outage</span><span class='o-on'>Power restored</span></b>" +
    "<p><span class='o-out'>Outage reported in your area. A crew has been dispatched.</span>" +
    "<span class='o-on'>Thank you for your patience.</span></p>" +
    "<small>Texas Nashvillians Electric Cooperative</small></div>";

  // a 420 by 200 street: a house, the pole and its lines, and the truck. The boom and its
  // bucket each turn about their own (0, 0), so they sit in translated groups.
  var STREET =
    "<svg viewBox='0 0 420 200' aria-hidden='true'>" +
    "<path d='M16 132 L57 98 L98 132 Z' fill='#2a2a2a'/>" +
    "<rect x='24' y='130' width='66' height='60' fill='#1e1e1e' stroke='#333'/>" +
    "<rect class='win' x='34' y='144' width='16' height='14'/><rect class='win' x='64' y='144' width='16' height='14'/>" +
    "<rect x='50' y='165' width='14' height='25' fill='#333'/>" +
    "<line x1='0' y1='190' x2='420' y2='190' stroke='#333' stroke-width='2'/>" +
    "<rect x='344' y='18' width='12' height='172' fill='#6b4f36'/>" +
    "<rect x='300' y='38' width='100' height='7' fill='#6b4f36'/>" +
    "<rect x='309' y='30' width='6' height='8' fill='#9ab'/><rect x='385' y='30' width='6' height='8' fill='#9ab'/>" +
    "<rect x='358' y='60' width='20' height='28' rx='3' fill='#7d8a96'/>" +
    "<path class='wire' d='M0 32 H312 M388 32 H420 M312 34 Q180 72 70 118'/>" +
    "<g class='truck'>" +
    "<rect x='110' y='148' width='108' height='28' rx='2' fill='#f2f0ea'/>" +
    "<rect x='116' y='152' width='30' height='9' fill='#dcd9cf'/><rect x='150' y='152' width='30' height='9' fill='#dcd9cf'/>" +
    "<path d='M218 176 V136 Q218 130 224 130 H252 L266 152 V176 Z' fill='#f2f0ea'/>" +
    "<path d='M224 136 H250 L259 150 H224 Z' fill='#6aa0d8'/>" +
    "<rect x='110' y='163' width='156' height='4' fill='#eb6834'/>" +
    "<rect x='264' y='168' width='6' height='6' fill='#999'/>" +
    "<rect class='beacon' x='232' y='125' width='10' height='5' rx='1'/>" +
    "<circle cx='140' cy='178' r='12' fill='#1c1c1c' stroke='#777' stroke-width='3'/>" +
    "<circle cx='245' cy='178' r='12' fill='#1c1c1c' stroke='#777' stroke-width='3'/>" +
    "<rect x='215' y='134' width='20' height='12' fill='#cfccc2'/>" +
    "<g transform='translate(225 140)'><g class='boom'>" +
    "<rect x='0' y='-3.5' width='135' height='7' rx='3.5' fill='#e0ded6'/>" +
    "<g transform='translate(135 0)'><g class='bucket'>" +
    "<rect x='-1.5' y='-6' width='3' height='6' fill='#e0ded6'/>" +
    "<rect x='-11' y='-26' width='22' height='20' rx='2' fill='#eb6834'/>" +
    "<circle cx='0' cy='-31' r='6' fill='#d9a77a'/><path d='M-7 -33 A7 7 0 0 1 7 -33 Z' fill='#ffd400'/>" +
    "</g></g></g></g></g>" +
    "<path class='spark' d='M312 18 L316 28 L326 24 L318 32 L328 38 L316 36 L312 46 L308 36 L296 38 L306 32 L298 24 L308 28 Z'/>" +
    "</svg>";

  function outage() {
    var root = document.documentElement;
    if (root.classList.contains("outage")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var scene = document.createElement("div");
    scene.className = "outage-scene";
    scene.setAttribute("role", "status");
    scene.title = "Click to restore power";
    scene.innerHTML = NOTICE + (calm ? "" : STREET);
    // the screen collapses toward the middle of what is in view, not of the whole page
    document.body.style.transformOrigin = "50% " + (scrollY + innerHeight / 2) + "px";
    var timers = [];
    function at(ms, f) { timers.push(setTimeout(f, ms)); }
    function step(c) { return function () { scene.classList.add(c); }; }
    function restore() {
      timers.forEach(clearTimeout);
      timers = [];
      scene.classList.add("fixed", "done");
      root.classList.remove("outage-off");
      root.classList.add("outage-on");
      at(700, function () {
        scene.remove();
        root.classList.remove("outage", "outage-flicker", "outage-on");
        document.body.style.transformOrigin = "";
      });
    }
    scene.addEventListener("click", restore);
    root.classList.add("outage");
    // the scene sits outside <body>, which is what switches off
    if (calm) {
      root.classList.add("outage-off");
      root.appendChild(scene);
      at(50, step("show"));
      at(3000, restore);
      return;
    }
    root.classList.add("outage-flicker");
    at(900, function () { root.classList.add("outage-off"); root.appendChild(scene); });
    at(1500, step("show"));    // the notice comes up and the truck drives in
    at(3300, step("lift"));    // the boom goes up to the pole
    at(4500, step("fixed"));   // a spark, the lines go live, the notice says so
    at(5800, restore);
  }
  window.pdlOutage = outage;
})();
