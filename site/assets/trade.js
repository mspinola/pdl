// The Couchfire egg. See site/eggs.json "trade_offer": loaded only on their franchise page.
// A trade proposal nobody should accept. Decline runs from the pointer a few times before it
// gives in, Accept is already too late, and however the offer ends, the couch catches fire
// (assets/clip.js, which this page also loads).
(function () {
  function offer(cfg) {
    if (document.querySelector(".trade-offer")) return;
    var li = function (items) { return items.map(function (t) { return "<li>" + t + "</li>"; }).join(""); };
    var back = document.createElement("div");
    back.className = "trade-back";
    back.innerHTML =
      "<div class='trade-offer' role='dialog' aria-modal='true' aria-labelledby='trade-h'>" +
      "<p class='trade-kicker'>Trade proposal</p>" +
      "<h2 id='trade-h'>" + cfg.from + " proposes a trade</h2>" +
      "<div class='trade-sides'><div><h3>You give</h3><ul>" + li(cfg.give) + "</ul></div>" +
      "<div><h3>You get</h3><ul>" + li(cfg.get) + "</ul></div></div>" +
      "<p class='trade-note'>Comment from " + cfg.from + ": “" + cfg.note + "”</p>" +
      "<p class='trade-result' aria-live='polite'></p>" +
      "<div class='trade-buttons'><button type='button' class='trade-yes'>Accept</button>" +
      "<button type='button' class='trade-no'>Decline</button></div></div>";
    document.body.appendChild(back);
    // the page and its styles can be a deploy apart for a few minutes: skip this visit rather than show it unstyled
    if (getComputedStyle(back).position !== "fixed") { back.remove(); return; }
    var card = back.querySelector(".trade-offer");
    var yes = back.querySelector(".trade-yes"), no = back.querySelector(".trade-no");
    var result = back.querySelector(".trade-result");
    back.getBoundingClientRect();
    back.classList.add("up");
    yes.focus();

    var over = false;
    function end(text) {
      if (over) return;
      over = true;
      result.textContent = text;
      card.classList.add("answered");
      setTimeout(function () {
        back.classList.remove("up");
        setTimeout(function () {
          back.remove();
          if (window.pdlClip) pdlClip(cfg.clip, cfg.clip_seconds);
        }, 400);
      }, 2600);
    }
    yes.addEventListener("click", function () { end(cfg.accepted); });

    // Decline dodges the pointer (or the first taps, on a touch screen) a few times, then holds still
    var dodges = 0;
    function dodge(e) {
      if (over || dodges >= cfg.dodges) return;
      dodges++;
      if (e.type === "click") e.preventDefault();
      var room = card.clientWidth - no.offsetWidth - 40;
      // it sits at the card's right edge, so it only jumps left
      no.style.transform = "translate(" + Math.round(-Math.random() * room) + "px, " +
        Math.round((Math.random() - 0.5) * 60) + "px)";
      if (dodges === cfg.dodges) no.textContent = "Decline (fine)";
      return true;
    }
    no.addEventListener("pointerenter", function (e) { if (e.pointerType === "mouse") dodge(e); });
    no.addEventListener("click", function (e) {
      if (dodges < cfg.dodges && dodge(e)) return;
      end(cfg.declined);
    });
    addEventListener("keydown", function esc(e) {
      if (e.key !== "Escape" || over) return;
      removeEventListener("keydown", esc);
      end(cfg.declined);
    });
  }
  window.pdlTradeOffer = offer;
})();
