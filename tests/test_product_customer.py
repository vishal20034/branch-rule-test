import pytest
from ops_api.domain.money import Money
from ops_api.domain.product import Product
from ops_api.domain.customer import Customer


def test_product_ok():
    p = Product("WID-1001", "Widget", Money("9.99"))
    assert p.sku == "WID-1001"
    assert p.active is True


def test_product_requires_sku():
    with pytest.raises(ValueError):
        Product("  ", "n", Money(1))


def test_product_requires_name():
    with pytest.raises(ValueError):
        Product("WID-1001", "", Money(1))


def test_customer_ok():
    c = Customer("C-1", "a@x.com", "Ada")
    assert not c.tax_exempt


def test_customer_bad_email():
    with pytest.raises(ValueError):
        Customer("C-1", "not-an-email", "Ada")
