"""Every user-facing string goes through Flask-Babel (CLAUDE.md, spec P0-7).

The i18n-localization skill's checker doesn't read Jinja templates, so these
tests do: no raw words in templates, every extracted string translated into
Hindi with the same placeholders, and committed .mo files built from the .po.
"""

import io
import re
from pathlib import Path

import pytest
from babel.messages.extract import extract_from_dir
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "agrisense" / "templates"
TRANSLATIONS = ROOT / "agrisense" / "translations"

JINJA = re.compile(r"{#.*?#}|{%.*?%}|{{.*?}}", re.S)
HUMAN_ATTRS = re.compile(r'\b(?:aria-label|placeholder|title|alt)="([^"]*)"')
PLACEHOLDER = re.compile(r"%\((\w+)\)s")


def visible_words(source: str) -> list[str]:
    """Words a person would see that aren't inside a Jinja expression."""
    text = JINJA.sub(" ", source)
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    attr_text = " ".join(HUMAN_ATTRS.findall(text))
    text = re.sub(r"<[^>]*>", " ", text)
    tokens = (text + " " + attr_text).split()
    return [t for t in tokens if re.search(r"[^\W\d_]", t)]  # has a letter


@pytest.mark.parametrize("template", sorted(TEMPLATES.rglob("*.html")), ids=lambda p: str(p.relative_to(TEMPLATES)))
def test_no_raw_text_in_templates(template):
    words = visible_words(template.read_text(encoding="utf-8"))
    assert words == [], f"Wrap these in _(): {words}"


def test_checker_catches_raw_text():
    assert visible_words('<p>Hello {{ _("ok") }}</p><img alt="A photo">') == ["Hello", "A", "photo"]
    assert visible_words('<p>{{ _("ok") }} · 2.5 ₹</p>') == []


def _extracted_ids() -> set[str]:
    method_map = [("agrisense/**.py", "python"), ("agrisense/templates/**.html", "jinja2")]
    keywords = {"_": None, "gettext": None, "ngettext": (1, 2), "_l": None, "lazy_gettext": None}
    ids = set()
    for _filename, _lineno, message, _comments, _context in extract_from_dir(
        str(ROOT), method_map=method_map, keywords=keywords
    ):
        ids.add(message if isinstance(message, str) else message[0])
    return ids


def _catalog(locale: str):
    with (TRANSLATIONS / locale / "LC_MESSAGES" / "messages.po").open("rb") as f:
        return read_po(f, locale=locale)


def test_every_string_has_a_hindi_translation():
    hindi = {m.id: m.string for m in _catalog("hi") if m.id}
    missing = sorted(i for i in _extracted_ids() if not hindi.get(i))
    assert missing == [], "Run pybabel extract/update and translate: " + repr(missing)


def test_hindi_keeps_every_placeholder():
    for message in _catalog("hi"):
        if message.id:
            assert set(PLACEHOLDER.findall(message.id)) == set(PLACEHOLDER.findall(message.string)), message.id


def test_no_fuzzy_translations():
    catalog = _catalog("hi")
    assert not catalog.fuzzy
    assert [m.id for m in catalog if m.id and m.fuzzy] == []


@pytest.mark.parametrize("locale", ["hi", "en"])
def test_committed_mo_matches_po(locale):
    buffer = io.BytesIO()
    write_mo(buffer, _catalog(locale))
    committed = (TRANSLATIONS / locale / "LC_MESSAGES" / "messages.mo").read_bytes()
    assert buffer.getvalue() == committed, "Run: pybabel compile -d agrisense/translations"
