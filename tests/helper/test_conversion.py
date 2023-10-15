"""Test conversion functions."""
import pytest

from sigmadsp.helper.conversion import clamp


@pytest.mark.parametrize(
    ("lower", "upper", "input_value", "expected"), [(-10, 20, 8, 8), (-5, 32, 34, 32), (-12, 0, -123, -12)]
)
def test_clamp(lower: float, upper: float, input_value: float, expected: float) -> None:
    """Test the clamping function.

    Args:
        lower (float): The lower limit for clamping.
        upper (float): The upper limit for clamping.
        input_value (float): The input value to clamp.
        expected (float): The expected (clamped) value.
    """
    assert expected == clamp(input_value, lower, upper)
