import pytest
from ops_api.services.auth import AuthService


def test_register_and_login():
    a = AuthService()
    a.register("alice", "password1")
    token = a.login("alice", "password1")
    assert a.verify(token) == "alice"


def test_bad_password():
    a = AuthService()
    a.register("alice", "password1")
    with pytest.raises(ValueError):
        a.login("alice", "wrongpass")


def test_unknown_user():
    a = AuthService()
    with pytest.raises(ValueError):
        a.login("ghost", "password1")


def test_short_password():
    a = AuthService()
    with pytest.raises(ValueError):
        a.register("alice", "short")


def test_duplicate_user():
    a = AuthService()
    a.register("alice", "password1")
    with pytest.raises(ValueError):
        a.register("alice", "password1")


def test_invalid_token():
    a = AuthService()
    with pytest.raises(ValueError):
        a.verify("nope")
