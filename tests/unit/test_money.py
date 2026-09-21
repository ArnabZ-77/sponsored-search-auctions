from decimal import Decimal

import pytest

from sponsored_search import ZERO, Money


def test_of_normalises_any_input_to_cents():
    assert Money.of("0.3") == Money.of(0.30) == Money(Decimal("0.30"))
    assert str(Money.of(5)) == "5.00"


def test_addition_and_subtraction():
    assert Money.of("1.25") + Money.of("0.75") == Money.of(2)
    assert Money.of(1) - Money.of("0.40") == Money.of("0.60")


def test_multiplying_by_a_weight_is_exact():
    assert Money.of("0.10") * Decimal(3) == Money.of("0.30")
    assert (Money.of(1) * Decimal("0.333")).amount == Decimal("0.333")


@pytest.mark.parametrize(
    "amount, divisor, expected",
    [("1.00", 3, "0.33"), ("2.00", 3, "0.67"), ("0.05", 2, "0.03"), ("0.50", 2, "0.25")],
)
def test_dividing_by_a_weight_rounds_half_up_to_the_cent(amount, divisor, expected):
    assert Money.of(amount) / Decimal(divisor) == Money.of(expected)


def test_ordering():
    assert ZERO < Money.of("0.01") < Money.of(1)
    assert max(Money.of(2), Money.of(3)) == Money.of(3)
