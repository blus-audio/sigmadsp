from sigmadsp.communication.sigma_tcp_server import ThreadedSigmaTcpRequestHandler, ThreadedTCPServer, SigmaTCPServer
from sigmadsp.hardware.spi import SpiHandler

import threading
import multiprocessing

def main(HOST = "0.0.0.0", PORT = 8087):
    """Main application that runs a TCP server, for connecting to it with Sigma Studio,
    and an SPI handler, which communicates with the DSP.

    Args:
        HOST (str, optional): Listening address. Defaults to "0.0.0.0" (all addresses).
        PORT (int, optional): Listening port. Defaults to 8087.
    """
    # Generate TCP server
    tcp_server = ThreadedTCPServer((HOST, PORT), ThreadedSigmaTcpRequestHandler)
    tcp_server.queue = multiprocessing.JoinableQueue()
    
    # Generate an SPI handler, along with its thread
    spi_handler = SpiHandler()

    with tcp_server:
        # Base TCP server thread
        # This initial thread starts one more thread for each request.
        tcp_server_thread = threading.Thread(target=tcp_server.serve_forever, name="TCPServerThread")
        tcp_server_thread.daemon = True
        tcp_server_thread.start()

        sigma_tcp_server = SigmaTCPServer(tcp_server)

        while True:
            # Wait for a request from the TCP server
            mode = sigma_tcp_server.read()

            if mode == "write":
                # Write request received

                # Get information about write request
                address, data = sigma_tcp_server.read()

                # Write data to DSP
                spi_handler.write(address, data)

            elif mode == "read":
                # Read request received

                # Get information about read request
                address, length = sigma_tcp_server.read()

                # Extract data from DSP
                data = spi_handler.read(address, length)

                # Send read response
                sigma_tcp_server.write(data)

if __name__ == "__main__":
    main()