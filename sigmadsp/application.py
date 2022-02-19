from communication.sigma_tcp_server import ThreadedSigmaTcpRequestHandler, ThreadedTCPServer, SigmaTCPServer
from hardware.spi import SpiHandler

import threading
import multiprocessing

def main():
    HOST = "0.0.0.0"
    PORT = 8087

    tcp_server = ThreadedTCPServer((HOST, PORT), ThreadedSigmaTcpRequestHandler)
    tcp_server.queue = multiprocessing.JoinableQueue()

    # Generate an SPI handler, along with its thread
    spi_handler = SpiHandler()

    with tcp_server:
        # Base server thread
        # This initial thread starts one more thread for each request.
        tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCPServerThread")
        tcp_server_thread.daemon = True
        tcp_server_thread.start()

        while True:
            # Wait for a request from the TCP server
            mode = SigmaTCPServer.read(tcp_server)

            if mode == "write":
                # Write request received

                # Get information about write request
                address, data = SigmaTCPServer.read(tcp_server)

                # Write data to DSP
                SpiHandler.write(spi_handler, address, data)

            elif mode == "read":
                # Read request received

                # Get information about read request
                address, length = SigmaTCPServer.read(tcp_server)

                # Extract data from DSP
                data = SpiHandler.read(spi_handler, address, length)

                # Send read response
                SigmaTCPServer.write(tcp_server, data)

if __name__ == "__main__":
    main()