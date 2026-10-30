// The Tally Wackers egg. See site/eggs.json: loaded only on their franchise page.
(function () {
  function tubeMan() {
    if (document.querySelector(".tube-pop")) return;
    var base = document.querySelector("link[rel=stylesheet]").href.replace("site.css", "");
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // reduced motion gets the still frame, not the flailing
    var el = calm ? new Image() : document.createElement("video");
    if (calm) {
      el.src = base + "tube-man.jpg";
    } else {
      el.muted = true; el.playsInline = true; el.autoplay = true; el.loop = true;
      el.setAttribute("muted", ""); el.setAttribute("playsinline", "");
      el.poster = base + "tube-man.jpg";
      el.src = base + "tube-man.mp4";
    }
    el.className = "tube-pop";
    el.setAttribute("aria-hidden", "true");
    document.body.appendChild(el);
    requestAnimationFrame(function () { requestAnimationFrame(function () { el.classList.add("up"); }); });
    function leave() {
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 700);
    }
    el.addEventListener("click", leave);
    setTimeout(leave, 9000);
  }
  window.pdlTubeMan = tubeMan;
})();
