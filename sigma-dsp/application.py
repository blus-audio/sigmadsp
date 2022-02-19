from communication.tcp_server import ThreadedTCPServer, ThreadedSigmaTcpRequestHandler
from hardware.spi import SpiHandler

import threading
import multiprocessing

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 8087

    spi_handler = SpiHandler()

    tcp_server = ThreadedTCPServer((HOST, PORT), ThreadedSigmaTcpRequestHandler)

    app_receive_tcp, tcp_send = multiprocessing.Pipe(duplex = False)
    tcp_receive, app_send_tcp = multiprocessing.Pipe(duplex = False)

    app_receive_spi, spi_send = multiprocessing.Pipe(duplex = False)
    spi_receive, app_send_spi = multiprocessing.Pipe(duplex = False)

    tcp_server.in_pipe = tcp_receive
    tcp_server.out_pipe = tcp_send

    spi_handler.in_pipe = spi_receive
    spi_handler.out_pipe = spi_send

    with tcp_server:
        # Base sever thread
        # This initial thread starts one more thread for each request.
        tcp_server_thread = threading.Thread(target=tcp_server.serve_forever)
        tcp_server_thread.daemon = True
        tcp_server_thread.start()

        spi_thread = threading.Thread(target=spi_handler.serve_forever)
        spi_thread.daemon = True
        spi_thread.start()

        while True:
            mode = app_receive_tcp.recv()

            if mode == "write":
                address, data = app_receive_tcp.recv()
                app_send_spi.send(mode)
                app_send_spi.send((address, data))

            elif mode == "read":
                address, length = app_receive_tcp.recv()

                app_send_spi.send(mode)
                app_send_spi.send((address, length))
                data = app_receive_spi.recv()
                
                app_send_tcp.send(data)

        input("Press any key to stop the Sigma TCP tcp_server.")
        
        tcp_server.shutdown()
        