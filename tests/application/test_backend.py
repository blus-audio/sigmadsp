"""Tests for the backend service."""
import pickle
import time
from typing import List

from sigmadsp.backend import BackendService
from sigmadsp.helper.conversion import int32_to_bytes
from sigmadsp.helper.settings import SigmadspSettings
from sigmadsp.sigmastudio.common import WriteRequest
from tests.mock.sigma_studio import SigmaTcpClient
from tests.protocols.dummy import DummyProtocol


def test_backend_service():
    """Integration test for the SigmaDsp backend service."""
    settings = SigmadspSettings("tests/application/test_config.yaml")
    safety_hash_cell = settings.parameter_parser.safety_hash_cell

    backend = BackendService(settings)
    protocol: DummyProtocol = backend.dsp.dsp_protocol
    protocol.write(safety_hash_cell.parameter_address, int32_to_bytes(safety_hash_cell.parameter_value))

    with open("sigma_studio_raw_dump.pkl", "rb") as dump:
        raw_requests: List[bytes] = pickle.load(dump)

    with open("sigma_studio_dump.pkl", "rb") as dump:
        write_requests: List[WriteRequest] = pickle.load(dump)

    client = SigmaTcpClient(ip=settings.config["host"]["ip"], port=settings.config["host"]["port"])

    protocol.reset()

    for request in raw_requests:
        client.write(request)

    client.s.close()

    while len(protocol.write_requests) != len(write_requests):
        time.sleep(0.01)

    for write_request, original_write_request in zip(protocol.write_requests, write_requests):
        assert write_request == original_write_request

    backend.close()
