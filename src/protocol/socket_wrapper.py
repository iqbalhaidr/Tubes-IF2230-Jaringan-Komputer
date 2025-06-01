# File: src/protocol/socket_wrapper.py

import socket
import random
import time
import threading
from typing import Dict, Tuple, Optional
from .segment import Segment

class SelectiveRepeatWindow:
    """
    Implementasi Selective Repeat window untuk flow control sesuai spesifikasi TCP.
    """
    def __init__(self, window_size: int = 4):
        self.window_size = window_size
        self.base = 0                    # Sequence number terkecil yang belum di‐ACK
        self.next_seq_num = 0            # Sequence number berikutnya untuk dikirim
        self.buffer: Dict[int, Segment] = {}  # Buffer untuk segment yang belum di‐ACK
        self.acked: Dict[int, bool] = {}       # Track segment mana yang sudah di‐ACK
        self.lock = threading.Lock()

    def can_send(self) -> bool:
        """Cek apakah masih bisa mengirim segment baru dalam window"""
        with self.lock:
            return len(self.buffer) < self.window_size

    def add_segment(self, seq_num: int, segment: Segment):
        """Tambah segment ke buffer untuk tracking ACK"""
        with self.lock:
            is_first_segment_in_empty_window = not self.buffer
            self.buffer[seq_num] = segment
            self.acked[seq_num] = False
            if is_first_segment_in_empty_window:
                self.base = seq_num

    def mark_acked(self, seq_num: int) -> bool:
        """Mark segment sebagai ACK‐ed, return True jika window bergeser"""
        with self.lock:
            if seq_num in self.buffer and not self.acked.get(seq_num, False):
                self.acked[seq_num] = True

                # Geser window base jika segment di base sudah di‐ACK
                window_moved = False
                original_base = self.base

                while self.base in self.acked and self.acked[self.base]:
                    if self.base in self.buffer: # Seharusnya selalu ada jika belum digeser
                        del self.buffer[self.base]


                    window_moved = True
                    if not self.buffer:
                        self.base = self.next_seq_num
                        break 
                    else:
                        self.base = min(self.buffer.keys())
                
                return window_moved
            return False 

    def get_unacked_segments(self) -> Dict[int, Segment]:
        """Dapatkan segment yang belum di‐ACK untuk retransmission"""
        with self.lock:
            return {seq: seg for seq, seg in self.buffer.items() 
                   if not self.acked.get(seq, False)}


