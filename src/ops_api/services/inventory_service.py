from typing import Dict
from ops_api.domain.inventory import StockItem
from ops_api.utils.validators import require_sku, require_positive_int


class InventoryService:
    def __init__(self):
        self._stock: Dict[str, StockItem] = {}

    def add_stock(self, sku: str, quantity: int, reorder_level: int = 5) -> StockItem:
        sku = require_sku(sku)
        require_positive_int(quantity, "quantity")
        if sku in self._stock:
            self._stock[sku].quantity += quantity
        else:
            self._stock[sku] = StockItem(sku=sku, quantity=quantity, reorder_level=reorder_level)
        return self._stock[sku]

    def get(self, sku: str) -> StockItem:
        sku = require_sku(sku)
        if sku not in self._stock:
            raise KeyError(f"unknown sku {sku}")
        return self._stock[sku]

    def reserve(self, sku: str, quantity: int) -> StockItem:
        item = self.get(sku)
        require_positive_int(quantity, "quantity")
        if item.available < quantity:
            raise ValueError("insufficient stock")
        item.reserved += quantity
        return item

    def release(self, sku: str, quantity: int) -> StockItem:
        item = self.get(sku)
        require_positive_int(quantity, "quantity")
        if item.reserved < quantity:
            raise ValueError("cannot release more than reserved")
        item.reserved -= quantity
        return item

    def ship(self, sku: str, quantity: int) -> StockItem:
        item = self.get(sku)
        require_positive_int(quantity, "quantity")
        if item.reserved < quantity:
            raise ValueError("ship quantity exceeds reserved")
        item.reserved -= quantity
        item.quantity -= quantity
        return item

    def low_stock(self):
        return [i for i in self._stock.values() if i.needs_reorder()]
