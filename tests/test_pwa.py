"""Section 10: install (manifest, icons), service worker, offline page,
versioned static URLs with cache headers, compression, keepable answers."""

import json
import re
from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

from agrisense import assets
from agrisense import farm_profile as fp
from agrisense.blueprints import pwa
from agrisense.offline import HEADER, NEVER_CACHE

HX = {"HX-Request": "true"}
STATIC = Path(__file__).resolve().parent.parent / "agrisense" / "static"


def static_urls(html):
    return re.findall(r'(?:href|src)="(/static/[^"]+)"', html)


# ---------------------------------------------------------------- manifest and icons


@pytest.mark.parametrize("lang", ["hi", "en"])
def test_manifest_is_installable(client, lang):
    r = client.get(f"/manifest.webmanifest?lang={lang}")
    assert r.status_code == 200 and r.mimetype == "application/manifest+json"
    m = json.loads(r.get_data(as_text=True))
    assert m["lang"] == lang and m["name"] and m["short_name"]
    assert m["start_url"] == "/today" and m["scope"] == "/" and m["display"] == "standalone"
    assert m["theme_color"] == "#5a3b22" and m["background_color"] == "#faf7f2"
    sizes = {(i["sizes"], i["purpose"]) for i in m["icons"]}
    assert sizes == {("192x192", "any"), ("192x192", "maskable"), ("512x512", "any"), ("512x512", "maskable")}
    for icon in m["icons"]:
        assert client.get(icon["src"]).status_code == 200


def test_manifest_description_follows_the_language(client):
    hi = json.loads(client.get("/manifest.webmanifest?lang=hi").get_data(as_text=True))
    en = json.loads(client.get("/manifest.webmanifest?lang=en").get_data(as_text=True))
    assert hi["description"] != en["description"] and "No sign-up" in en["description"]
    other = json.loads(client.get("/manifest.webmanifest?lang=fr").get_data(as_text=True))
    assert other["lang"] == "hi"


