import socket

import pytest

from agrisense import create_app
from agrisense.extensions import db as _db

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect


def _guarded_connect(sock, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in _LOCAL_HOSTS:
        raise RuntimeError(f"Network access blocked in tests (tried {host!r}); use a fixture.")
    return _real_connect(sock, address)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """ADR-004: tests never touch the internet. Local DBs/servers are allowed."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    return _db.session
