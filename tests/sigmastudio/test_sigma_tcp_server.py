import pickle
import threading
from multiprocessing import Queue
from typing import List

from sigmadsp.sigmastudio.adau14xx import Adau14xxHeaderGenerator
from sigmadsp.sigmastudio.common import CONNECTION_CLOSED, WriteRequest
from sigmadsp.sigmastudio.server import (
    SigmaStudioRawRequestHandler,
    SigmaStudioRequestHandler,
    SigmaStudioTcpServer,
)

IP = "localhost"
PORT = 8089


def server_worker(server: SigmaStudioTcpServer):
    with server:
        server.serve_forever()


def dump_sigma_studio(raw: bool, output_path: str = "") -> List[WriteRequest]:
    receive_queue = Queue()
    send_queue = Queue()

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

    return requests


# dump_sigma_studio(True, "sigma_studio_raw_dump.pkl")
# dump_sigma_studio(False, "sigma_studio_dump.pkl")
