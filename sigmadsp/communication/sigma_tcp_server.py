"""This module communicates with SigmaStudio.

It can receive read/write requests and return with read response packets.
"""
import logging
import threading
from multiprocessing import Pipe

from sigmadsp.communication import tcpip1701, tcpipadau145x
from sigmadsp.communication.base import (
    ReadRequest,
    SafeloadRequest,
    ThreadedTCPServer,
    WriteRequest,
)

# A logger for this module
logger = logging.getLogger(__name__)


class SigmaStudioInterface:
    """This is an interface class for communicating with SigmaStudio.

    It creates a TCP server, which SigmaStudio talks to.
    """

    def __init__(self, host: str, port: int, dsp_type: str = "adau14xx"):
        """Initialize the SigmaStudio interface.

        Starts the main TCP worker and initializes a pipe for communicating with the sigmadsp backend.

        Args:
            host (str): Listening IP address
            port (int): Port to listen at
            dsp_type (str): DSP type, used to select the relevant protocol handler
        """
        self.host = host
        self.port = port
        self.dsp_type = dsp_type

        # Generate a Pipe for communicating with the TCP server worker thread within this class.
        self.pipe_end_owner, self.pipe_end_user = Pipe()

        tcp_server_worker_thread = threading.Thread(target=self.tcp_server_worker, name="TCP server worker thread")
        tcp_server_worker_thread.daemon = True
        tcp_server_worker_thread.start()

    def tcp_server_worker(self):
        """The main worker for the TCP server."""
        # default to ADAU145x
        protocol_handler: 
        
        if self.dsp_type == "adau145x":
            protocol_handler = tcpipadau145x.SigmaStudioRequestHandler

        elif self.dsp_type == "adau1701":
            protocol_handler = tcpip1701.SigmaStudioRequestHandler
        
        else:
            raise TypeError(f"The specified DSP type {self.dsp_type} is not supported.")

        tcp_server = ThreadedTCPServer((self.host, self.port), protocol_handler)

        with tcp_server:
            # Base TCP server thread
            # This initial thread starts one more thread for each request.
            tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCP server thread")
            tcp_server_thread.daemon = True
            tcp_server_thread.start()

            while True:
                # Wait for a request from the TCP server
                request = tcp_server.pipe_end_user.recv()

                if isinstance(request, WriteRequest):
                    # Write request received, don't do anything else
                    self.pipe_end_owner.send(request)

                elif isinstance(request, SafeloadRequest):
                    # Safeload request received, don't do anything else
                    self.pipe_end_owner.send(request)

                elif isinstance(request, ReadRequest):
                    # Read request received, wait for data to send to PC application
                    self.pipe_end_owner.send(request)

                    read_response = self.pipe_end_owner.recv()

                    # Send read response
                    tcp_server.pipe_end_user.send(read_response)
