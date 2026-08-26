from dataclasses import dataclass


@dataclass(frozen=True)
class Customer:
    customer_id: str
    email: str
    name: str
    tax_exempt: bool = False

    def __post_init__(self):
        if not self.customer_id:
            raise ValueError("customer_id is required")
        if "@" not in self.email:
            raise ValueError("invalid email")
        if not self.name:
            raise ValueError("name is required")
