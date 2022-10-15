"""Tests for the backend service."""
import pickle
import time
import typing
from typing import Dict, List, Tuple, Union

from pytest import fixture

from sigmadsp.backend import BackendService
from sigmadsp.dsp.adau14xx import Adau14xx
from sigmadsp.dsp.common import Dsp
from sigmadsp.helper.conversion import int32_to_bytes
from sigmadsp.helper.settings import SigmadspSettings
from sigmadsp.sigmastudio.common import ReadRequest, WriteRequest
from tests.mock.dummy_protocol import DummyProtocol
from tests.mock.sigma_studio import SigmaTcpClient


def dsp_from_config(config: Dict) -> Dsp:
    """DSP factory, for testing purposes.

    Args:
        config (Dict): The config dictionary, unused.

    Returns:
        Dsp: The new DSP.
    """
    del config
    return Adau14xx(False, DummyProtocol(), [])


@fixture(name="settings")
def sigmadsp_settings():
    """Provides settings for integration tests."""
    return SigmadspSettings("tests/application/test_config.yaml")


def test_backend_service(settings: SigmadspSettings):
    """Integration test for the SigmaDsp backend service.

    This puts multiple write requests into the backend service, previously dumped from SigmaStudio.
    """
    assert settings.parameter_parser is not None, "Parameter parser does not exist."

    safety_hash_cell = settings.parameter_parser.safety_hash_cell

    assert safety_hash_cell is not None, "Safety hash cell not found."

    backend = BackendService(settings, dsp_from_config_fn=dsp_from_config)

    protocol: DummyProtocol = typing.cast(DummyProtocol, backend.dsp.dsp_protocol)
    protocol.write(safety_hash_cell.parameter_address, int32_to_bytes(safety_hash_cell.parameter_value))

    with open("sigma_studio_dump.pkl", "rb") as dump_file:
        dump: Tuple[List[bytes], List[Union[ReadRequest, WriteRequest]]] = pickle.load(dump_file)
        raw_requests, requests = dump

    client = SigmaTcpClient(ip=settings.config["host"]["ip"], port=settings.config["host"]["port"])

    protocol.reset()

    for raw_request in raw_requests:
        client.write(raw_request)

    while (len(protocol.write_requests) + len(protocol.read_requests)) != len(requests):
        time.sleep(0.01)

    for write_request, original_write_request in zip(protocol.write_requests, requests):
        assert write_request == original_write_request

    client.s.close()
    backend.close()