class BetterUDPSocket:
    def __init__(self, udp_socket: socket.socket = None, mtu: int = 128):
        self.udp_socket = udp_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Pastikan blocking (karena kita akan menggunakan timeout secara eksplisit)
        self.udp_socket.setblocking(True)
        self.mtu = mtu
        self.peer_addr = None
        self.connected = False

        # Sequence tracking sesuai spesifikasi TCP
        self.seq = 0  # Current sequence number
        self.ack = 0  # Current acknowledgment number

        # Flow control variables
        self.send_window = SelectiveRepeatWindow(window_size=4)
        self.recv_buffer: Dict[int, bytes] = {}  # Buffer untuk out‐of‐order segments
        self.expected_seq = 0  # Sequence number yang diharapkan berikutnya

        # Timing untuk retransmission
        self.rtt_estimate = 1.0
        self.timeout = 4.0  # Diperbesar agar server punya cukup waktu untuk ACK
        self.segment_timers: Dict[int, float] = {}

        # Thread management
        self.retransmit_thread = None
        self.running = False

    @property
    def window_size(self) -> int:
        """Dapatkan ukuran window saat ini"""
        return self.send_window.window_size

    def _start_retransmit_timer(self):
        """Start background thread untuk automatic retransmission"""
        if self.retransmit_thread is None or not self.retransmit_thread.is_alive():
            self.running = True
            self.retransmit_thread = threading.Thread(
                target=self._retransmit_worker,
                daemon=True
            )
            self.retransmit_thread.start()

    def _retransmit_worker(self):
        """Background worker untuk automatic retransmission"""
        while self.running and self.connected:
            current_time = time.time()
            unacked = self.send_window.get_unacked_segments()

            for seq_num, segment in unacked.items():
                if seq_num in self.segment_timers:
                    if current_time - self.segment_timers[seq_num] > self.timeout:
                        try:
                            self.udp_socket.sendto(segment.to_bytes(), self.peer_addr)
                            self.segment_timers[seq_num] = current_time
                            print(f"[RETRANSMIT] Seq {seq_num}")
                        except Exception as e:
                            print(f"[ERROR] Retransmit failed: {e}")
            time.sleep(0.1)

    def send(self, data: bytes):
        """
        Kirim data dengan flow control Selective Repeat.
        Data dibagi menjadi segment dengan payload ≤ 64 bytes.
        """
        if not self.connected:
            raise RuntimeError("Socket not connected")
        
        self._start_retransmit_timer()
        

        # Spesifikasi: maksimal 64 byte untuk payload
        max_payload_size = min(64, self.mtu - Segment.HEADER_SIZE)
        if max_payload_size <= 0:
            raise ValueError("Header terlalu besar, tidak ada ruang untuk payload")

        # Bagi data menjadi chunks ≤ 64 byte
        chunks = [data[i:i + max_payload_size] for i in range(0, len(data), max_payload_size)]

        sent_first = False
        for chunk in chunks:
            # Tunggu sampai window ada slot kosong
            while not self.send_window.can_send():
                self._process_incoming_acks(timeout=0.01)
                time.sleep(0.001)

            seq_num = self.seq
            segment = Segment(
                src_port=self.udp_socket.getsockname()[1],
                dst_port=self.peer_addr[1],
                seq_num=seq_num,
                ack_num=self.ack,
                flags=0x10, 
                payload=chunk
            )

            # Simpan di window dan kirim
            self.send_window.add_segment(seq_num, segment)
            self.udp_socket.sendto(segment.to_bytes(), self.peer_addr)
            self.segment_timers[seq_num] = time.time()

            # Start retransmit timer hanya sekali setelah segmen pertama terkirim
            if not sent_first:
                self._start_retransmit_timer()
                sent_first = True

            # Update sequence number sesuai ukuran data
            self.seq += len(chunk)
            with self.send_window.lock:
                self.send_window.next_seq_num = seq_num + 1

            print(f"[SEND] Seq {seq_num}, Payload: {len(chunk)} bytes")

        # Tunggu sampai semua segment di‐ACK
        while self.send_window.get_unacked_segments():
            self._process_incoming_acks(timeout=0.1)
        time.sleep(1)
    
    def _process_incoming_acks(self, timeout: float = 0.1):
        """Proses ACK yang masuk dari peer"""
        try:
            self.udp_socket.settimeout(timeout)
            raw, addr = self.udp_socket.recvfrom(self.mtu)
            if addr != self.peer_addr:
                return

            segment = Segment.from_bytes(raw)

            # Jika ACK flag ter‐set
            if segment.flags & 0x10:
                ack_num = segment.ack_num
                # Cari seq yang di‐ACK (ack_num – payload_size)
                for seq in list(self.send_window.buffer.keys()):
                    sent_segment = self.send_window.buffer[seq]
                    if ack_num == seq + len(sent_segment.payload):
                        if self.send_window.mark_acked(seq):
                            print(f"[ACK] Received ACK for seq {seq}, window moved")
                        else:
                            print(f"[ACK] Received ACK for seq {seq}")
                        break

            # Jika ada payload, forward ke handler
            if segment.payload:
                self._handle_data_segment(segment)

        except socket.timeout:
            pass
        except Exception as e:
            print(f"[ERROR] Processing ACK: {e}")

    def _handle_data_segment(self, segment: Segment):
        """Handle segment data yang diterima sesuai spesifikasi TCP"""
        seq_num = segment.seq_num
        payload_len = len(segment.payload)

        # Simpan data di buffer
        self.recv_buffer[seq_num] = segment.payload

        # Kirim ACK (seq saat ini, ack = seq_num + payload_len)
        ack_segment = Segment(
            src_port=self.udp_socket.getsockname()[1],
            dst_port=self.peer_addr[1],
            seq_num=self.seq,
            ack_num=seq_num + payload_len,
            flags=0x10,
            payload=b''
        )
        try:
            self.udp_socket.sendto(ack_segment.to_bytes(), self.peer_addr)
            print(f"[ACK SENT] For seq {seq_num} -> ack {seq_num + payload_len}")
        except Exception as e:
            print(f"[ERROR] Sending ACK: {e}")

    def receive(self, timeout: float = None) -> bytes:
        """
        Terima data dari peer dengan Selective Repeat flow control.
        Mengembalikan byte yang sudah di‐urutkan secara in‐order.
        """
        if not self.connected:
            raise RuntimeError("Socket not connected")

        result = b''

        # Periksa buffer untuk data yang sudah bisa di‐deliver in‐order
        while self.expected_seq in self.recv_buffer:
            chunk = self.recv_buffer.pop(self.expected_seq)
            result += chunk
            self.expected_seq += len(chunk)

        if result:
            return result

        # Tunggu data baru
        try:
            if timeout is not None:
                self.udp_socket.settimeout(timeout)
            else:
                self.udp_socket.settimeout(1.0)

            raw, addr = self.udp_socket.recvfrom(self.mtu)
            if addr != self.peer_addr:
                return b''

            segment = Segment.from_bytes(raw)
            if segment.payload:
                self._handle_data_segment(segment)

                # Periksa lagi apakah ada data in‐order sekarang
                while self.expected_seq in self.recv_buffer:
                    chunk = self.recv_buffer.pop(self.expected_seq)
                    result += chunk
                    self.expected_seq += len(chunk)

            return result

        except socket.timeout:
            return b''
        except Exception as e:
            print(f"[ERROR] Receiving data: {e}")
            return b''

    def connect(self, ip_address: str, port: int, timeout: float = 5.0):
        """
        Inisiasi 3-way handshake sesuai spesifikasi TCP, dengan retransmit SYN.
        """
        # Pastikan socket sudah bind atau bind ephemeral kalau belum
        try:
            self.udp_socket.getsockname()
        except OSError:
            self.udp_socket.bind(('', 0))

        x = random.randrange(0, 2**32)
        self.seq = x
        server_addr = (ip_address, port)
        syn = Segment(
            src_port=self.udp_socket.getsockname()[1],
            dst_port=port,
            seq_num=self.seq,
            flags=0x02,  # SYN
            payload=b'',
        )

        interval = 0.5
        deadline = time.time() + timeout
        received_synack = False
        y = 0

        while time.time() < deadline:
            # Kirim (atau kirim ulang) SYN
            self.udp_socket.sendto(syn.to_bytes(), server_addr)
            print(f"[HANDSHAKE] Sent SYN (seq={self.seq}) to {server_addr}")

            # Tunggu interval kecil untuk cek SYN+ACK
            wait_until = time.time() + interval
            while time.time() < wait_until:
                try:
                    self.udp_socket.settimeout(wait_until - time.time())
                    raw, addr = self.udp_socket.recvfrom(self.mtu)
                    segment = Segment.from_bytes(raw)
                    # Cukup cek flag == SYN+ACK dan ack_num benar,
                    # tanpa memeriksa port asli lagi
                    if segment.flags == 0x12 and segment.ack_num == x + 1:
                        y = segment.seq_num
                        self.peer_addr = addr
                        received_synack = True
                        print(f"[HANDSHAKE] Received SYN+ACK from {addr}, server_seq={y}, ack={segment.ack_num}")
                        break
                except socket.timeout:
                    break
                except Exception:
                    continue

            if received_synack:
                break

        if not received_synack:
            raise TimeoutError("Handshake timeout: did not receive SYN+ACK")

        # Kirim final ACK
        self.seq += 1
        self.ack = y + 1
        ack_segment = Segment(
            src_port=self.udp_socket.getsockname()[1],
            dst_port=self.peer_addr[1],
            seq_num=self.seq,
            ack_num=self.ack,
            flags=0x10,  # ACK
            payload=b'',
        )
        self.udp_socket.sendto(ack_segment.to_bytes(), self.peer_addr)
        print(f"[HANDSHAKE] Sent final ACK (seq={self.seq}, ack={self.ack}) to {self.peer_addr}")

        self.connected = True
        self.expected_seq = y + 1
        self.send_window.next_seq_num = self.seq
        self.send_window.base = self.seq
        self.udp_socket.setblocking(True)
        print(f"[CONNECTED] Connected to {self.peer_addr}")

    def get_state(self):
        """
        Kembalikan objek BetterUDPSocket yang mewakili koneksi setelah connect().
        """
        return self

    def listen(self, ip: str, port: int):
        """
        Siapkan socket untuk menerima koneksi masuk.
        """
        self.udp_socket.bind((ip, port))
        print(f"[LISTEN] Listening on {ip}:{port}")

    # socket_wrapper.py - Critical fix for accept() method

    def accept(self, timeout: float = None):
        """
        Tunggu dan terima koneksi masuk dengan 3-way handshake, dengan retransmit SYN+ACK.
        """
        if timeout is not None:
            self.udp_socket.settimeout(timeout)
        else:
            self.udp_socket.setblocking(True)

        # 1. Tunggu SYN
        try:
            raw, addr = self.udp_socket.recvfrom(self.mtu)
        except socket.timeout:
            raise TimeoutError("Accept timed out waiting for SYN")

        syn = Segment.from_bytes(raw)
        if syn.flags != 0x02:
            raise ValueError("Expected SYN")

        x = syn.seq_num
        print(f"[HANDSHAKE] Received SYN from {addr} seq={x}")

        # 2. Siapkan ephemeral socket untuk SYN+ACK
        new_conn_socket_raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_ip = self.udp_socket.getsockname()[0]
        if listening_ip == '0.0.0.0':
            listening_ip = addr[0]
        new_conn_socket_raw.bind((listening_ip, 0))
        eph_port = new_conn_socket_raw.getsockname()[1]

        y = random.randrange(0, 2**32)
        
        # CRITICAL FIX: Create new socket for this client BEFORE sending SYN+ACK
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.bind(('', 0))  # Bind to new port
        new_port = client_socket.getsockname()[1]
        
        # Send SYN+ACK with the NEW port number
        synack = Segment(
            src_port=eph_port,
            dst_port=addr[1],
            seq_num=y,
            ack_num=x + 1,
            flags=0x12,  # SYN+ACK
            payload=b''
        )

        interval = 0.5
        deadline = time.time() + (timeout if timeout is not None else 5.0)
        received_final = False

        while time.time() < deadline:
            new_conn_socket_raw.sendto(synack.to_bytes(), addr)
            print(f"[HANDSHAKE] Sent SYN+ACK from {listening_ip}:{eph_port} seq={y} to {addr}")

            wait_until = time.time() + interval
            while time.time() < wait_until:
                try:
                    new_conn_socket_raw.settimeout(wait_until - time.time())
                    raw2, addr2 = new_conn_socket_raw.recvfrom(self.mtu)
                    fin_ack = Segment.from_bytes(raw2)
                    # Cukup cek flag==ACK dan ack_num benar, tanpa memeriksa port lagi
                    if fin_ack.flags == 0x10 and fin_ack.ack_num == y + 1:
                        received_final = True
                        print(f"[HANDSHAKE] Received final ACK from {addr} ack={fin_ack.ack_num}")
                        break
                except socket.timeout:
                    break
                except Exception:
                    continue

            if received_final:
                break

        if not received_final:
            new_conn_socket_raw.close()
            raise TimeoutError("Handshake timeout: did not receive final ACK")

        # 3. Setup koneksi
        conn = BetterUDPSocket(new_conn_socket_raw, mtu=self.mtu)
        conn.peer_addr = addr
        conn.connected = True
        conn.seq = y + 1
        conn.ack = x + 1
        conn.expected_seq = x + 1
        conn.udp_socket.setblocking(True)

        print(f"[CONNECTED] {addr} connected (server ephemeral port={eph_port})")
        return conn, addr

    def start_receiving_in_background(self, callback):
        """
        Jalankan thread yang terus memanggil receive(), dan setiap
        kali ada payload, panggil `callback(payload)`.
        """
        self._recv_bg_stop = False

        def _recv_loop():
            while not getattr(self, "_recv_bg_stop", False) and self.connected:
                data = self.receive(timeout=0.1)
                if data:
                    callback(data)

        self._recv_thread = threading.Thread(target=_recv_loop, daemon=True)
        self._recv_thread.start()

    def stop_receiving_in_background(self):
        """
        Stop thread receiving (jika sebelumnya sudah dipanggil start_receiving_in_background).
        """
        self._recv_bg_stop = True
        if hasattr(self, "_recv_thread"):
            self._recv_thread.join(timeout=0.5)

    def close(self):
        """
        Tutup koneksi dengan FIN-ACK handshake.
        """
        if self.connected:
            try:
                fin_segment = Segment(
                    src_port=self.udp_socket.getsockname()[1],
                    dst_port=self.peer_addr[1],
                    seq_num=self.seq,
                    ack_num=self.ack,
                    flags=0x01,  # FIN
                    payload=b''
                )
                self.udp_socket.sendto(fin_segment.to_bytes(), self.peer_addr)
                print("[CLOSE] Sent FIN")

                self.udp_socket.settimeout(2.0)
                raw, addr = self.udp_socket.recvfrom(self.mtu)
                response = Segment.from_bytes(raw)
                if response.flags & 0x11:  # FIN+ACK
                    print("[CLOSE] Received FIN+ACK, connection closed gracefully")
            except Exception as e:
                print(f"[CLOSE] Error during graceful close: {e}")

        self.running = False
        self.connected = False
        self.udp_socket.close()
        print("[CLOSE] Socket closed")
