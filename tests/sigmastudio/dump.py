"""Helper functionality for dumping data from SigmaStudio."""
import logging
import pickle
import threading
from multiprocessing import Queue
from pathlib import Path
from typing import List
from typing import Union

from sigmadsp.sigmastudio.adau14xx import Adau14xxHeaderGenerator
from sigmadsp.sigmastudio.common import CONNECTION_CLOSED
from sigmadsp.sigmastudio.common import ReadRequest
from sigmadsp.sigmastudio.common import ReadResponse
from sigmadsp.sigmastudio.common import WriteRequest
from sigmadsp.sigmastudio.server import SigmaStudioRequestHandler
from sigmadsp.sigmastudio.server import SigmaStudioTcpServer

IP = "localhost"
PORT = 8089


def server_worker(server: SigmaStudioTcpServer):
    """A worker that is started as a thread, for running the SigmaStudio TCP server.

    Args:
        server (SigmaStudioTcpServer): The server to run.
    """
    with server:
        server.serve_forever()


def dump_sigma_studio(output_path: Path):
    """Dumps data that was received from SigmaStudio.

    Args:
        output_path (str, optional): The path to store the dump to. Defaults to "".
    """
    receive_queue: Queue = Queue()
    raw_receive_queue: Queue = Queue()
    send_queue: Queue = Queue()

    server = SigmaStudioTcpServer(
        (IP, PORT),
        SigmaStudioRequestHandler,
        Adau14xxHeaderGenerator(),
        send_queue,
        receive_queue,
        raw_receive_queue=raw_receive_queue,
    )

    sigma_tcp_server_thread = threading.Thread(target=server_worker, args=(server,), daemon=True)
    sigma_tcp_server_thread.start()

    requests: List[Union[ReadRequest, WriteRequest]] = []
    raw_requests: List[bytes] = []

    with server:
        while True:
            request = server.receive_queue.get()

            if request is CONNECTION_CLOSED:
                break

            elif isinstance(request, ReadRequest):
                response = ReadResponse(bytes(request.length))
                server.send_queue.put(response)

            assert server.raw_receive_queue is not None, "Raw receive queue was not created."

            raw_requests.append(server.raw_receive_queue.get())
            requests.append(request)

    with open(output_path, "wb") as dump:
        pickle.dump((raw_requests, requests), dump)

    server.shutdown()
    sigma_tcp_server_thread.join()


def main():
    """The dumping function.

    Run this, and use SigmaStudio functionalities:
    - Write to the DSP.
    - Read from the DSP.

    That data can be used for testing the backend.
    """
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Dumping data from SigmaStudio...")

    dump_sigma_studio(Path("sigma_studio_dump.pkl"))


if __name__ == "__main__":
    main()
