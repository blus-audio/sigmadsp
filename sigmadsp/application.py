from communication.tcp_server import ThreadedTCPServer, ThreadedSigmaTcpRequestHandler
from hardware.spi import SpiHandler

import threading
import multiprocessing

def main():
    HOST, PORT = "0.0.0.0", 8087

    # Generate an SPI handler, along with its thread
    spi_handler = SpiHandler()

    # Generate a TCP server, for handling requests from Sigma Studio
    tcp_server = ThreadedTCPServer((HOST, PORT), ThreadedSigmaTcpRequestHandler)
    tcp_server.queue = multiprocessing.JoinableQueue()

    with tcp_server:
        # Base sever thread
        # This initial thread starts one more thread for each request.
        tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCPServerThread")
        tcp_server_thread.daemon = True
        tcp_server_thread.start()

        while True:
            # Wait for a request from the TCP server
            mode = tcp_server.queue.get()
            tcp_server.queue.task_done()

            if mode == "write":
                # Write request received

                address, data = tcp_server.queue.get()
                tcp_server.queue.task_done()

                SpiHandler.write(spi_handler, address, data)

            elif mode == "read":
                # Read request received

                address, length = tcp_server.queue.get()
                tcp_server.queue.task_done()

                data = SpiHandler.read(spi_handler, address, length)
                
                tcp_server.queue.put(data)
                tcp_server.queue.join()

if __name__ == "__main__":
    main()