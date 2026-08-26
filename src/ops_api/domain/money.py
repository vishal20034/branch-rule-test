from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP


class Money:
    """Immutable money value in a single currency (USD by default)."""

    def __init__(self, amount, currency: str = "USD"):
        if isinstance(amount, Money):
            self._amount = amount._amount
            self._currency = amount._currency
            return
        self._amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if self._amount < 0:
            raise ValueError("amount cannot be negative")
        if not currency or len(currency) != 3:
            raise ValueError("currency must be a 3-letter code")
        self._currency = currency.upper()

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    def _check(self, other: "Money"):
        if self.currency != other.currency:
            raise ValueError("currency mismatch")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("result cannot be negative")
        return Money(result, self.currency)

    def __mul__(self, factor) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and self.amount == other.amount and self.currency == other.currency

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"
