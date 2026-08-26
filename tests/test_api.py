import pytest
from ops_api.api.app import create_app, ApiError


@pytest.fixture
def api():
    return create_app()


def test_health(api):
    h = api.health()
    assert h["status"] == "ok"
    assert "started_at" in h


def test_place_order(api):
    result = api.place_order("O-100", "C-1", [("WID-1001", 2), ("CAB-3003", 1)])
    assert result["status"] == "confirmed"
    assert result["items"] == 3
    assert float(result["total"]) > 0


def test_tax_exempt_order(api):
    result = api.place_order("O-101", "C-2", [("WID-1001", 1)])
    assert result["total"] == "12.50"


def test_unknown_product(api):
    with pytest.raises(ApiError) as ei:
        api.place_order("O-102", "C-1", [("ZZZ-9999", 1)])
    assert ei.value.status == 400


def test_unknown_customer(api):
    with pytest.raises(ApiError):
        api.place_order("O-103", "NOPE", [("WID-1001", 1)])


def test_login_operator(api):
    token = api.auth.login("operator", "changeme1")
    assert api.auth.verify(token) == "operator"
