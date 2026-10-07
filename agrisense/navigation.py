"""Bottom navigation: Today, Plan, Field, Market, More (spec sitemap)."""

from __future__ import annotations

from flask import request
from flask_babel import lazy_gettext as _l

# (tab id, endpoint, icon, label)
TABS = [
    ("today", "today.index", "today", _l("Today")),
    ("plan", "planner.index", "plan", _l("Plan")),
    ("field", "field.index", "field", _l("Field")),
    ("market", "market.index", "market", _l("Market")),
    ("more", "more.index", "more", _l("More")),
]

# Which tab is lit for each blueprint. The public home lights none.
TAB_FOR_BLUEPRINT = {
    "today": "today",
    "planner": "plan",
    "fertilizer": "plan",
    "field": "field",
    "weather": "field",
    "market": "market",
    "more": "more",
    "schemes": "more",
    "profile": "more",
}


def active_tab() -> str | None:
    return TAB_FOR_BLUEPRINT.get(request.blueprint or "")
