import pytest
from ops_api.domain.money import Money
from ops_api.domain.product import Product
from ops_api.domain.customer import Customer
from ops_api.domain.order import OrderStatus
from ops_api.services.inventory_service import InventoryService
from ops_api.services.order_service import OrderService


@pytest.fixture
def svc():
    inv = InventoryService()
    inv.add_stock("WID-1001", 50)
    inv.add_stock("GAD-2002", 50)
    s = OrderService(inv)
    s.register_customer(Customer("C-1", "a@x.com", "Ada"))
    s.register_customer(Customer("C-2", "b@x.com", "Bob", tax_exempt=True))
    s.register_product(Product("WID-1001", "Widget", Money("10.00")))
    s.register_product(Product("GAD-2002", "Gadget", Money("20.00")))
    return s


def test_confirm_and_ship(svc):
    svc.create_draft("O-1", "C-1")
    svc.add_item("O-1", "WID-1001", 2)
    svc.confirm("O-1")
    shipped = svc.ship("O-1")
    assert shipped.status == OrderStatus.SHIPPED
    assert svc.inventory.get("WID-1001").quantity == 48


def test_cancel_releases_stock(svc):
    svc.create_draft("O-2", "C-1")
    svc.add_item("O-2", "WID-1001", 5)
    svc.cancel("O-2")
    assert svc.inventory.get("WID-1001").reserved == 0


def test_cannot_confirm_empty(svc):
    svc.create_draft("O-3", "C-1")
    with pytest.raises(ValueError):
        svc.confirm("O-3")


def test_cannot_ship_draft(svc):
    svc.create_draft("O-4", "C-1")
    with pytest.raises(ValueError):
        svc.ship("O-4")


def test_cannot_cancel_shipped(svc):
    svc.create_draft("O-5", "C-1")
    svc.add_item("O-5", "GAD-2002", 1)
    svc.confirm("O-5")
    svc.ship("O-5")
    with pytest.raises(ValueError):
        svc.cancel("O-5")


def test_unknown_customer(svc):
    with pytest.raises(KeyError):
        svc.create_draft("O-x", "NOPE")


def test_duplicate_order(svc):
    svc.create_draft("O-6", "C-1")
    with pytest.raises(ValueError):
        svc.create_draft("O-6", "C-1")


def test_tax_exempt_total(svc):
    svc.create_draft("O-7", "C-2")
    svc.add_item("O-7", "WID-1001", 1)
    total = svc.total("O-7")
    assert total == Money("10.00")
