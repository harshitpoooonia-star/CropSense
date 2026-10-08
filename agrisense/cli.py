"""Admin commands: `flask --app wsgi agrisense <command>`."""

from __future__ import annotations

import click
from flask import Flask, current_app
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .auth import AuthSettings, normalize_phone, phone_hash, pin_problem
from .extensions import db
from .models import User, utcnow


def register_cli(app: Flask) -> None:
    @app.cli.group("agrisense")
    def agrisense() -> None:
        """AgriSense admin commands."""

    @agrisense.command("refresh-prices")
    @click.option("--days", default=3, show_default=True, help="How many past days to fetch.")
    def refresh_prices(days: int) -> None:
        """Fetch recent Agmarknet prices into the cache (needs DATA_GOV_IN_KEY)."""
        from .market import agmarknet

        report = agmarknet.refresh(db.session, current_app.config.get("DATA_GOV_IN_KEY"), days=days)
        if report.error == "no_key":
            raise click.ClickException("DATA_GOV_IN_KEY is not set.")
        click.echo(f"days {report.days}, rows seen {report.rows_seen}, stored {report.rows_stored}, "
                   f"failed days {len(report.failed_days)}" + (f", error: {report.error}" if report.error else ""))

    @agrisense.command("make-helper")
    def make_helper() -> None:
        """Give a KVK/FPO helper the role that can start PIN resets.

        Promotes an existing account, or creates one. Phone and PIN are
        prompted (never passed as arguments, so they stay out of shell history).
        """
        settings = AuthSettings.from_config(current_app.config)
        phone = normalize_phone(click.prompt("Helper's mobile number", hide_input=True))
        if phone is None:
            raise click.ClickException("Not a valid Indian mobile number.")
        phone_h = phone_hash(phone, settings.pepper)
        user = db.session.scalar(select(User).where(User.phone_hmac == phone_h))
        if user is None:
            pin = click.prompt("New 4-digit PIN", hide_input=True, confirmation_prompt=True)
            if pin_problem(pin):
                raise click.ClickException("PIN must be 4 digits and not 1111/1234-style.")
            user = User(
                phone_hmac=phone_h,
                pin_hash=generate_password_hash(pin),
                consent_at=utcnow(),
                consent_version="helper-cli",
            )
            db.session.add(user)
        user.role = "helper"
        db.session.commit()
        click.echo(f"Helper ready (account id {user.id}).")
