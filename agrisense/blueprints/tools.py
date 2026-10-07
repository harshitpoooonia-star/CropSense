"""Shared helper for the tool blueprints while they are placeholders."""

from flask import render_template


def placeholder(title: str, section: int):
    return render_template("tool_placeholder.html", title=title, section=section)
