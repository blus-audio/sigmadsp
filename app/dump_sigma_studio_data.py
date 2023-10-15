"""Helper functionality for dumping data from SigmaStudio."""
from __future__ import annotations

import datetime
import logging
import pickle
import signal
import sys
import threading
from multiprocessing import Queue
from pathlib import Path

from sigmadsp.sigmastudio.adau1x01 import Adau1x01HeaderGenerator
from sigmadsp.sigmastudio.common import CONNECTION_CLOSED
from sigmadsp.sigmastudio.common import ReadRequest
from sigmadsp.sigmastudio.common import ReadResponse
from sigmadsp.sigmastudio.common import WriteRequest
from sigmadsp.sigmastudio.header import PacketHeaderGenerator
from sigmadsp.sigmastudio.server import SigmaStudioRequestHandler
from sigmadsp.sigmastudio.server import SigmaStudioTcpServer

# from sigmadsp.sigmastudio.adau14xx import Adau14xxHeaderGenerator

signal.signal(signal.SIGINT, signal.default_int_handler)

IP = "0.0.0.0"
PORT = 8089


def server_worker(server: SigmaStudioTcpServer):
    """A worker that is started as a thread, for running the SigmaStudio TCP server.

    Args:
        server (SigmaStudioTcpServer): The server to run.
    """
    with server:
        server.serve_forever()


def dump_sigma_studio(output_path: Path, header_generator_type: type[PacketHeaderGenerator]):
    """Dumps data that was received from SigmaStudio.

    Args:
        output_path (Path, optional): The path to store the dump to. Defaults to "".
        header_generator_type (type[PacketHeaderGenerator]): The type of header generator to use.
    """
    receive_queue: Queue = Queue()
    raw_receive_queue: Queue = Queue()
    send_queue: Queue = Queue()

    server = SigmaStudioTcpServer(
        (IP, PORT),
        SigmaStudioRequestHandler,
        header_generator_type(),
        send_queue,
        receive_queue,
        raw_receive_queue=raw_receive_queue,
    )

    sigma_tcp_server_thread = threading.Thread(target=server_worker, args=(server,), daemon=True)
    sigma_tcp_server_thread.start()

    requests: list[ReadRequest | WriteRequest] = []
    raw_requests: list[bytes] = []

    with server:
        try:
            while True:
                request = server.receive_queue.get()

                if request is CONNECTION_CLOSED:
                    break

                if isinstance(request, ReadRequest):
                    response = ReadResponse(bytes(request.length))
                    server.send_queue.put(response)

                assert server.raw_receive_queue is not None, "Raw receive queue was not created."

                raw_requests.append(server.raw_receive_queue.get())
                requests.append(request)

        except KeyboardInterrupt:
            pass

    with output_path.open("wb") as dump:
        pickle.dump((raw_requests, requests), dump)

    sys.exit(0)


def main():
    """The dumping function.

    Run this, and use SigmaStudio functionalities:
    - Write to the DSP.
    - Read from the DSP.

    That data can be used for testing the backend.
    """
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Dumping data from SigmaStudio...")

    dump_sigma_studio(Path(f"sigma_studio_dump_{datetime.datetime.now().isoformat()}.pkl"), Adau1x01HeaderGenerator)


if __name__ == "__main__":
    main()
