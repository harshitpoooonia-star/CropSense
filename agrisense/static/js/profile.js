// Guest farm profile on this device (ADR-003, spec 01 R2).
// Sends it as the `profile` field with every HTMX request and form post, and
// saves whatever profile the server hands back in a
// <script type="application/json" data-profile-update> block ("null" clears it).
(function () {
  "use strict";
  var KEY = "agrisense.profile";

  function read() {
    try { return window.localStorage.getItem(KEY) || ""; } catch (e) { return ""; }
  }

  function write(value) {
    try {
      if (value === null) { window.localStorage.removeItem(KEY); }
      else { window.localStorage.setItem(KEY, value); }
      return true;
    } catch (e) { return false; }
  }

  function absorb(root) {
    var nodes = (root || document).querySelectorAll('script[type="application/json"][data-profile-update]');
    Array.prototype.forEach.call(nodes, function (node) {
      var text = node.textContent.trim();
      var saved = write(text === "null" ? null : text);
      if (!saved) {
        Array.prototype.forEach.call(document.querySelectorAll("[data-storage-warning]"), function (el) {
          el.hidden = false;
        });
      }
      node.parentNode.removeChild(node);
    });
  }

  function fill(form) {
    var input = form && form.querySelector && form.querySelector('input[name="profile"]');
    if (input && !input.value) { input.value = read(); }
  }

  document.addEventListener("DOMContentLoaded", function () { absorb(document); });
  document.addEventListener("submit", function (event) { fill(event.target); }, true);
  document.addEventListener("htmx:configRequest", function (event) {
    if (!event.detail.parameters.profile) { event.detail.parameters.profile = read(); }
  });
  document.addEventListener("htmx:afterSettle", function (event) { absorb(event.target); });
})();
