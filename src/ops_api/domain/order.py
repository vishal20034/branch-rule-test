from dataclasses import dataclass, field
from enum import Enum
from typing import List
from .money import Money
from .product import Product


class OrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"


@dataclass
class OrderLine:
    product: Product
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

    @property
    def line_total(self) -> Money:
        return self.product.unit_price * self.quantity


@dataclass
class Order:
    order_id: str
    customer_id: str
    lines: List[OrderLine] = field(default_factory=list)
    status: OrderStatus = OrderStatus.DRAFT

    def add_line(self, product: Product, quantity: int) -> None:
        if self.status != OrderStatus.DRAFT:
            raise ValueError("can only add lines to a draft order")
        self.lines.append(OrderLine(product, quantity))

    @property
    def subtotal(self) -> Money:
        if not self.lines:
            return Money(0)
        total = Money(0)
        for line in self.lines:
            total = total + line.line_total
        return total

    @property
    def item_count(self) -> int:
        return sum(l.quantity for l in self.lines)
