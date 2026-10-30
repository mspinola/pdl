// The Dunbar Dogs egg. See site/eggs.json "y2k": loaded only on their franchise page.
// A moment after arrival the page turns into a home page from 2000, headed by eggs.y2k()'s
// <template>, until a button brings the modern one back.
(function () {
  function y2k() {
    var root = document.documentElement;
    if (root.classList.contains("y2k")) return;
    var top = document.getElementById("pdl-y2k").content.firstElementChild.cloneNode(true);
    // a hit counter has six digits, mostly zeros
    top.querySelector(".y2k-counter span").textContent = ("00000" + (1000 + Math.floor(Math.random() * 9000))).slice(-6);
    var main = document.querySelector("main");
    main.insertBefore(top, main.firstChild);
    root.classList.add("y2k");
    top.querySelector(".y2k-off").addEventListener("click", function () {
      top.remove();
      root.classList.remove("y2k");
    });
  }
  window.pdlY2K = y2k;
})();
