// Field setup wizard, step 1 (spec 01 R1, ADR-005).
// Loads Leaflet only when a [data-map] element is on the page, lets the
// farmer drag or tap a pin, or use the phone's GPS. Without JS the
// "choose district" form still works.
(function () {
  "use strict";
  var leaflet = null;

  function loadLeaflet(el) {
    if (leaflet) { return leaflet; }
    leaflet = new Promise(function (resolve, reject) {
      var css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = el.dataset.leafletCss;
      document.head.appendChild(css);
      var js = document.createElement("script");
      js.src = el.dataset.leafletJs;
      js.onload = function () { resolve(window.L); };
      js.onerror = reject;
      document.head.appendChild(js);
    });
    return leaflet;
  }

  function setPin(form, lat, lon, source) {
    form.querySelector('[name="lat"]').value = lat.toFixed(5);
    form.querySelector('[name="lon"]').value = lon.toFixed(5);
    form.querySelector('[name="location_source"]').value = source;
    form.querySelector('[data-pin-submit]').disabled = false;
  }

  function initMap(el) {
    if (el.dataset.ready) { return; }
    el.dataset.ready = "1";
    var form = el.closest("form");
    loadLeaflet(el).then(function (L) {
      var lat = parseFloat(el.dataset.lat), lon = parseFloat(el.dataset.lon);
      var hasPin = !isNaN(lat) && !isNaN(lon);
      var map = L.map(el, { zoomControl: true }).setView(
        hasPin ? [lat, lon] : [parseFloat(el.dataset.centerLat), parseFloat(el.dataset.centerLon)],
        hasPin ? 15 : 9
      );
      // Plain credit line: Leaflet's default prefix adds a flag icon.
      map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
      L.tileLayer(el.dataset.tiles, { maxZoom: 19, attribution: el.dataset.attribution }).addTo(map);
      var icon = L.divIcon({ className: "farm-pin", iconSize: [28, 28], iconAnchor: [14, 28] });
      var marker = null;
      function place(latlng, source) {
        if (!marker) {
          marker = L.marker(latlng, { draggable: true, icon: icon, keyboard: true }).addTo(map);
          marker.on("dragend", function () { var p = marker.getLatLng(); setPin(form, p.lat, p.lng, "map"); });
        } else {
          marker.setLatLng(latlng);
        }
        setPin(form, latlng.lat, latlng.lng, source);
      }
      if (hasPin) { place(L.latLng(lat, lon), form.querySelector('[name="location_source"]').value || "map"); }
      map.on("click", function (e) { place(e.latlng, "map"); });
      el.mapPlace = function (latlng, zoom) { map.setView(latlng, zoom); place(latlng, "gps"); };
    }).catch(function () {
      var error = form.querySelector("[data-map-error]");
      if (error) { error.hidden = false; }
    });
  }

  function useGps(button) {
    var form = button.closest("form");
    var error = form.querySelector("[data-gps-error]");
    if (!navigator.geolocation) { error.hidden = false; return; }
    button.disabled = true;
    navigator.geolocation.getCurrentPosition(function (pos) {
      button.disabled = false;
      error.hidden = true;
      var el = form.querySelector("[data-map]");
      if (el && el.mapPlace && window.L) {
        el.mapPlace(window.L.latLng(pos.coords.latitude, pos.coords.longitude), 16);
      } else {
        setPin(form, pos.coords.latitude, pos.coords.longitude, "gps");
      }
    }, function () {
      button.disabled = false;
      error.hidden = false;
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  }

  function scan(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll("[data-map]"), initMap);
  }

  document.addEventListener("DOMContentLoaded", function () { scan(document); });
  document.addEventListener("htmx:load", function (event) { scan(event.target); });
  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-gps]");
    if (button) { event.preventDefault(); useGps(button); }
  });
})();
