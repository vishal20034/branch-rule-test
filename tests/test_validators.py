import pytest
from ops_api.utils.validators import require_sku, require_positive_int
from ops_api.utils.dates import utc_now_iso


def test_sku_ok():
    assert require_sku("ABC-1234") == "ABC-1234"


def test_sku_bad():
    with pytest.raises(ValueError):
        require_sku("abc123")


def test_positive_int():
    assert require_positive_int(3, "n") == 3


def test_positive_int_rejects_bool_and_zero():
    with pytest.raises(ValueError):
        require_positive_int(True, "n")
    with pytest.raises(ValueError):
        require_positive_int(0, "n")


def test_iso_timestamp_shape():
    ts = utc_now_iso()
    assert ts.endswith("Z")
    assert "T" in ts
