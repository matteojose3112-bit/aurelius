from decimal import Decimal

import pytest

from app.domain.money import Money


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("12.345", "USD", "12.35"),
        ("12.344", "CAD", "12.34"),
        ("123.5", "JPY", "124"),
        ("1.2345", "KWD", "1.235"),
        ("-2.345", "COP", "-2.35"),
    ],
)
def test_currency_scale_and_half_up_rounding(amount, currency, expected):
    assert Money.from_decimal_string(amount, currency).to_decimal_string() == expected


def test_minor_units_are_exact_integers():
    assert Money.from_decimal_string("1234.56", "COP").minor_units == 123456
    assert Money.from_decimal_string("1234", "JPY").minor_units == 1234
    assert Money.from_decimal_string("1.234", "KWD").minor_units == 1234


def test_addition_and_subtraction_preserve_currency_and_precision():
    first = Money.from_decimal_string("10.10", "USD")
    second = Money.from_decimal_string("2.20", "USD")
    assert (first + second).to_decimal_string() == "12.30"
    assert (first - second).to_decimal_string() == "7.90"


def test_currency_codes_are_normalized():
    assert Money.from_decimal_string("10.00", "usd").currency == "USD"


@pytest.mark.parametrize("amount", [1.25, float("nan"), float("inf")])
def test_binary_floats_are_rejected(amount):
    with pytest.raises(TypeError):
        Money(amount, "USD")


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_decimal_values_are_rejected(amount):
    with pytest.raises(ValueError):
        Money.from_decimal_string(amount, "USD")


def test_unknown_currency_is_rejected_instead_of_assuming_two_decimals():
    with pytest.raises(ValueError, match="unsupported currency"):
        Money.from_decimal_string("1.00", "XYZ")


def test_cross_currency_arithmetic_requires_explicit_fx_conversion():
    usd = Money.from_decimal_string("10.00", "USD")
    cad = Money.from_decimal_string("10.00", "CAD")
    with pytest.raises(ValueError, match="different currencies"):
        _ = usd + cad


def test_api_constructor_requires_decimal_string():
    with pytest.raises(TypeError, match="decimal strings"):
        Money.from_decimal_string(12.34, "USD")
