from typing import Dict
from ops_api.domain.order import Order, OrderStatus
from ops_api.domain.product import Product
from ops_api.domain.customer import Customer
from ops_api.services.inventory_service import InventoryService
from ops_api.services.pricing import PricingService


class OrderService:
    def __init__(self, inventory: InventoryService, pricing: PricingService | None = None):
        self.inventory = inventory
        self.pricing = pricing or PricingService()
        self._orders: Dict[str, Order] = {}
        self._customers: Dict[str, Customer] = {}
        self._products: Dict[str, Product] = {}

    def register_customer(self, customer: Customer) -> Customer:
        self._customers[customer.customer_id] = customer
        return customer

    def register_product(self, product: Product) -> Product:
        self._products[product.sku] = product
        return product

    def create_draft(self, order_id: str, customer_id: str) -> Order:
        if customer_id not in self._customers:
            raise KeyError("unknown customer")
        if order_id in self._orders:
            raise ValueError("order already exists")
        order = Order(order_id=order_id, customer_id=customer_id)
        self._orders[order_id] = order
        return order

    def add_item(self, order_id: str, sku: str, quantity: int) -> Order:
        order = self._get_draft(order_id)
        product = self._products.get(sku)
        if product is None or not product.active:
            raise KeyError("unknown or inactive product")
        self.inventory.reserve(sku, quantity)
        order.add_line(product, quantity)
        return order

    def confirm(self, order_id: str) -> Order:
        order = self._get_draft(order_id)
        if not order.lines:
            raise ValueError("cannot confirm an empty order")
        order.status = OrderStatus.CONFIRMED
        return order

    def ship(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError("unknown order")
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError("only confirmed orders can ship")
        for line in order.lines:
            self.inventory.ship(line.product.sku, line.quantity)
        order.status = OrderStatus.SHIPPED
        return order

    def cancel(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError("unknown order")
        if order.status == OrderStatus.SHIPPED:
            raise ValueError("cannot cancel a shipped order")
        if order.status != OrderStatus.CANCELLED:
            for line in order.lines:
                self.inventory.release(line.product.sku, line.quantity)
            order.status = OrderStatus.CANCELLED
        return order

    def total(self, order_id: str):
        order = self._orders[order_id]
        customer = self._customers[order.customer_id]
        return self.pricing.grand_total(order, tax_exempt=customer.tax_exempt)

    def _get_draft(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError("unknown order")
        if order.status != OrderStatus.DRAFT:
            raise ValueError("order is not a draft")
        return order
