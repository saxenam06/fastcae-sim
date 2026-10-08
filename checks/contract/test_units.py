"""Units: every quantity in a contract carries a unit from a fixed list (spec §5)."""

import math

import pytest

from zenryx.contract.units import Quantity, UnitError, Vector


def test_parse_and_convert_torque():
    q = Quantity.parse("366 N·m")
    assert q.to_canonical() == pytest.approx((366000.0, "N*mm"))


@pytest.mark.parametrize("text", ["366 Nm", "366 N*m", "366 N.m", "366 N m", "366 N⋅m"])
def test_aliases(text):
    value, unit = Quantity.parse(text).to_canonical()
    assert unit == "N*mm"
    assert value == pytest.approx(366000.0)


def test_micrometres_both_spellings():
    assert Quantity.parse("6 µm").to_canonical() == pytest.approx((0.006, "mm"))
    assert Quantity.parse("6 um").to_canonical() == pytest.approx((0.006, "mm"))
    # The Greek mu, which looks the same as the micro sign
    assert Quantity.parse("6 μm").to_canonical() == pytest.approx((0.006, "mm"))


def test_speed():
    value, unit = Quantity.parse("15000 rpm").to_canonical()
    assert unit == "rad/s"
    assert value == pytest.approx(15000 * 2 * math.pi / 60)


def test_angles():
    assert Quantity.parse("20 deg").to_canonical()[0] == pytest.approx(math.radians(20))
    assert Quantity.parse("0.5 mrad").to_canonical() == pytest.approx((5e-4, "rad"))


def test_a_value_without_a_unit_is_refused():
    with pytest.raises(UnitError, match="needs a unit"):
        Quantity.parse("20")


def test_unknown_unit_is_refused():
    with pytest.raises(UnitError, match="allowed units"):
        Quantity.parse("3 furlongs")
    with pytest.raises(ValueError, match="allowed units"):
        Quantity(value=3.0, unit="furlongs")


def test_density_and_modulus():
    assert Quantity.parse("2660 kg/m3").to_canonical() == pytest.approx((2.66e-9, "t/mm3"))
    assert Quantity.parse("2.66 g/cm³").to_canonical() == pytest.approx((2.66e-9, "t/mm3"))
    assert Quantity.parse("70.93 GPa").to_canonical() == pytest.approx((70930.0, "MPa"))


def test_thermal_expansion():
    assert Quantity.parse("23.1 µm/(m·K)").to_canonical() == pytest.approx((23.1e-6, "1/K"))
    assert Quantity.parse("23.1 um/(m.K)").to_canonical() == pytest.approx((23.1e-6, "1/K"))
    assert Quantity.parse("2.31e-5 1/K").to_canonical() == pytest.approx((2.31e-5, "1/K"))


def test_dimensionless_and_percent():
    assert Quantity(value=9.32, unit="1").to_canonical() == (9.32, "1")
    assert Quantity.parse("1 %").to_canonical() == pytest.approx((0.01, "1"))


def test_unit_spelling_is_normalised_on_construction():
    assert Quantity(value=366, unit="Nm").unit == "N·m"


def test_vector_converts_each_component():
    v = Vector(values=(1.0, 0.0, -2.5), unit="kN")
    assert v.to_canonical() == ((1000.0, 0.0, -2500.0), "N")


def test_vector_needs_three_components():
    with pytest.raises(ValueError):
        Vector(values=(1.0, 2.0), unit="mm")
