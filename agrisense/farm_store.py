"""Saved farms: guest profile <-> DB rows (ADR-003, spec 01 R6-R8)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import districts, farm_profile
from .farm_profile import SOIL_KEYS, plot
from .models import Event, Farm, LoginAttempt, Plot, SoilCard, User, utcnow

_SOIL_COLUMNS = {"n": "n_kg_ha", "p": "p_kg_ha", "k": "k_kg_ha", "ph": "ph", "oc": "oc_pct"}


def current_plot(session: Session, user: User) -> Plot | None:
    return session.scalar(
        select(Plot).join(Farm).where(Farm.user_id == user.id).order_by(Plot.id).limit(1)
    )


def save_profile(session: Session, user: User, profile: dict, *, source: str = "app") -> Plot | None:
    """Create or update the user's farm and plot from a profile. Doesn't commit.

    A changed soil card becomes the current one; the old one is kept. Tool
    results from the guest profile are imported as events.
    """
    farm_data, p = profile["farm"], plot(profile)
    if any(profile.get("prefs", {}).values()):
        user.prefs = dict(profile["prefs"])
    if not farm_data["district_code"]:
        return None
    existing = current_plot(session, user)
    if existing is None:
        farm = Farm(user_id=user.id)
        session.add(farm)
        row = Plot(farm=farm, area_ha=Decimal(p["area_ha"] or 0))
        session.add(row)
    else:
        row, farm = existing, existing.farm

    district = districts.get(farm_data["district_code"])
    farm.district_code = farm_data["district_code"]
    farm.state = district.state if district else None
    farm.lat = Decimal(str(farm_data["lat"])) if farm_data["lat"] is not None else None
    farm.lon = Decimal(str(farm_data["lon"])) if farm_data["lon"] is not None else None
    farm.location_source = farm_data["location_source"]

    if p["area_ha"]:
        row.area_ha = Decimal(p["area_ha"])
        row.area_input_value = Decimal(p["area"]["value"])
        row.area_input_unit = p["area"]["unit"]
    row.irrigation_source = p["irrigation_source"]
    session.flush()

    _update_soil(session, row, p)
    for tool, envelope in profile["last_results"].items():
        session.add(Event(
            plot_id=row.id, kind=f"{tool}.result", occurred_at=utcnow(),
            payload=envelope, payload_version=1, source=source,
        ))
    return row


def _update_soil(session: Session, row: Plot, p: dict) -> None:
    current = session.scalar(select(SoilCard).where(SoilCard.plot_id == row.id, SoilCard.is_current.is_(True)))
    wanted = {k: (Decimal(p["soil"][k]) if p["soil"][k] is not None else None) for k in SOIL_KEYS}
    sampled = date.fromisoformat(p["soil"]["sampled_on"]) if p["soil"]["sampled_on"] else None
    if all(v is None for v in wanted.values()):
        if current is not None:
            current.is_current = False
        return
    if current is not None:
        same = all(getattr(current, _SOIL_COLUMNS[k]) == wanted[k] for k in SOIL_KEYS)
        if same and current.sampled_on == sampled:
            return
        current.is_current = False
    session.add(SoilCard(
        plot_id=row.id, sampled_on=sampled, source="shc", is_current=True,
        **{_SOIL_COLUMNS[k]: v for k, v in wanted.items()},
    ))


def profile_for(session: Session, user: User) -> dict:
    """The saved farm in the guest-profile shape, for the browser's copy."""
    profile = farm_profile.empty()
    if user.prefs:
        profile["prefs"]["transport_rate"] = farm_profile.transport_rate(user.prefs.get("transport_rate"))
    row = current_plot(session, user)
    if row is None:
        return profile
    farm = row.farm
    profile["farm"].update(
        lat=float(farm.lat) if farm.lat is not None else None,
        lon=float(farm.lon) if farm.lon is not None else None,
        district_code=farm.district_code,
        location_source=farm.location_source,
    )
    p = plot(profile)
    if row.area_input_unit:
        p["area"] = {"value": farm_profile._dec(row.area_input_value), "unit": row.area_input_unit}
    p["area_ha"] = farm_profile._dec(row.area_ha) if row.area_ha else None
    p["irrigation_source"] = row.irrigation_source
    card = session.scalar(select(SoilCard).where(SoilCard.plot_id == row.id, SoilCard.is_current.is_(True)))
    if card is not None:
        for key in SOIL_KEYS:
            value = getattr(card, _SOIL_COLUMNS[key])
            p["soil"][key] = farm_profile._dec(value) if value is not None else None
        p["soil"]["sampled_on"] = card.sampled_on.isoformat() if card.sampled_on else None
    else:
        p["soil_skipped"] = True
    return profile


def delete_account(session: Session, user: User) -> None:
    """Remove the user and everything they saved (DPDP erasure). Commits."""
    plot_ids = [pid for (pid,) in session.execute(
        select(Plot.id).join(Farm).where(Farm.user_id == user.id)
    )]
    farm_ids = [fid for (fid,) in session.execute(select(Farm.id).where(Farm.user_id == user.id))]
    if plot_ids:
        session.execute(delete(Event).where(Event.plot_id.in_(plot_ids)))
        session.execute(delete(SoilCard).where(SoilCard.plot_id.in_(plot_ids)))
        session.execute(delete(Plot).where(Plot.id.in_(plot_ids)))
    if farm_ids:
        session.execute(delete(Farm).where(Farm.id.in_(farm_ids)))
    session.execute(delete(LoginAttempt).where(LoginAttempt.phone_hmac == user.phone_hmac))
    # Helpers who reset this user's PIN keep their own rows; just unlink.
    for helped in session.scalars(select(User).where(User.pin_reset_by_id == user.id)):
        helped.pin_reset_by_id = None
    session.delete(user)
    session.commit()
