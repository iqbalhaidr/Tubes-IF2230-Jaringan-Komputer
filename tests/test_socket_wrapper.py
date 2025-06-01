import threading
import unittest
from protocol.socket_wrapper import BetterUDPSocket

class TestHandshakeAndSend(unittest.TestCase):
    def setUp(self):
        self.server = BetterUDPSocket()
        self.server.listen('127.0.0.1', 12354)

        def run_server():
            conn, addr = self.server.accept(timeout=2)
            data = conn.receive(timeout=2)
            conn.send(data)

        self._t = threading.Thread(target=run_server, daemon=True)
        self._t.start()

    def tearDown(self):
        # Tutup server socket agar tidak muncul ResourceWarning
        try:
            self.server.close()
        except:
            pass

    def test_handshake_and_echo(self):
        client = BetterUDPSocket()
        client.connect('127.0.0.1', 12354, timeout=2)
        self.assertTrue(client.connected)

        msg = b"hello world"
        client.send(msg)
        resp = client.receive(timeout=2)
        self.assertEqual(resp, msg)

        # Jangan lupa menutup client juga
        client.close()


if __name__ == "__main__":
    unittest.main()
