// The arrival clips. See site/eggs.json "clips": loaded only on those teams' franchise pages.
(function () {
  // a clip is a local <name>.mp4 with <name>.jpg as its still, or, given youtube, that
  // video in YouTube's own player (muted, so the browser lets it start on its own)
  function clip(name, seconds, youtube) {
    if (document.querySelector(".clip-pop")) return;
    var base = document.querySelector("link[rel=stylesheet]").href.replace("site.css", "");
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var still = youtube ? "https://i.ytimg.com/vi/" + youtube + "/hqdefault.jpg" : base + name + ".jpg";
    // reduced motion gets the still frame, not the clip
    var el;
    if (calm) {
      el = new Image();
      el.src = still;
    } else if (youtube) {
      el = document.createElement("div");
      var f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + youtube +
        "?autoplay=1&mute=1&playsinline=1&rel=0&modestbranding=1";
      f.allow = "autoplay; encrypted-media";
      f.title = name;
      el.appendChild(f);
      // the player takes its own clicks (play, sound), so it gets a close button
      var x = document.createElement("button");
      x.type = "button"; x.textContent = "\u00d7"; x.setAttribute("aria-label", "Close");
      el.appendChild(x);
      el.classList.add("clip-yt");
    } else {
      el = document.createElement("video");
      el.muted = true; el.playsInline = true; el.autoplay = true; el.loop = true;
      el.setAttribute("muted", ""); el.setAttribute("playsinline", "");
      el.poster = still;
      el.src = base + name + ".mp4";
    }
    el.classList.add("clip-pop");
    el.setAttribute("aria-hidden", "true");
    document.body.appendChild(el);
    // read the layout first, so the slide starts from below rather than jumping
    el.getBoundingClientRect();
    el.classList.add("up");
    function leave() {
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 700);
    }
    (youtube && !calm ? el.querySelector("button") : el).addEventListener("click", leave);
    // seconds 0 stays until closed
    if (seconds) setTimeout(leave, seconds * 1000);
  }
  window.pdlClip = clip;
})();
