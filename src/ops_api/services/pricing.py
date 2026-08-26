from decimal import Decimal
from ops_api.domain.money import Money
from ops_api.domain.order import Order


class PricingService:
    """Tax and discount rules."""

    def __init__(self, tax_rate: Decimal = Decimal("0.08"), bulk_threshold: int = 10, bulk_rate: Decimal = Decimal("0.05")):
        self.tax_rate = Decimal(tax_rate)
        self.bulk_threshold = bulk_threshold
        self.bulk_rate = Decimal(bulk_rate)

    def discount(self, order: Order) -> Money:
        if order.item_count >= self.bulk_threshold:
            return order.subtotal * self.bulk_rate
        return Money(0, order.subtotal.currency)

    def tax(self, order: Order, tax_exempt: bool = False) -> Money:
        if tax_exempt:
            return Money(0, order.subtotal.currency)
        taxable = order.subtotal - self.discount(order)
        return taxable * self.tax_rate

    def grand_total(self, order: Order, tax_exempt: bool = False) -> Money:
        return order.subtotal - self.discount(order) + self.tax(order, tax_exempt)
