/* JND Track & Trace — theme toggle + copy-to-clipboard. Degrades safely if
   storage/clipboard APIs are unavailable (no exceptions thrown). */
(function () {
  var root = document.documentElement;

  function setCookie(v) {
    try { document.cookie = "jnd_theme=" + v + ";path=/;max-age=31536000;samesite=lax"; } catch (e) {}
  }
  function current() { return root.getAttribute("data-theme") === "light" ? "light" : "neon"; }
  function apply(t) {
    root.setAttribute("data-theme", t);
    var b = document.getElementById("theme-toggle");
    if (!b) return;
    var neon = t === "neon";
    b.setAttribute("aria-pressed", String(neon));
    b.setAttribute("aria-label", neon ? "Switch to light theme" : "Switch to neon theme");
    var lbl = b.querySelector(".tt-label");
    if (lbl) lbl.textContent = neon ? "Neon" : "Light";
  }

  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    apply(current());
    toggle.addEventListener("click", function () {
      var t = current() === "neon" ? "light" : "neon";
      apply(t); setCookie(t);
    });
  }

  var sr = document.getElementById("sr-status");
  function announce(msg) {
    if (!sr) return;
    sr.textContent = "";
    setTimeout(function () { sr.textContent = msg; }, 30);
  }
  function flash(btn, ok) {
    var label = btn.querySelector(".copy-label");
    var prev = label ? label.textContent : "";
    if (label) label.textContent = ok ? "Copied" : "Press Ctrl+C";
    btn.classList.toggle("is-copied", ok);
    announce(ok ? "Copied " + (btn.getAttribute("data-copy") || "") : "Copy failed. Press Control C to copy.");
    setTimeout(function () { if (label) label.textContent = prev; btn.classList.remove("is-copied"); }, 1600);
  }
  function copy(text, btn) {
    function fallback() {
      try {
        var ta = document.createElement("textarea");
        ta.value = text; ta.setAttribute("readonly", "");
        ta.style.position = "fixed"; ta.style.top = "-1000px";
        document.body.appendChild(ta); ta.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(ta); flash(btn, ok);
      } catch (e) { flash(btn, false); }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash(btn, true); }, fallback);
    } else { fallback(); }
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (!b) return;
    e.preventDefault();
    copy(b.getAttribute("data-copy"), b);
  });
})();
