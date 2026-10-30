// The console moose and Moose mode. See site/eggs.json.
(function () {
  try {
    console.log(
      "%c  \\|//      \\|//\n   \\|/______\\|/\n     |  o  o  |\n     |   __   |\n      \\_(  )_/\n         \\/\n\n Moose are loose!",
      "color:#6b3d1f;font:bold 13px monospace");
  } catch (e) {}

  function mooseMode() {
    if (document.documentElement.classList.contains("moose-mode")) return;
    document.documentElement.classList.add("moose-mode");
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!calm) {
      var img = new Image();
      img.src = document.querySelector("link[rel=stylesheet]").href.replace("site.css", "manic-moose.svg");
      img.alt = "";
      img.className = "moose-run";
      document.body.appendChild(img);
      setTimeout(function () { img.remove(); }, 4200);
    }
    // rename the innermost element, so markup inside a link (the antlers) survives
    var names = Array.prototype.map.call(document.querySelectorAll(".data a[href*='franchises/']"),
      function (a) { return a.querySelector(".moose") || a; });
    var was = names.map(function (n) { return n.textContent; });
    names.forEach(function (n) { n.textContent = "Moose"; });
    setTimeout(function () {
      names.forEach(function (n, i) { n.textContent = was[i]; });
      document.documentElement.classList.remove("moose-mode");
    }, 3000);
  }
  // the trades page's team filter sets the Moose loose too
  window.pdlMoose = mooseMode;

  var code = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
  var at = 0;
  addEventListener("keydown", function (e) {
    var k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    at = k === code[at] ? at + 1 : (k === code[0] ? 1 : 0);
    if (at < code.length) return;
    at = 0;
    mooseMode();
  });
})();