def test_icon_pngs_have_the_right_sizes():
    import struct

    for name, size in {"icon-192.png": 192, "icon-512.png": 512, "apple-touch-icon.png": 180}.items():
        head = (STATIC / "icons" / name).read_bytes()[:24]
        assert head[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", head[16:24]) == (size, size)


def test_every_page_links_manifest_icons_and_pwa_script(client):
    html = client.get("/").get_data(as_text=True)
    assert 'rel="manifest" href="/manifest.webmanifest?lang=' in html
    assert 'rel="apple-touch-icon"' in html and 'rel="icon"' in html
    assert re.search(r'src="/static/js/pwa\.js\?v=\w+" data-sw="/sw\.js" defer', html)
    assert 'id="offline-saved"' in html and 'id="offline-none"' in html and "{time}" in html


def test_install_card_on_home_and_more_hidden_until_the_phone_can_install(client):
    client.set_cookie("lang", "en")
    for path in ("/", "/more"):
        html = client.get(path).get_data(as_text=True)
        assert "<section data-install hidden" in html and "Add to home screen" in html
        assert "<div data-install-android hidden" in html and "<p data-install-ios hidden" in html


# ---------------------------------------------------------------- service worker


def test_service_worker_headers_and_scope(client):
    r = client.get("/sw.js")
    assert r.status_code == 200 and r.mimetype == "text/javascript"
    assert r.headers["Cache-Control"] == "no-cache"


def test_service_worker_precaches_files_that_exist(client):
    js = client.get("/sw.js").get_data(as_text=True)
    urls = json.loads(re.search(r"var PRECACHE = (\[.*?\]);", js).group(1))
    assert "/offline" in urls and any(u.startswith("/static/css/app.css?v=") for u in urls)
    assert sum("/static/fonts/" in u for u in urls) == 4
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_service_worker_leaves_accounts_and_machine_endpoints_alone(client):
    js = client.get("/sw.js").get_data(as_text=True)
    never = json.loads(re.search(r"var NEVER = (\[.*?\]);", js).group(1))
    assert never == list(NEVER_CACHE)
    for path in ("/login", "/logout", "/pin/reset", "/helper/pin-reset", "/farm/save", "/farm/delete",
                 "/lang/en", "/api/profile", "/internal/refresh/prices"):
        assert any(path.startswith(p) for p in never), path


def test_service_worker_strips_the_profile_block_it_would_replay(client):
    js = client.get("/sw.js").get_data(as_text=True)
    pattern = re.search(r"var PROFILE_BLOCK = /(.*)/g;", js).group(1).replace("\\/", "/")
    block = '<p>x</p><script type="application/json" data-profile-update>{"v": 1}</script><p>y</p>'
    assert re.sub(pattern, "", block) == "<p>x</p><p>y</p>"


def test_cache_version_changes_with_assets(monkeypatch):
    a = pwa.cache_version(["/static/css/app.css?v=1"])
    assert pwa.cache_version(["/static/css/app.css?v=2"]) != a
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    assert pwa.cache_version(["/static/css/app.css?v=1"]) != a


def test_background_fetches_do_not_swallow_a_pending_profile_sync(client):
    with client.session_transaction() as s:
        s["profile_sync"] = "clear"
    client.get("/sw.js")
    client.get("/offline")
    html = client.get("/").get_data(as_text=True)
    assert '<script type="application/json" data-profile-update>null</script>' in html


def test_offline_page_is_in_both_languages(client):
    client.set_cookie("lang", "en")
    html = client.get("/offline").get_data(as_text=True)
    assert 'lang="hi"' in html and 'lang="en"' in html
    assert "इंटरनेट नहीं है" in html and "No internet" in html
    assert 'href=""' in html  # retry reloads the address asked for


# ---------------------------------------------------------------- static assets


def test_static_urls_carry_a_content_hash_except_fonts(client):
    urls = static_urls(client.get("/").get_data(as_text=True))
    for url in urls:
        if "/fonts/" in url:
            assert "?v=" not in url
        else:
            assert re.search(r"\?v=[0-9a-f]{12}$", url), url


def test_versioned_static_is_cached_for_a_year(client):
    css = next(u for u in static_urls(client.get("/").get_data(as_text=True)) if "app.css" in u)
    cc = client.get(css).headers["Cache-Control"]
    assert "max-age=31536000" in cc and "immutable" in cc
    stale = client.get("/static/css/app.css?v=000000000000").headers.get("Cache-Control", "")
    assert "immutable" not in stale


def test_fonts_cached_for_a_month(client):
    cc = client.get("/static/fonts/mukta-400-latin.woff2").headers["Cache-Control"]
    assert "max-age=2592000" in cc and "immutable" not in cc


def test_version_follows_file_content(tmp_path):
    f = tmp_path / "a.css"
    f.write_text("a{}")
    first = assets.version(str(tmp_path), "a.css")
    f.write_text("b{color:red}")
    assert assets.version(str(tmp_path), "a.css") != first
    assert assets.version(str(tmp_path), "missing.css") is None
    assert assets.version(str(tmp_path), "../escape.css") is None


def test_html_and_css_are_compressed(client):
    r = client.get("/", headers={"Accept-Encoding": "br, gzip"})
    assert r.headers["Content-Encoding"] in ("br", "gzip") and "Accept-Encoding" in r.headers["Vary"]
    css = next(u for u in static_urls(client.get("/").get_data(as_text=True)) if "app.css" in u)
    assert client.get(css, headers={"Accept-Encoding": "br"}).headers["Content-Encoding"] == "br"


# ---------------------------------------------------------------- keepable answers


def ready_profile():
    p = fp.empty()
    fp.apply_where(p, MultiDict({"location_source": "district", "district_code": "UP-bulandshahr"}))
    fp.apply_area(p, MultiDict({"area": "2.5", "area_unit": "acre"}))
    fp.apply_water(p, MultiDict({"irrigation_source": "tubewell"}))
    return p


def test_scheme_results_are_keepable_but_questions_are_not(client):
    form = {"answers": json.dumps({"state": "UP"}), "profile": json.dumps(ready_profile())}
    question = client.post("/schemes/answer/ownership", headers=HX, data={**form, "value": "owner"})
    assert question.status_code == 200 and HEADER not in question.headers
    final = client.post("/schemes/answer/exclusion", headers=HX, data={**form, "value": "no"})
    assert final.headers[HEADER] == "1"


def test_form_errors_and_empty_states_are_not_keepable(client):
    empty = client.post("/field/summary", headers=HX, data={"profile": ""})
    assert empty.status_code == 200 and HEADER not in empty.headers
    bad = client.post("/market/board", headers=HX, data={"profile": json.dumps(ready_profile()), "crop": "nope"})
    assert bad.status_code == 200 and HEADER not in bad.headers
    error = client.post("/schemes/answer/age", headers=HX, data={"answers": "{}", "profile": "", "value": "abc"})
    assert HEADER not in error.headers
