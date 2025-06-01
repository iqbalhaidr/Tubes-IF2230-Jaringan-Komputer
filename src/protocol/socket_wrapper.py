import socket
import random
import time
import threading
from typing import Dict, Optional, Tuple
from .segment import Segment

class SelectiveRepeatWindow:
    """
    Implementasi Selective Repeat window untuk flow control sesuai spesifikasi TCP
    """
    def __init__(self, window_size: int = 4):
        self.window_size = window_size
        self.base = 0  
        self.next_seq_num = 0  
        self.buffer: Dict[int, Segment] = {}
        self.acked: Dict[int, bool] = {}
        self.lock = threading.Lock()
        
    def can_send(self) -> bool:
        """Cek apakah masih bisa mengirim segment baru dalam window"""
        with self.lock:
            return self.next_seq_num < self.base + self.window_size

    def add_segment(self, seq_num: int, segment: Segment):
        """Tambah segment ke buffer untuk tracking ACK"""
        with self.lock:
            is_first_segment_in_empty_window = not self.buffer
            self.buffer[seq_num] = segment
            self.acked[seq_num] = False
            if is_first_segment_in_empty_window:
                self.base = seq_num

    def mark_acked(self, seq_num: int) -> bool:
        """Mark segment sebagai ACK-ed, return True jika window bergeser"""
        with self.lock:
            if seq_num in self.buffer and not self.acked.get(seq_num, False):
                self.acked[seq_num] = True
                
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
        """Dapatkan segment yang belum di-ACK untuk retransmission"""
        with self.lock:
            return {seq: seg for seq, seg in self.buffer.items() 
                   if not self.acked.get(seq, False)}

