"""Exact, currency-aware money primitives for Aurelius.

Amounts are represented as Decimal values and never accept binary floats.
This module is deliberately independent of SQLAlchemy, FastAPI, and providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import ClassVar


_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Money:
    """An amount denominated in one explicitly supported ISO-style currency.

    Construction rounds to the currency's minor-unit scale using ROUND_HALF_UP.
    Cross-currency arithmetic is rejected; FX conversion belongs in a separate,
    evidence-bearing domain service.
    """

    amount: Decimal
    currency: str

    CURRENCY_EXPONENTS: ClassVar[dict[str, int]] = {
        "BHD": 3,
        "CAD": 2,
        "COP": 2,
        "EUR": 2,
        "GBP": 2,
        "JPY": 0,
        "KWD": 3,
        "USD": 2,
    }

    def __post_init__(self) -> None:
        currency = self.currency.upper() if isinstance(self.currency, str) else ""
        if not _CURRENCY_PATTERN.fullmatch(currency):
            raise ValueError("currency must be a three-letter uppercase currency code")
        if currency not in self.CURRENCY_EXPONENTS:
            raise ValueError(f"unsupported currency: {currency}")

        if isinstance(self.amount, bool) or isinstance(self.amount, float):
            raise TypeError("money amounts must be Decimal or decimal strings, never float")
        if isinstance(self.amount, str):
            try:
                amount = Decimal(self.amount)
            except InvalidOperation as exc:
                raise ValueError("amount must be a valid decimal string") from exc
        elif isinstance(self.amount, Decimal):
            amount = self.amount
        else:
            raise TypeError("money amounts must be Decimal or decimal strings")

        if not amount.is_finite():
            raise ValueError("money amount must be finite")

        exponent = self.CURRENCY_EXPONENTS[currency]
        quantum = Decimal(1).scaleb(-exponent)
        object.__setattr__(self, "amount", amount.quantize(quantum, rounding=ROUND_HALF_UP))
        object.__setattr__(self, "currency", currency)

    @classmethod
    def from_decimal_string(cls, amount: str, currency: str) -> "Money":
        """Create Money from an exact API/import decimal string."""
        if not isinstance(amount, str):
            raise TypeError("API money amounts must be decimal strings")
        return cls(amount=amount, currency=currency)

    @property
    def minor_units(self) -> int:
        """Return the exact integer number of minor units for this currency."""
        exponent = self.CURRENCY_EXPONENTS[self.currency]
        return int(self.amount.scaleb(exponent))

    def to_decimal_string(self) -> str:
        """Return a fixed-scale, JSON-safe decimal string."""
        exponent = self.CURRENCY_EXPONENTS[self.currency]
        return f"{self.amount:.{exponent}f}"

    def _require_same_currency(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError("money arithmetic requires another Money value")
        if self.currency != other.currency:
            raise ValueError("cannot combine different currencies without an explicit FX conversion")

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)
