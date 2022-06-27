from sigmadsp.sigmastudio.server import SigmaStudioTcpServer

IP = "localhost"
PORT = 8087


def test_sigma_studio_interface():
    interface = SigmaStudioTcpServer(
        IP,
        PORT,
        "dummy",
    )

    client = SigmaTcpClient(ip=IP, port=PORT)

    client.read_request()
