import re

SKU_RE = re.compile(r"^[A-Z]{3}-[0-9]{4}$")


def require_sku(sku: str) -> str:
    if not sku or not SKU_RE.match(sku):
        raise ValueError("sku must look like ABC-1234")
    return sku


def require_positive_int(value, name: str = "value") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value
