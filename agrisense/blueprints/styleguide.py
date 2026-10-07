"""Every UI macro in Hindi and English (Section 3). Off in production unless
STYLEGUIDE=1, because it shows sample data."""

from datetime import date

from flask import Blueprint, render_template
from flask_babel import force_locale
from flask_babel import gettext as _
from markupsafe import Markup

bp = Blueprint("styleguide", __name__)


def _sample_trust() -> dict:
    return {
        "reasons": [_("Sample reason: this is where the 2-3 factors behind an answer go."),
                    _("Sample reason: each one is a plain sentence.")],
        "sources": [{"name": "Agmarknet", "date": date(2026, 10, 6)},
                    {"name": _("your soil card"), "date": None}],
        "confidence": "medium",
        "estimated_fields": [_("soil nitrogen")],
    }


@bp.get("/styleguide")
def index():
    panels = []
    for code in ("hi", "en"):
        with force_locale(code):
            html = render_template("styleguide/_components.html", trust=_sample_trust(), locale_code=code)
        panels.append((code, Markup(html)))
    return render_template("styleguide/index.html", panels=panels)