class BetterUDPSocket:
    def __init__(self, udp_socket: socket.socket = None, mtu: int = 128):
        self.udp_socket = udp_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setblocking(True)
        self.mtu = mtu
        self.peer_addr = None
        self.connected = False
        
        self.seq = 0
        self.ack = 0
        
        self.send_window = SelectiveRepeatWindow(window_size=4)
        self.recv_buffer: Dict[int, bytes] = {}
        self.expected_seq = 0
        
        # Timing untuk retransmission
        self.rtt_estimate = 1.0
        self.timeout = 2.0
        self.segment_timers: Dict[int, float] = {}
        
        self.retransmit_thread = None
        self.running = False
        
    def _start_retransmit_timer(self):
        """Start background thread untuk retransmission"""
        if self.retransmit_thread is None or not self.retransmit_thread.is_alive():
            self.running = True
            self.retransmit_thread = threading.Thread(target=self._retransmit_worker, daemon=True)
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
        Data dibagi menjadi segment dengan payload ≤ 64 bytes sesuai spesifikasi.
        """
        if not self.connected:
            raise RuntimeError("Socket not connected")
        
        self._start_retransmit_timer()
        
        max_payload_size = min(64, self.mtu - Segment.HEADER_SIZE)
        if max_payload_size <= 0:
            raise ValueError("Header terlalu besar, tidak ada ruang untuk payload")
        
        # Bagi data menjadi chunks ≤ 64 bytes
        chunks = []
        for i in range(0, len(data), max_payload_size):
            chunks.append(data[i:i + max_payload_size])
        
        for chunk in chunks:
            # Tunggu sampai window ada slot kosong
            while not self.send_window.can_send():
                self._process_incoming_acks(timeout=0.01)
                time.sleep(0.001)
            
            # Buat segment dengan sequence number sesuai spesifikasi TCP
            seq_num = self.seq
            segment = Segment(
                src_port=self.udp_socket.getsockname()[1],
                dst_port=self.peer_addr[1],
                seq_num=seq_num,
                ack_num=self.ack,
                flags=0x10, 
                payload=chunk
            )
            
            self.send_window.add_segment(seq_num, segment)
            self.udp_socket.sendto(segment.to_bytes(), self.peer_addr)
            self.segment_timers[seq_num] = time.time()
            
            self.seq += len(chunk)
            
            # Update window state
            with self.send_window.lock:
                self.send_window.next_seq_num = seq_num + 1
            
            print(f"[SEND] Seq {seq_num}, Payload: {len(chunk)} bytes")
        
        # Tunggu sampai semua segment di-ACK
        while self.send_window.get_unacked_segments():
            self._process_incoming_acks(timeout=0.1)
        time.sleep(1)
    
    def _process_incoming_acks(self, timeout: float = 0.1):
        """Process ACK yang masuk dari peer"""
        try:
            self.udp_socket.settimeout(timeout)
            raw, addr = self.udp_socket.recvfrom(self.mtu)
            
            if addr != self.peer_addr:
                return
            
            segment = Segment.from_bytes(raw)
            
            # Process ACK sesuai spesifikasi TCP
            if segment.flags & 0x10:  # ACK flag set
                ack_num = segment.ack_num
                # Cari sequence number yang di-ACK (ack_num - payload_size)
                for seq in list(self.send_window.buffer.keys()):
                    sent_segment = self.send_window.buffer[seq]
                    if ack_num == seq + len(sent_segment.payload):
                        if self.send_window.mark_acked(seq):
                            print(f"[ACK] Received ACK for seq {seq}, window moved")
                        else:
                            print(f"[ACK] Received ACK for seq {seq}")
                        break
            
            # Process data jika ada payload
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
        
        # Kirim ACK dengan ack_num = seq_num + payload_length (spesifikasi TCP)
        ack_segment = Segment(
            src_port=self.udp_socket.getsockname()[1],
            dst_port=self.peer_addr[1],
            seq_num=self.seq,
            ack_num=seq_num + payload_len,  # ACK number sesuai spesifikasi
            flags=0x10,  # ACK
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
        Mengembalikan data yang diterima sebagai bytes.
        """
        if not self.connected:
            raise RuntimeError("Socket not connected")
        
        result = b''
        
        # Cek buffer untuk data yang sudah bisa dikembalikan secara berurutan
        while self.expected_seq in self.recv_buffer:
            chunk = self.recv_buffer.pop(self.expected_seq)
            result += chunk
            self.expected_seq += len(chunk)  # Update sesuai ukuran data
        
        if result:
            return result
        
        # Tunggu data baru dari network
        try:
            if timeout is not None:
                self.udp_socket.settimeout(timeout)
            else:
                self.udp_socket.settimeout(1.0)
                
            raw, addr = self.udp_socket.recvfrom(self.mtu)
            
            if addr != self.peer_addr:
                return b''
            
            segment = Segment.from_bytes(raw)
            
            # Handle data segment
            if segment.payload:
                self._handle_data_segment(segment)
                
                # Cek lagi apakah sekarang ada data yang bisa dikembalikan
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
        Connect to server with proper port switching after handshake.
        """
        try:
            # Bind client to random port
            self.udp_socket.bind(('', 0))
            client_port = self.udp_socket.getsockname()[1]
            
            # Generate random ISN
            x = random.randrange(0, 2**32)
            
            # Send SYN to server's listener port
            syn = Segment(
                src_port=client_port,
                dst_port=port,
                seq_num=x,
                flags=0x02,  # SYN
                payload=b'',
            )
            self.udp_socket.sendto(syn.to_bytes(), (ip_address, port))
            print(f"[HANDSHAKE] Sent SYN with seq {x} to {ip_address}:{port}")
            
            # Wait for SYN+ACK (will come from server's NEW port)
            self.udp_socket.settimeout(timeout)
            raw, addr = self.udp_socket.recvfrom(self.mtu)
            segment = Segment.from_bytes(raw)
            
            if segment.flags != 0x12 or segment.ack_num != x + 1:
                raise ValueError("Invalid SYN+ACK response")
            
            y = segment.seq_num
            server_new_port = segment.src_port  # Server's new port for this connection
            server_new_addr = (ip_address, server_new_port)
            
            print(f"[HANDSHAKE] Received SYN+ACK with seq {y} from server's new port {server_new_port}")
            
            # Send final ACK to server's NEW port
            ack_segment = Segment(
                src_port=client_port,
                dst_port=server_new_port,  # Send to server's new port
                seq_num=x + 1,
                ack_num=y + 1,
                flags=0x10,  # ACK
                payload=b'',
            )
            self.udp_socket.sendto(ack_segment.to_bytes(), server_new_addr)
            print(f"[HANDSHAKE] Sent final ACK to server's new port {server_new_port}")
            
            # CRITICAL: Update peer address to server's NEW port
            self.peer_addr = server_new_addr  # Not the original listener port!
            self.connected = True
            self.seq = x + 1
            self.ack = y + 1
            self.expected_seq = y + 1
            
            # Reset window state
            self.send_window = SelectiveRepeatWindow(window_size=4)
            self.recv_buffer = {}
            
            print(f"[CONNECTED] Successfully connected to {server_new_addr}")
            
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            raise

    def listen(self, ip: str, port: int):
        """
        Siapkan socket untuk menerima koneksi masuk.
        """
        self.udp_socket.bind((ip, port))
        print(f"[LISTEN] Listening on {ip}:{port}")

    # socket_wrapper.py - Critical fix for accept() method

    def accept(self, timeout: float = None):
        """
        Accept incoming connection with proper socket isolation.
        The key fix: After handshake, client should communicate on a different socket.
        """
        if timeout is not None:
            self.udp_socket.settimeout(timeout)

        # 1. Wait for SYN
        raw, addr = self.udp_socket.recvfrom(self.mtu)
        syn = Segment.from_bytes(raw)
        if syn.flags != 0x02:
            raise ValueError("Expected SYN")

        x = syn.seq_num
        print(f"[HANDSHAKE] Received SYN from {addr} with seq {x}")

        # 2. Generate random sequence number and send SYN+ACK
        y = random.randrange(0, 2**32)
        
        # CRITICAL FIX: Create new socket for this client BEFORE sending SYN+ACK
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.bind(('', 0))  # Bind to new port
        new_port = client_socket.getsockname()[1]
        
        # Send SYN+ACK with the NEW port number
        synack = Segment(
            src_port=new_port,  # Use new port, not original listener port
            dst_port=addr[1],
            seq_num=y,
            ack_num=x + 1,
            flags=0x12,  # SYN+ACK
            payload=b''
        )
        
        # Send SYN+ACK from the NEW socket, not the listener socket
        client_socket.sendto(synack.to_bytes(), addr)
        print(f"[HANDSHAKE] Sent SYN+ACK with seq {y} from new port {new_port}")

        # 3. Wait for final ACK on the NEW socket
        client_socket.settimeout(timeout or 5.0)
        raw2, addr2 = client_socket.recvfrom(self.mtu)
        fin_ack = Segment.from_bytes(raw2)
        
        if addr2 != addr:
            raise ValueError(f"ACK from wrong address: expected {addr}, got {addr2}")
        if fin_ack.flags != 0x10 or fin_ack.ack_num != y + 1:
            raise ValueError("Expected final ACK")
        
        print(f"[HANDSHAKE] Received final ACK on new port {new_port}")

        # Create connection object with the NEW isolated socket
        conn = BetterUDPSocket(client_socket, mtu=self.mtu)
        conn.peer_addr = addr
        conn.connected = True
        conn.seq = y + 1
        conn.ack = x + 1
        conn.expected_seq = x + 1
        
        # Initialize fresh window state
        conn.send_window = SelectiveRepeatWindow(window_size=4)
        conn.recv_buffer = {}
        
        print(f"[CONNECTED] Client {addr} connected on isolated port {new_port}")
        return conn, addr

    def close(self):
        """
        Tutup koneksi dengan FIN-ACK handshake sesuai spesifikasi.
        """
        if self.connected:
            try:
                # Kirim FIN
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
                
                # Tunggu FIN+ACK (mutual FIN-ACK sesuai spesifikasi)
                self.udp_socket.settimeout(2.0)
                raw, addr = self.udp_socket.recvfrom(self.mtu)
                response = Segment.from_bytes(raw)
                
                if response.flags & 0x11:  # FIN+ACK
                    print("[CLOSE] Received FIN+ACK, connection closed gracefully")
                
            except Exception as e:
                print(f"[CLOSE] Error during graceful close: {e}")
        
        # Cleanup
        self.running = False
        self.connected = False
        self.udp_socket.close()
        print("[CLOSE] Socket closed")