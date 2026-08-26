from dataclasses import dataclass


@dataclass
class StockItem:
    sku: str
    quantity: int
    reserved: int = 0
    reorder_level: int = 5

    def __post_init__(self):
        if self.quantity < 0 or self.reserved < 0:
            raise ValueError("quantity/reserved cannot be negative")
        if self.reserved > self.quantity:
            raise ValueError("reserved cannot exceed quantity")

    @property
    def available(self) -> int:
        return self.quantity - self.reserved

    def needs_reorder(self) -> bool:
        return self.available <= self.reorder_level
