"""Entry point: `gunicorn wsgi:app` on Render, `flask --app wsgi run` locally."""

from agrisense import create_app

app = create_app()
