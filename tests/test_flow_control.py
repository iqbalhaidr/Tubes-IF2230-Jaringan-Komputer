# File: tests/test_flow_control.py

import unittest
import threading
import time

from protocol.socket_wrapper import BetterUDPSocket
from protocol.segment import Segment

class EchoServerSR:
    def __init__(self, host='127.0.0.1', port=12354):
        self.server_socket = BetterUDPSocket()
        self.server_socket.listen(host, port)
        self.received_chunks = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_and_receive, daemon=True)
        self._thread.start()

# In class EchoServerSR, method _accept_and_receive:
    def _accept_and_receive(self):
        conn = None # Initialize conn to None
        try:
            conn, addr = self.server_socket.accept(timeout=5.0)
            print(f"[SERVER] Accepted connection from {addr}") # Tambahkan log

            start = time.time()
            # Loop untuk menerima data sedikit lebih lama atau sampai stop event
            while (time.time() - start < 3.5) and not self._stop.is_set() and conn.connected: # Check conn.connected
                data = conn.receive(timeout=0.1) # Panggil receive pada objek koneksi
                if data:
                    print(f"[SERVER] Received data: {len(data)} bytes") # Tambahkan log
                    self.received_chunks.append(data)
                # else:
                # print("[SERVER] No data received in this interval")
        except TimeoutError:
            print("[SERVER] Accept timed out.")
            return # Exit if accept times out
        except Exception as e:
            print(f"[SERVER] Error in accept_and_receive: {e}")
        finally:
            if conn:
                print(f"[SERVER] Closing connection with {conn.peer_addr}")
                # Kirim FIN jika diperlukan sebelum menutup (opsional, tergantung implementasi close())
                # Bagian FIN opsional di EchoServerSR bisa dihapus jika close() milik BetterUDPSocket sudah handle
                conn.close() # Tutup socket koneksi client
            # self._stop.set() # Set stop event di sini jika thread hanya handle satu koneksi

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)
        try:
            self.server_socket.udp_socket.close()
        except Exception:
            pass


class TestSelectiveRepeatFlowControl(unittest.TestCase):
    def setUp(self):
        self.server = EchoServerSR(host='127.0.0.1', port=12354)
        time.sleep(0.1)

        self.client = BetterUDPSocket()
        self.client.connect('127.0.0.1', 12354)
        self.client_conn = self.client.get_state()

    def test_send_200_bytes_without_loss(self):
        # Tambahkan jeda kecil agar server sudah di loop receive()
        time.sleep(0.1)

        original_data = b'X' * 200
        self.client_conn.send(original_data)

        time.sleep(3.0)

        server_data = b''.join(self.server.received_chunks)
        self.assertEqual(server_data, original_data)

    def tearDown(self):
        try:
            self.server.stop()
        except Exception:
            pass
        try:
            self.client.close()
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main()
