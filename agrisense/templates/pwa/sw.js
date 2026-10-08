// AgriSense service worker (Section 10). Rendered by agrisense/blueprints/pwa.py,
// which fills in the version and the content-hashed URLs to precache.
//
//  - Static files: cache first (their URLs change when their content does).
//  - Pages: network first; offline, the copy from the last visit, else /offline.
//  - Tool answers (HTMX POSTs the server marks as keepable): network first;
//    offline, the last answer, marked with the time it was saved so the page
//    can say it is old. Nothing is replayed that the server didn't mark.
//  - Accounts, PINs, the language switch and machine endpoints: left alone.
//
// Saved copies have the <script data-profile-update> block removed, so an old
// copy can never overwrite the farm saved on this phone.
"use strict";

var VERSION = {{ version | tojson }};
var SHELL = "agrisense-shell-" + VERSION;
var PAGES = "agrisense-pages";   // pages and last answers; profile.js empties it on logout
var PRECACHE = {{ precache | tojson }};
var OFFLINE_URL = {{ offline_url | tojson }};
var STATIC_PREFIX = {{ static_prefix | tojson }};
var NEVER = {{ never_cache | tojson }};
var KEEP_HEADER = {{ keep_header | tojson }};
var SAVED_AT_HEADER = {{ saved_at_header | tojson }};
var LAST_PREFIX = "/__last";
var PROFILE_BLOCK = /<script type="application\/json" data-profile-update>[\s\S]*?<\/script>/g;

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(SHELL)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (names) {
        return Promise.all(names.filter(function (name) {
          return name.indexOf("agrisense-shell-") === 0 && name !== SHELL;
        }).map(function (name) { return caches.delete(name); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

function never(path) {
  return NEVER.some(function (prefix) { return path.indexOf(prefix) === 0; });
}

// Same response, without the profile block, plus any extra headers.
function sanitised(response, extraHeaders) {
  return response.text().then(function (text) {
    var headers = new Headers(response.headers);
    Object.keys(extraHeaders || {}).forEach(function (name) { headers.set(name, extraHeaders[name]); });
    headers.delete("Content-Length");
    headers.delete("Content-Encoding");
    return new Response(text.replace(PROFILE_BLOCK, ""), { status: 200, headers: headers });
  });
}

function staticFile(request) {
  return caches.match(request).then(function (hit) {
    if (hit) { return hit; }
    return fetch(request).then(function (response) {
      if (response.ok) {
        var copy = response.clone();
        caches.open(SHELL).then(function (cache) { cache.put(request, copy); });
      }
      return response;
    }).catch(function () {
      // An older page may ask for an older version of a file: any version beats none.
      return caches.match(request, { ignoreSearch: true }).then(function (any) {
        return any || Response.error();
      });
    });
  });
}

function page(event) {
  var request = event.request;
  return fetch(request).then(function (response) {
    var type = response.headers.get("Content-Type") || "";
    if (response.ok && !response.redirected && type.indexOf("text/html") === 0) {
      var copy = response.clone();
      event.waitUntil(sanitised(copy).then(function (clean) {
        return caches.open(PAGES).then(function (cache) { return cache.put(request.url, clean); });
      }));
    }
    return response;
  }).catch(function () {
    return caches.open(PAGES)
      .then(function (cache) { return cache.match(request.url, { ignoreVary: true }); })
      .then(function (hit) { return hit || caches.match(OFFLINE_URL); });
  });
}

function toolAnswer(event, path) {
  var key = LAST_PREFIX + path;
  return fetch(event.request.clone()).then(function (response) {
    if (response.ok && response.headers.get(KEEP_HEADER)) {
      var copy = response.clone();
      var savedAt = {};
      savedAt[SAVED_AT_HEADER] = String(Date.now());
      event.waitUntil(sanitised(copy, savedAt).then(function (clean) {
        return caches.open(PAGES).then(function (cache) { return cache.put(key, clean); });
      }));
    }
    return response;
  }).catch(function () {
    return caches.open(PAGES)
      .then(function (cache) { return cache.match(key); })
      .then(function (hit) { return hit || Response.error(); });
  });
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin || never(url.pathname)) { return; }

  if (request.method === "GET" && url.pathname.indexOf(STATIC_PREFIX) === 0) {
    event.respondWith(staticFile(request));
  } else if (request.method === "GET" && request.mode === "navigate") {
    event.respondWith(page(event));
  } else if (request.method === "POST" && request.headers.get("HX-Request")) {
    event.respondWith(toolAnswer(event, url.pathname));
  }
});
