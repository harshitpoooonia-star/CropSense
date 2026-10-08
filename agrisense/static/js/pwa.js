// Install and offline support (Section 10).
//  - Registers the service worker (/sw.js).
//  - Shows the install card on Android Chrome (beforeinstallprompt) and the
//    "Add to Home Screen" hint on iPhone Safari, which has no install prompt.
//  - When the service worker answers a tool from its saved copy, puts the
//    "no internet, last answer from <time>" note on top; when it has no copy,
//    says so in the answer area instead of failing silently.
(function () {
  "use strict";
  var script = document.currentScript;
  var deferred = null;

  if ("serviceWorker" in navigator && script && script.dataset.sw) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(script.dataset.sw, { scope: "/" }).catch(function () {});
    });
  }

  function standalone() {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  }

  function isIos() {
    var ua = window.navigator.userAgent;
    return /iphone|ipad|ipod/i.test(ua) || (/macintosh/i.test(ua) && window.navigator.maxTouchPoints > 1);
  }

  function showInstall(kind) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-install]"), function (card) {
      card.hidden = false;
      Array.prototype.forEach.call(card.querySelectorAll("[data-install-android], [data-install-ios]"), function (part) {
        part.hidden = !part.hasAttribute("data-install-" + kind);
      });
    });
  }

  function hideInstall() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-install]"), function (card) { card.hidden = true; });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferred = event;
    showInstall("android");
  });
  window.addEventListener("appinstalled", function () { deferred = null; hideInstall(); });

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-install-android] button");
    if (!button || !deferred) { return; }
    deferred.prompt();
    deferred.userChoice.then(function () { deferred = null; hideInstall(); });
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (isIos() && !standalone()) { showInstall("ios"); }
  });

  function note(id) {
    var template = document.getElementById(id);
    return template ? template.content.firstElementChild.cloneNode(true) : null;
  }

  document.addEventListener("htmx:afterSwap", function (event) {
    var xhr = event.detail.xhr;
    var savedAt = xhr && Number(xhr.getResponseHeader("X-Offline-Saved-At"));
    var banner = savedAt && note("offline-saved");
    if (!banner) { return; }
    var when = new Date(savedAt).toLocaleString(document.documentElement.lang === "hi" ? "hi-IN" : "en-IN",
                                                { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
    var text = banner.querySelector("[data-saved-text]");
    text.textContent = text.textContent.replace("{time}", when);
    event.detail.target.insertBefore(banner, event.detail.target.firstChild);
  });

  document.addEventListener("htmx:sendError", function (event) {
    var target = event.detail.target;
    var message = note("offline-none");
    if (target && message) {
      target.replaceChildren(message);
    }
  });
})();
