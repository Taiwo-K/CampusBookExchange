import bcrypt
import pytest

from app import create_app
from app.blueprints import auth as auth_bp

PASSWORD = "Tr1cky#Horse"
USER = {
    "id": 7,
    "password_hash": bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode(),
    "verified": True,
}


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True

    started = []
    monkeypatch.setattr(auth_bp, "start_session", lambda uid: started.append(uid))
    monkeypatch.setattr(auth_bp, "end_session", lambda: started.append("ended"))
    monkeypatch.setattr(auth_bp, "current_user", lambda: None)
    monkeypatch.setattr(
        auth_bp.db, "query_one",
        lambda sql, params=(): USER if params == ("test@my.unt.edu",) else None,
    )

    c = app.test_client()
    c.started = started
    return c


def login(client, email="test@my.unt.edu", password=PASSWORD, **extra):
    return client.post("/login", data={"email": email, "password": password, **extra})


def test_login_page_renders(client):
    assert client.get("/login").status_code == 200


def test_valid_login_starts_session(client):
    res = login(client)
    assert res.status_code == 302
    assert client.started == [7]


def test_email_is_trimmed_and_case_insensitive(client):
    assert login(client, email="  Test@My.UNT.edu ").status_code == 302


def test_wrong_password_rejected(client):
    res = login(client, password="Wr0ng#Password")
    assert res.status_code == 401
    assert b"Invalid email or password." in res.data
    assert client.started == []


def test_unknown_email_gives_same_error(client):
    res = login(client, email="nobody@my.unt.edu")
    assert res.status_code == 401
    assert b"Invalid email or password." in res.data
    assert client.started == []


@pytest.mark.parametrize("email, password", [("", PASSWORD), ("test@my.unt.edu", "")])
def test_blank_fields_rejected(client, email, password):
    assert login(client, email=email, password=password).status_code == 401


def test_redirects_to_safe_next(client):
    assert login(client, next="/listings").headers["Location"] == "/listings"


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_ignores_unsafe_next(client, target):
    assert login(client, next=target).headers["Location"] == "/login"


def test_logout_ends_session(client):
    res = client.post("/logout")
    assert res.status_code == 302
    assert client.started == ["ended"]
