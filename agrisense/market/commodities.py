"""Our crop codes <-> Agmarknet commodity names.

Agmarknet names vary ("Paddy(Dhan)(Common)", "Wheat Atta", "Mustard Oil"),
so match on keywords: (include any, exclude all).
"""

from __future__ import annotations

KEYWORDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "wheat": (("wheat",), ("atta", "flour")),
    "paddy": (("paddy",), ()),
    "mustard": (("mustard",), ("oil",)),
    "potato": (("potato",), ("sweet",)),
    "maize": (("maize",), ()),
    "barley": (("barley",), ()),
    "bajra": (("bajra", "pearl millet"), ()),
    "chickpea": (("bengal gram", "gram"), ("green gram", "black gram", "flour", "dal")),
    "blackgram": (("black gram", "urad"), ("dal",)),
    "mungbean": (("green gram", "moong"), ("dal",)),
    "pigeonpeas": (("arhar", "tur"), ("dal",)),
    "lentil": (("lentil", "masur", "masoor"), ("dal",)),
    "sugarcane": (("sugarcane",), ()),
}


def matches(crop: str, commodity: str) -> bool:
    include, exclude = KEYWORDS.get(crop, ((), ()))
    name = " ".join(str(commodity).lower().split())
    return any(k in name for k in include) and not any(k in name for k in exclude)


def crop_for(commodity: str) -> str | None:
    return next((crop for crop in KEYWORDS if matches(crop, commodity)), None)


def tradable() -> list[str]:
    return list(KEYWORDS)
