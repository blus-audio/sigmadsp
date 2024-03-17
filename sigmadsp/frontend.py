"""This module is the frontend to the SigmaDSP backend service.

It can control the backend via the command line.
"""

from __future__ import annotations

import logging
from io import TextIOWrapper
from ipaddress import IPv4Address

import click
import grpc

from sigmadsp.generated.backend_service.control_pb2 import ControlParameterRequest
from sigmadsp.generated.backend_service.control_pb2 import ControlRequest
from sigmadsp.generated.backend_service.control_pb2 import ControlResponse
from sigmadsp.generated.backend_service.control_pb2_grpc import BackendStub


class Channel:
    """Opens a channel to and handles control of the backend."""

    stub = BackendStub

    def __init__(self, backend_address: IPv4Address, backend_port: int):
        """Initialize the channel.

        Args:
            backend_address (ip_address): The IP address of the backend.
            backend_port (int): The backend port.
        """
        self.address = f"{backend_address}:{backend_port}"

    def _emit(self, request: ControlRequest | ControlParameterRequest):
        """Emits a request towards the backend.

        During emission, the channel is opened.

        Args:
            request (ControlRequest | ControlParameterRequest): The request to emit.
        """
        with grpc.insecure_channel(self.address) as channel:
            stub = BackendStub(channel)
            response: ControlResponse | None = None

            if isinstance(request, ControlRequest):
                response = stub.control(request)

            elif isinstance(request, ControlParameterRequest):
                response = stub.control_parameter(request)

            if response is not None:
                logging.info(response and response.message)

    def read_register(self, address: int, length: int):
        """Read a DSP register.

        Args:
            address (int): The address to read from.
            length (int): The length of data to read in bytes.
        """
        request = ControlRequest()
        request.read_register.address = address
        request.read_register.length = length
        self._emit(request)

    def change_volume(self, volume: float, relative: bool):
        """Change the DSP volume by a certain amount.

        Args:
            volume (float): The volume change in dB.
            relative (bool): If True, performs a relative change. If False, sets the provided volume.
        """
        request = ControlParameterRequest()
        request.change_volume.name_tokens[:] = ["main"]
        request.change_volume.value = volume
        request.change_volume.relative = relative
        self._emit(request)

    def reset(self, hard: bool):
        """Reset the DSP.

        Args:
            hard (bool): If True, performs a hard reset. If False, performs a soft reset.
        """
        request = ControlRequest()

        if hard:
            request.hard_reset_dsp = True

        else:
            request.reset_dsp = True

        self._emit(request)

    def load_parameters(self, file: TextIOWrapper):
        """Load a parameter file to the backend.

        Args:
            file (TextIOWrapper): The file to load.
        """
        request = ControlRequest()
        request.load_parameters.content[:] = file.readlines()
        self._emit(request)


@click.group()
@click.pass_context
@click.option(
    "--port",
    default=50051,
    show_default=True,
    type=int,
    help="Set the port, on which the backend listens for requests.",
)
@click.option(
    "--ip",
    default=IPv4Address("127.0.0.1"),
    show_default=True,
    type=IPv4Address,
    help="Set the IP address, on which the backend listens for requests.",
)
def sigmadsp(ctx: click.Context, port: int, ip: IPv4Address):
    """Command-line tool for controlling the sigmadsp-backend."""
    logging.basicConfig(level=logging.DEBUG)
    ctx.obj = Channel(ip, port)


@sigmadsp.command(context_settings={"ignore_unknown_options": True})
@click.pass_obj
@click.argument("file", type=click.File("r"))
def load_parameters(channel: Channel, file: TextIOWrapper):
    """Load a parameter file."""
    channel.load_parameters(file)


@sigmadsp.command(context_settings={"ignore_unknown_options": True})
@click.pass_obj
@click.argument("volume", type=float)
def set_volume(channel: Channel, volume: float):
    """Sets the volume to a certain value in dB."""
    channel.change_volume(volume, False)


@sigmadsp.command(context_settings={"ignore_unknown_options": True})
@click.pass_obj
@click.argument("change", type=float)
def change_volume(channel: Channel, change: float):
    """Changes the volume by a certain amount in dB."""
    channel.change_volume(change, True)


@sigmadsp.command()
@click.pass_obj
@click.option("--hard", is_flag=True)
def reset(channel: Channel, hard: bool):
    """Resets the DSP."""
    channel.reset(hard)


@sigmadsp.command()
@click.pass_obj
@click.argument("address", type=int)
@click.argument("length", type=int)
def read_register(channel: Channel, address: int, length: int):
    """Reads a DSP register."""
    channel.read_register(address, length)


if __name__ == "__main__":
    sigmadsp()  # pylint: disable=no-value-for-parameter
