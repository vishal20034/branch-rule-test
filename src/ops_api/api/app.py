"""Minimal HTTP-style API facade (no web server required for unit tests)."""
from ops_api.domain.money import Money
from ops_api.domain.product import Product
from ops_api.domain.customer import Customer
from ops_api.services.inventory_service import InventoryService
from ops_api.services.order_service import OrderService
from ops_api.services.pricing import PricingService
from ops_api.services.auth import AuthService
from ops_api.utils.dates import utc_now_iso


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class OperationsAPI:
    def __init__(self):
        self.inventory = InventoryService()
        self.orders = OrderService(self.inventory, PricingService())
        self.auth = AuthService()
        self.started_at = utc_now_iso()

    def health(self) -> dict:
        return {"status": "ok", "started_at": self.started_at}

    def seed_demo(self) -> None:
        self.auth.register("operator", "changeme1")
        p1 = Product("WID-1001", "Widget", Money("12.50"), "hardware")
        p2 = Product("GAD-2002", "Gadget", Money("19.99"), "hardware")
        p3 = Product("CAB-3003", "Cable", Money("4.25"), "accessories")
        for p in (p1, p2, p3):
            self.orders.register_product(p)
            self.inventory.add_stock(p.sku, 100, reorder_level=10)
        self.orders.register_customer(Customer("C-1", "a@example.com", "Ada"))
        self.orders.register_customer(Customer("C-2", "b@example.com", "Bob", tax_exempt=True))

    def place_order(self, order_id: str, customer_id: str, items: list) -> dict:
        try:
            order = self.orders.create_draft(order_id, customer_id)
            for sku, qty in items:
                self.orders.add_item(order_id, sku, qty)
            self.orders.confirm(order_id)
            total = self.orders.total(order_id)
            return {
                "order_id": order.order_id,
                "status": order.status.value,
                "total": str(total.amount),
                "currency": total.currency,
                "items": order.item_count,
            }
        except (KeyError, ValueError) as exc:
            raise ApiError(400, str(exc)) from exc


def create_app() -> OperationsAPI:
    api = OperationsAPI()
    api.seed_demo()
    return api
