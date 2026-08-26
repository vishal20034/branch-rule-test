import pytest
from ops_api.domain.money import Money


def test_parses_string_and_rounds():
    assert Money("1.234").amount == Money("1.23").amount


def test_add_same_currency():
    assert Money(2) + Money(3) == Money(5)


def test_sub_same_currency():
    assert Money(5) - Money("1.50") == Money("3.50")


def test_mul():
    assert Money("10.00") * 3 == Money("30.00")


def test_reject_negative():
    with pytest.raises(ValueError):
        Money(-1)


def test_reject_currency_mismatch():
    with pytest.raises(ValueError):
        Money(1, "USD") + Money(1, "EUR")


def test_sub_cannot_go_negative():
    with pytest.raises(ValueError):
        Money(1) - Money(2)


def test_bad_currency():
    with pytest.raises(ValueError):
        Money(1, "US")
