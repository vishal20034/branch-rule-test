import pytest
from ops_api.services.inventory_service import InventoryService


@pytest.fixture
def inv():
    s = InventoryService()
    s.add_stock("WID-1001", 10, reorder_level=3)
    return s


def test_add_and_available(inv):
    assert inv.get("WID-1001").available == 10


def test_add_increments(inv):
    inv.add_stock("WID-1001", 5)
    assert inv.get("WID-1001").quantity == 15


def test_reserve(inv):
    inv.reserve("WID-1001", 4)
    assert inv.get("WID-1001").available == 6


def test_reserve_insufficient(inv):
    with pytest.raises(ValueError):
        inv.reserve("WID-1001", 99)


def test_release(inv):
    inv.reserve("WID-1001", 4)
    inv.release("WID-1001", 2)
    assert inv.get("WID-1001").reserved == 2


def test_ship(inv):
    inv.reserve("WID-1001", 4)
    inv.ship("WID-1001", 4)
    assert inv.get("WID-1001").quantity == 6
    assert inv.get("WID-1001").reserved == 0


def test_unknown_sku(inv):
    with pytest.raises(KeyError):
        inv.get("ZZZ-0000")


def test_bad_sku_format(inv):
    with pytest.raises(ValueError):
        inv.add_stock("bad", 1)


def test_low_stock_flag(inv):
    inv.reserve("WID-1001", 8)
    lows = inv.low_stock()
    assert any(i.sku == "WID-1001" for i in lows)
