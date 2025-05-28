import socket, random, time
from .segment import Segment

class BetterUDPSocket:
	def __init__(self, udp_socket: socket.socket = None, mtu: int = 128):
		self.udp_socket = udp_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.udp_socket.setblocking(True)
		self.mtu = mtu
		self.peer_addr = None
		self.connected = False
		self.seq = 0
		self.ack = 0

	def send(self, data: bytes): 
		"""
        Kirim data ke peer yang sudah terhubung.
        Data dibagi menjadi segment ≤ 64 byte payload.
        """
		max_payload_size = self.mtu - Segment.HEADER_SIZE
		for i in range(0, len(data), max_payload_size):
			chunk = data[i:i + max_payload_size]
			segment = Segment(
                src_port = self.udp_socket.getsockname()[1],
                dst_port = self.peer_addr[1],
                seq_num = self.seq,
                ack_num = self.ack,
                flags = 0,
                payload = chunk
            )
		self.udp_socket.sendto(segment.to_bytes(), self.peer_addr)
		self.seq += len(chunk)
		
	def receive(self, timeout: float = None) -> bytes:
		"""
        Terima data dari peer.
        Mengembalikan data yang diterima sebagai bytes.
        """
		if timeout is not None:
			self.udp_socket.settimeout(timeout)
		try:
			raw, addr = self.udp_socket.recvfrom(self.mtu)
			if self.peer_addr is None:
				self.peer_addr = addr
				self.connected = True
			segment = Segment.from_bytes(raw)
			if segment.seq_num == self.ack:
				self.ack += len(segment.payload)
				return segment.payload
		except socket.timeout:
			return b''
		return b''
	def connect(self, ip_address: str, port: int, timeout: float = 1.0):
		"""
		Inisiasi 3-way handshake untuk menghubungkan ke peer.
		"""			
		self.udp_socket.bind(('', 0))
		x = random.randrange(0, 2**32)
		self.seq = x
		syn = Segment(
			src_port=self.udp_socket.getsockname()[1],
			dst_port=port,
			seq_num=self.seq,
			flags=0x02,  # SYN
			payload=b'',
        )
		self.udp_socket.sendto(syn.to_bytes(), (ip_address, port))
		self.udp_socket.settimeout(timeout) # Tunggu SYN+ACK
		start = time.time()
		while True:
			raw, addr = self.udp_socket.recvfrom(self.mtu)
			segment = Segment.from_bytes(raw)
			if segment.flags == 0x12 and segment.ack_num == x + 1: # SYN+ACK
				y = segment.seq_num
				break
			if time.time() - start > timeout:
				raise TimeoutError("Handshake timeout (SYN+ACK)")	

        # Kirim ACK
		self.ack = y + 1
		self.seq = x + 1
		ack_segment = Segment(
			src_port=self.udp_socket.getsockname()[1],
			dst_port=port,
			seq_num=self.seq,
			ack_num=self.ack,
			flags=0x10,  # ACK
			payload=b'',
        )
		self.udp_socket.sendto(ack_segment.to_bytes(), (ip_address, port))
		self.peer_addr = (ip_address, port)
		self.connected = True
		
	def listen(self, ip: str, port: int):
		"""
		Siapkan socket agar menerima koneksi masuk.
		"""
		self.udp_socket.bind((ip, port))
	
	def accept(self, timeout: float = None):
		"""
		Tunggu koneksi masuk (three-way handshake).
		Kembalikan objek BetterUDPSocket terhubung dan alamat client.
		"""
		if timeout is not None:
			self.udp_socket.settimeout(timeout)

		# 1. Tunggu SYN
		raw, addr = self.udp_socket.recvfrom(self.mtu)
		syn = Segment.from_bytes(raw)
		if syn.flags != 0x02:
			raise ValueError("Expected SYN")

		x = syn.seq_num
		# 2. Kirim SYN+ACK
		y = random.randrange(0, 2**32)
		synack = Segment(
			src_port=self.udp_socket.getsockname()[1],
			dst_port=addr[1],
			seq_num=y,
			ack_num=x + 1,
			flags=0x12,  # SYN+ACK
			payload=b''
		)
		self.udp_socket.sendto(synack.to_bytes(), addr)

		# 3. Tunggu ACK final
		raw2, addr2 = self.udp_socket.recvfrom(self.mtu)
		fin_ack = Segment.from_bytes(raw2)
		if fin_ack.flags != 0x10 or fin_ack.ack_num != y + 1:
			raise ValueError("Expected final ACK")

		# Siapkan socket baru untuk koneksi ini
		conn = BetterUDPSocket(self.udp_socket, mtu=self.mtu)
		conn.peer_addr = addr
		conn.seq = fin_ack.ack_num
		conn.ack = fin_ack.seq_num + len(fin_ack.payload)
		conn.connected = True
		return conn, addr
		
	def close(self):
		"""
        Tutup socket.
        """
		self.udp_socket.close()
		self.connected = False