"""This module is the frontend to the SigmaDSP backend service.

It can control the backend via the command line.
"""
import argparse
import logging

import grpc

from sigmadsp.generated.backend_service.control_pb2 import ControlRequest
from sigmadsp.generated.backend_service.control_pb2_grpc import BackendStub


def main():
    """The main frontend command-line application, which controls the SigmaDSP
    backend."""

    logging.basicConfig(level=logging.INFO)

    argument_parser = argparse.ArgumentParser()

    argument_parser.add_argument(
        "-p",
        "--port",
        required=False,
        type=int,
        help="Set the port, on which the backend listens for requests.",
    )

    argument_parser.add_argument(
        "-a",
        "--address",
        required=False,
        type=str,
        help="Set the IP address, on which the backend listens for requests.",
    )

    argument_parser.add_argument(
        "-av",
        "--adjust_volume",
        required=False,
        type=float,
        help="Adjust the volume by a certain value in dB (positive or negative).",
    )

    argument_parser.add_argument(
        "-sv",
        "--set_volume",
        required=False,
        type=float,
        help="Sets the volume to a certain value in dB (zero or lower).",
    )

    argument_parser.add_argument(
        "-r",
        "--reset",
        required=False,
        help="Soft-reset the DSP.",
        action="store_true",
    )

    argument_parser.add_argument(
        "-lp",
        "--load_parameters",
        required=False,
        help="Load new parameter file",
    )

    arguments = argument_parser.parse_args()

    backend_port = 50051
    backend_address = "localhost"

    if arguments.port is not None:
        backend_port = arguments.port

    if arguments.address is not None:
        backend_address = arguments.address

    control_request = ControlRequest()

    if arguments.adjust_volume is not None:
        control_request.change_volume.cell_name = "adjustable_volume_main"
        control_request.change_volume.value = arguments.adjust_volume
        control_request.change_volume.relative = True

    if arguments.set_volume is not None:
        control_request.change_volume.cell_name = "adjustable_volume_main"
        control_request.change_volume.value = arguments.set_volume
        control_request.change_volume.relative = False

    if arguments.load_parameters is not None:
        with open(
            arguments.load_parameters, "r", encoding="utf8"
        ) as parameter_file:
            control_request.load_parameters.content[
                :
            ] = parameter_file.readlines()

    if arguments.reset is True:
        control_request.reset_dsp = True

    with grpc.insecure_channel(f"{backend_address}:{backend_port}") as channel:
        stub = BackendStub(channel)
        response = stub.control(control_request)
        logging.info(response.message)


if __name__ == "__main__":
    main()
