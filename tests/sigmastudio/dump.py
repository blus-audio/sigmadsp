"""Helper functionality for dumping data from SigmaStudio."""
import pickle
import threading
from multiprocessing import Queue
from typing import Type, Union

from sigmadsp.sigmastudio.adau14xx import Adau14xxHeaderGenerator
from sigmadsp.sigmastudio.common import CONNECTION_CLOSED
from sigmadsp.sigmastudio.server import (
    SigmaStudioRawRequestHandler,
    SigmaStudioRequestHandler,
    SigmaStudioTcpServer,
)

IP = "localhost"
PORT = 8089


def server_worker(server: SigmaStudioTcpServer):
    """A worker that is started as a thread, for running the SigmaStudio TCP server.

    Args:
        server (SigmaStudioTcpServer): The server to run.
    """
    with server:
        server.serve_forever()


def dump_sigma_studio(raw: bool, output_path: str = ""):
    """Dumps data that was received from SigmaStudio.

    Args:
        raw (bool): If True, dump the raw received data. If False, dump ``WriteRequest`` objects.
        output_path (str, optional): The path to store the dump to. Defaults to "".
    """
    receive_queue: Queue = Queue()
    send_queue: Queue = Queue()

    request_handler_type: Union[Type[SigmaStudioRawRequestHandler], Type[SigmaStudioRequestHandler]]
    if raw:
        request_handler_type = SigmaStudioRawRequestHandler

    else:
        request_handler_type = SigmaStudioRequestHandler

    server = SigmaStudioTcpServer(
        (IP, PORT), request_handler_type, Adau14xxHeaderGenerator(), send_queue, receive_queue
    )

    sigma_tcp_server_thread = threading.Thread(target=server_worker, args=(server,), daemon=True)
    sigma_tcp_server_thread.start()

    requests = []

    with server:
        while True:
            request = server.receive_queue.get()

            if request is CONNECTION_CLOSED:
                break

            requests.append(request)

    if output_path:
        with open(output_path, "wb") as dump:
            pickle.dump(requests, dump)

    server.shutdown()
    sigma_tcp_server_thread.join()


dump_sigma_studio(True, "sigma_studio_raw_dump.pkl")
dump_sigma_studio(False, "sigma_studio_dump.pkl")
