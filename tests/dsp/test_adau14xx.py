import math
from typing import Callable, Union

from hypothesis import given
from hypothesis.strategies import floats

from sigmadsp.dsp.adau14xx import Adau14xx
from sigmadsp.dsp.factory import VALID_ADAU14XX, dsp_factory
from sigmadsp.helper.conversion import db_to_linear, int32_to_bytes, linear_to_db
from tests.protocols.dummy import DummyProtocol

TEST_ADDRESS = 123
ABS_TOL = 0.1
REL_TOL = 1e-2


def round_value_db_dsp(value_db: float, float_to_frac_fn: Callable, frac_to_float_fn: Callable) -> Union[float, None]:
    """Round the test volume in dB to a DSP-representable value.

    Args:
        value_db (value): The value to round.
        float_to_frac_fn (Callable): The DSP-function to convert float to fractional integer.
        frac_to_float_fn (Callable): The DSP-function to convert fractional integer to float.
    """
    try:
        register_value = float_to_frac_fn(db_to_linear(value_db))
        rounded_value_db = linear_to_db(frac_to_float_fn(register_value))

        return rounded_value_db

    except (ValueError, OverflowError):
        return None


@given(floats(min_value=0, max_value=1), floats())
def test_adau14xx_adjust_volume(test_volume: float, volume_change_db: float):
    """Test the volume adjustment functionality.

    Args:
        test_volume (float): The original (linear) DSP volume.
        volume_change_db (float): The change in volume in dB.
    """
    dummy_protocol = DummyProtocol()
    test_volume_db = linear_to_db(test_volume)

    # Do not use safeload while testing. The dummy protocol does not support it.
    adau14xx: Adau14xx = dsp_factory(VALID_ADAU14XX[0])(False, dummy_protocol)

    dummy_protocol.write(TEST_ADDRESS, int32_to_bytes(adau14xx.float_to_frac(test_volume)))

    new_volume_db = adau14xx.adjust_volume(volume_change_db, TEST_ADDRESS)
    rounded_new_volume_db = round_value_db_dsp(
        test_volume_db + volume_change_db, adau14xx.float_to_frac, adau14xx.frac_to_float
    )

    if rounded_new_volume_db is None:
        return

    if rounded_new_volume_db <= 0:
        assert math.isclose(new_volume_db, rounded_new_volume_db, rel_tol=REL_TOL, abs_tol=ABS_TOL)

    else:
        assert math.isclose(new_volume_db, test_volume_db, rel_tol=REL_TOL, abs_tol=ABS_TOL)


@given(floats())
def test_adau14xx_set_volume(test_volume_db: float):
    """Test the volume set functionality.

    Args:
        test_volume_db (float): The target DSP volume.
    """
    dummy_protocol = DummyProtocol()

    # Do not use safeload while testing. The dummy protocol does not support it.
    adau14xx: Adau14xx = dsp_factory(VALID_ADAU14XX[0])(False, dummy_protocol)

    current_volume_db = round_value_db_dsp(test_volume_db, adau14xx.float_to_frac, adau14xx.frac_to_float)
    if current_volume_db is None:
        return

    new_volume_db = adau14xx.set_volume(current_volume_db, TEST_ADDRESS)

    assert new_volume_db <= 0

    if current_volume_db <= 0:
        assert math.isclose(new_volume_db, current_volume_db, rel_tol=REL_TOL, abs_tol=ABS_TOL)
