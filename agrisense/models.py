"""Phase 1 schema from ADR-003: user -> farm -> plot (+ soil_card), an
append-only per-plot event log, and shared, non-personal caches.

All timestamps are UTC. SQLite hands them back without tzinfo; use `aware()`
before comparing a loaded value with `utcnow()`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(Timestamps, db.Model):
    # "user" is a reserved word in Postgres; ADR-003 calls this table `user`.
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # HMAC-SHA256(PHONE_PEPPER, E.164 number). The number itself is never stored.
    phone_hmac: Mapped[str] = mapped_column(String(64), unique=True)
    pin_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="farmer")  # farmer | helper
    locale: Mapped[str] = mapped_column(String(5), default="hi")
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(32))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Staff-assisted PIN reset: a helper confirms the farmer in person and gets
    # a one-time code; the farmer enters it with a new PIN before it expires.
    pin_reset_required: Mapped[bool] = mapped_column(Boolean, default=False)
    pin_reset_code_hash: Mapped[str | None] = mapped_column(String(255))
    pin_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pin_reset_by_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))

    farms: Mapped[list[Farm]] = relationship(back_populates="user")

    @property
    def is_helper(self) -> bool:
        return self.role == "helper"


class LoginAttempt(db.Model):
    """Failed and successful PIN/code attempts, for rate limiting. Pruned after 24 h."""

    __tablename__ = "login_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # login | register | pin_reset
    phone_hmac: Mapped[str | None] = mapped_column(String(64), index=True)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    success: Mapped[bool] = mapped_column(Boolean)


class Farm(Timestamps, db.Model):
    __tablename__ = "farm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(40))
    district_code: Mapped[str | None] = mapped_column(String(16))
    # The pin is personal data: never log it, never copy it into caches.
    lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    lon: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))

    user: Mapped[User] = relationship(back_populates="farms")
    plots: Mapped[list[Plot]] = relationship(back_populates="farm")


class Plot(Timestamps, db.Model):
    __tablename__ = "plot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farm.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(80))
    area_ha: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    area_input_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    area_input_unit: Mapped[str | None] = mapped_column(String(16))  # acre | bigha | hectare
    irrigation_source: Mapped[str | None] = mapped_column(String(16))
    current_crop: Mapped[str | None] = mapped_column(String(32))
    season: Mapped[str | None] = mapped_column(String(8))  # kharif | rabi | zaid
    sowing_date: Mapped[date | None] = mapped_column(Date)
    boundary_geojson: Mapped[dict | None] = mapped_column(JSON)  # Phase 2 field health

    farm: Mapped[Farm] = relationship(back_populates="plots")
    soil_cards: Mapped[list[SoilCard]] = relationship(back_populates="plot")
    events: Mapped[list[Event]] = relationship(back_populates="plot")


class SoilCard(Timestamps, db.Model):
    __tablename__ = "soil_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plot_id: Mapped[int] = mapped_column(ForeignKey("plot.id"), index=True)
    sampled_on: Mapped[date | None] = mapped_column(Date)
    n_kg_ha: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    p_kg_ha: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    k_kg_ha: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    ph: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    oc_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ec_ds_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    extra: Mapped[dict | None] = mapped_column(JSON)  # S, Zn, Fe ... as printed
    source: Mapped[str] = mapped_column(String(16))  # shc | lab | sensor_estimate
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    plot: Mapped[Plot] = relationship(back_populates="soil_cards")


class Event(db.Model):
    """Append-only log of everything that happens on a plot (ADR-003).

    `kind` + versioned JSON `payload`; tool results carry the trust envelope.
    New kinds need a payload validator, not a migration.
    """

    __tablename__ = "event"
    __table_args__ = (Index("ix_event_plot_kind_time", "plot_id", "kind", "occurred_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plot_id: Mapped[int] = mapped_column(ForeignKey("plot.id"))
    kind: Mapped[str] = mapped_column(String(40))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)
    payload_version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # app | user | sensor | import
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plot: Mapped[Plot] = relationship(back_populates="events")


class CachedPrice(db.Model):
    """Mandi prices as published (Rs per quintal). Shared; no personal data."""

    __tablename__ = "cached_price"
    __table_args__ = (
        UniqueConstraint(
            "source", "market", "commodity", "variety", "grade", "arrival_date",
            name="uq_cached_price_row",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(40))
    district: Mapped[str] = mapped_column(String(60))
    market: Mapped[str] = mapped_column(String(80))
    commodity: Mapped[str] = mapped_column(String(80))
    variety: Mapped[str] = mapped_column(String(80))
    grade: Mapped[str] = mapped_column(String(40))
    arrival_date: Mapped[date] = mapped_column(Date, index=True)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    modal_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CachedWeather(db.Model):
    """Forecast per 0.01-degree cell (~1 km), never per exact pin. Shared."""

    __tablename__ = "cached_weather"
    __table_args__ = (UniqueConstraint("source", "lat_r", "lon_r", name="uq_cached_weather_cell"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16))
    lat_r: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    lon_r: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)
