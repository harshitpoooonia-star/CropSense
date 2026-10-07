"""The spec's palette meets WCAG AA for every pair the macros use."""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parent.parent / "agrisense" / "static" / "src" / "app.css").read_text(encoding="utf-8")
TOKENS = dict(re.findall(r"--color-([\w-]+):\s*(#[0-9a-fA-F]{6})", CSS))


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(TOKENS[a]), luminance(TOKENS[b])), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


TEXT_PAIRS = [  # (foreground, background): 4.5:1 for body text
    ("ink", "bg"), ("ink", "surface"), ("ink", "surface-2"),
    ("ink-muted", "bg"), ("ink-muted", "surface"), ("ink-muted", "surface-2"),
    ("accent", "bg"), ("accent", "surface"), ("white", "accent"), ("white", "accent-strong"),
    ("white", "soil"), ("soil", "white"), ("accent", "accent-soft"),
    ("good", "good-bg"), ("warn", "warn-bg"), ("crit", "crit-bg"), ("crit", "surface"),
]
UI_PAIRS = [  # input borders and focus ring: 3:1
    ("line", "surface"), ("line", "bg"), ("accent", "bg"),
]


@pytest.mark.parametrize("fg, bg", TEXT_PAIRS)
def test_text_contrast_meets_aa(fg, bg):
    assert contrast(fg, bg) >= 4.5


@pytest.mark.parametrize("fg, bg", UI_PAIRS)
def test_ui_contrast_meets_aa(fg, bg):
    assert contrast(fg, bg) >= 3


def test_one_green_accent_and_no_default_palette():
    assert "--color-*: initial" in CSS
    assert not any(name.startswith(("blue", "red", "green-", "slate", "gray")) for name in TOKENS)
