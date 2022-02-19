from communication.tcp_server import ThreadedTCPServer, ThreadedSigmaTcpRequestHandler
from hardware.spi import SpiHandler

import threading
import multiprocessing

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 8087

    spi_handler = SpiHandler()

    tcp_server = ThreadedTCPServer((HOST, PORT), ThreadedSigmaTcpRequestHandler)
    tcp_server.queue = multiprocessing.Queue()

    with tcp_server:
        # Base sever thread
        # This initial thread starts one more thread for each request.
        tcp_server_thread = threading.Thread(target=tcp_server.serve_forever)
        tcp_server_thread.daemon = True
        tcp_server_thread.start()

        while True:
            mode = tcp_server.queue.get()

            if mode == "write":
                address, data = tcp_server.queue.get()
                spi_handler.queue.put(mode)
                spi_handler.queue.put((address, data))
                spi_handler.queue.join()

            elif mode == "read":
                address, length = tcp_server.queue.get()

                spi_handler.queue.put(mode)
                spi_handler.queue.put((address, length))
                spi_handler.queue.join()

                data = spi_handler.queue.get()
                
                tcp_server.queue.put(data)
                tcp_server.queue.join()
