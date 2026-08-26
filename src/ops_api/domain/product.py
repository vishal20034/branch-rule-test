from dataclasses import dataclass
from .money import Money


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    unit_price: Money
    category: str = "general"
    active: bool = True

    def __post_init__(self):
        if not self.sku or not self.sku.strip():
            raise ValueError("sku is required")
        if not self.name or not self.name.strip():
            raise ValueError("name is required")
        if not isinstance(self.unit_price, Money):
            raise TypeError("unit_price must be Money")
