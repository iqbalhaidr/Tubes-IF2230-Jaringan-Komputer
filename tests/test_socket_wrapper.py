import threading, unittest
from src.protocol.socket_wrapper import BetterUDPSocket

class TestHandshakeAndSend(unittest.TestCase):
    def test_handshake_and_echo(self):
        server = BetterUDPSocket()
        server.listen('127.0.0.1', 9000)

        def run_server():
            conn, addr = server.accept(timeout=2)
            # terima satu pesan lalu echo
            data = conn.receive(timeout=2)
            conn.send(data)

        t = threading.Thread(target=run_server, daemon=True)
        t.start()

        client = BetterUDPSocket()
        client.connect('127.0.0.1', 9000, timeout=2)
        self.assertTrue(client.connected)

        msg = b"hello world"
        client.send(msg)
        resp = client.receive(timeout=2)
        self.assertEqual(resp, msg)

if __name__ == "__main__":
    unittest.main()
