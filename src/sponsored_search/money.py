from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self

CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    @classmethod
    def of(cls, value: str | int | float | Decimal) -> Self:
        return cls(Decimal(str(value)).quantize(CENTS))

    def __lt__(self, other: Money) -> bool:
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        return self.amount >= other.amount

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        return Money(self.amount - other.amount)

    def __mul__(self, factor: Decimal) -> Money:
        return Money(self.amount * factor)

    def __truediv__(self, divisor: Decimal) -> Money:
        return Money((self.amount / divisor).quantize(CENTS, rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"{self.amount:.2f}"


ZERO = Money.of(0)
CENT = Money(CENTS)
