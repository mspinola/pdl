// The Beers rumor mill. See site/eggs.json "beers": loaded only on their franchise page.
// A news ticker crawls along the bottom of the screen with what Beers has heard, every word of
// it made up. Hovering holds it, and its button closes it. Reduced motion gets one rumor at a
// time, without the crawl.
(function () {
  function mill(c) {
    if (document.querySelector(".rumor")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "rumor";
    el.setAttribute("role", "marquee");
    var label = document.createElement("b");
    label.textContent = c.label;
    var track = document.createElement("div");
    track.className = "rumor-track";
    var text = document.createElement("span");
    var x = document.createElement("button");
    x.type = "button"; x.textContent = "×"; x.setAttribute("aria-label", "Close");
    track.appendChild(text);
    el.appendChild(label);
    el.appendChild(track);
    el.appendChild(x);
    document.body.appendChild(el);
    var timer;
    if (calm) {
      var i = 0;
      text.textContent = c.rumors[0];
      timer = setInterval(function () { i = (i + 1) % c.rumors.length; text.textContent = c.rumors[i]; }, 6000);
    } else {
      text.textContent = c.rumors.join("   ★   ");
      // about eight characters a second, whatever the length
      text.style.animationDuration = Math.round(text.textContent.length / 8) + "s";
      text.classList.add("crawl");
    }
    el.getBoundingClientRect();
    el.classList.add("up");
    x.addEventListener("click", function () {
      clearInterval(timer);
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 400);
    });
  }
  window.pdlRumors = mill;
})();
