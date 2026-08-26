from decimal import Decimal
from ops_api.domain.money import Money
from ops_api.domain.product import Product
from ops_api.domain.order import Order
from ops_api.services.pricing import PricingService


def _order(qty, price="10.00"):
    p = Product("WID-1001", "Widget", Money(price))
    o = Order("O-1", "C-1")
    o.add_line(p, qty)
    return o


def test_no_discount_under_threshold():
    s = PricingService()
    assert s.discount(_order(2)) == Money(0)


def test_bulk_discount():
    s = PricingService()
    o = _order(10)
    assert s.discount(o) == Money("5.00")  # 5% of 100


def test_tax_on_discounted():
    s = PricingService(tax_rate=Decimal("0.10"))
    o = _order(10)  # subtotal 100, discount 5, taxable 95
    assert s.tax(o) == Money("9.50")


def test_tax_exempt():
    s = PricingService()
    assert s.tax(_order(2), tax_exempt=True) == Money(0)


def test_grand_total():
    s = PricingService(tax_rate=Decimal("0.00"), bulk_rate=Decimal("0.00"))
    assert s.grand_total(_order(3)) == Money("30.00")
