// The F-Jackie egg. See site/eggs.json: type "barney" anywhere on the site.
(function () {
  var word = "barney";
  var typed = "";
  addEventListener("keydown", function (e) {
    var t = e.target;
    if (t && (t.isContentEditable || /^(input|textarea|select)$/i.test(t.tagName))) return;
    if (e.key.length !== 1) return;
    typed = (typed + e.key.toLowerCase()).slice(-word.length);
    if (typed !== word || document.querySelector(".barney-pop")) return;
    typed = "";
    document.documentElement.classList.add("barney-mode");
    var img = new Image();
    img.src = document.querySelector("link[rel=stylesheet]").href.replace("site.css", "barney.jpg");
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
  });
})();
