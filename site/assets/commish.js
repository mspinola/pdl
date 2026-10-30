// The commissioner's build log, on the Moose's franchise page. See site/eggs.json "build_log".
// A terminal slides up in the corner and types out a site build nobody asked to watch. A line
// starting "$ " is typed a character at a time; a "|" in a line is a pause, as for "... done".
(function () {
  function log(lines) {
    if (document.querySelector(".commish")) return;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var el = document.createElement("div");
    el.className = "commish";
    el.setAttribute("role", "log");
    el.innerHTML = "<div class='commish-bar'><span></span><span></span><span></span>" +
      "<b>commissioner@pdl: ~/pdl</b><button type='button' aria-label='Close'>×</button></div><pre></pre>";
    document.body.appendChild(el);
    // the page and its styles can be a deploy apart for a few minutes: skip this visit rather than show it unstyled
    if (getComputedStyle(el).position !== "fixed") { el.remove(); return; }
    var pre = el.querySelector("pre");
    el.getBoundingClientRect();
    el.classList.add("up");
    var timers = [];
    function leave() {
      timers.forEach(clearTimeout);
      el.classList.remove("up");
      setTimeout(function () { el.remove(); }, 600);
    }
    el.querySelector("button").addEventListener("click", leave);
    if (calm) {
      pre.textContent = lines.map(function (l) { return l.replace("|", ""); }).join("\n");
      timers.push(setTimeout(leave, 12000));
      return;
    }
    // the whole script as one queue of (delay, text to append)
    var queue = [], t = 500;
    lines.forEach(function (line, i) {
      var head = i ? "\n" : "";
      if (line.indexOf("$ ") === 0) {
        queue.push([t, head + "$ "]);
        line.slice(2).split("").forEach(function (ch) { t += 45; queue.push([t, ch]); });
        t += 500;
      } else {
        line.split("|").forEach(function (part, j) {
          t += j ? 550 : 250;
          queue.push([t, (j ? "" : head) + part]);
        });
      }
    });
    queue.forEach(function (q) {
      timers.push(setTimeout(function () {
        pre.textContent += q[1];
        pre.scrollTop = pre.scrollHeight;
      }, q[0]));
    });
    timers.push(setTimeout(function () { pre.classList.add("idle"); }, t));
    // there is a lot to read, so it stays half a minute after the last line
    timers.push(setTimeout(leave, t + 30000));
  }
  window.pdlBuildLog = log;
})();
