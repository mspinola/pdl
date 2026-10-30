// The arrival clips, and the Karpet Munchers' magazine. See site/eggs.json "clips" and
// "magazine": loaded only on those teams' franchise pages.
(function () {
  // a clip is a local <name>.mp4 with <name>.jpg as its still, or, given youtube, that
  // video in YouTube's own player (muted, so the browser lets it start on its own)
  function clip(name, seconds, youtube) {
    if (document.querySelector(".clip-pop")) return;
    var base = document.querySelector("link[rel=stylesheet]").href.replace(/site\.css.*$/, "");
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
    // a YouTube player has a button in it, so only the others are hidden from screen readers
    if (!(youtube && !calm)) el.setAttribute("aria-hidden", "true");
    pop(el, seconds, youtube && !calm ? el.querySelector("button") : el);
  }

  // slide el up in the corner, and off again after seconds (0 stays) or a click on closer
  function pop(el, seconds, closer) {
    document.body.appendChild(el);
    // read the layout first, so the slide starts from below rather than jumping
    el.getBoundingClientRect();
    el.classList.add("up");
    function leave() {
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 700);
    }
    closer.addEventListener("click", leave);
    if (seconds) setTimeout(leave, seconds * 1000);
  }

  // the magazine is built into its page as a <template>
  function magazine(seconds) {
    if (document.querySelector(".clip-pop")) return;
    var el = document.getElementById("pdl-magazine").content.firstElementChild.cloneNode(true);
    pop(el, seconds, el);
  }
  window.pdlClip = clip;
  window.pdlMagazine = magazine;
})();
