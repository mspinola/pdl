// The arrival clips. See site/eggs.json "clips": loaded only on those teams' franchise pages.
(function () {
  function clip(name, seconds) {
    if (document.querySelector(".clip-pop")) return;
    var base = document.querySelector("link[rel=stylesheet]").href.replace("site.css", "");
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // reduced motion gets the still frame, not the clip
    var el = calm ? new Image() : document.createElement("video");
    if (calm) {
      el.src = base + name + ".jpg";
    } else {
      el.muted = true; el.playsInline = true; el.autoplay = true; el.loop = true;
      el.setAttribute("muted", ""); el.setAttribute("playsinline", "");
      el.poster = base + name + ".jpg";
      el.src = base + name + ".mp4";
    }
    el.className = "clip-pop";
    el.setAttribute("aria-hidden", "true");
    document.body.appendChild(el);
    // read the layout first, so the slide starts from below rather than jumping
    el.getBoundingClientRect();
    el.classList.add("up");
    function leave() {
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 700);
    }
    el.addEventListener("click", leave);
    setTimeout(leave, seconds * 1000);
  }
  window.pdlClip = clip;
})();
