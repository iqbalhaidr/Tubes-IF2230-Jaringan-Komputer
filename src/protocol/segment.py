import struct
from .checksum import compute_checksum, verify_checksum
class Segment:
    # Format Header:
    # !   : network byte order (big-endian)
    # H   : src_port (16 bit)
    # H   : dst_port (16 bit)
    # I   : seq_num (32 bit)
    # I   : ack_num (32 bit)
    # B   : data_offset + reserved (4+4 bit)
    # B   : flags (8 bit)
    # H   : window (16 bit)
    # H   : checksum (16 bit)
    # H   : urgent_pointer (16 bit)
    HEADER_FORMAT = '!HHIIBBHHH'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    # Konstruktor
    def __init__(self,
                 src_port: int,
                 dst_port: int,
                 seq_num: int,
                 ack_num: int = 0,
                 flags: int = 0,
                 window: int = 1024,
                 payload: bytes = b''):
        self.src_port = src_port
        self.dst_port = dst_port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.data_offset = 5
        self.flags = flags
        self.window = window
        self.urgent_pointer = 0
        self.payload = payload
    
    def to_bytes(self) -> bytes:
        # Pack header tanpa checksum
        # Data offset adalah 5 (5 * 4 = 20 bytes header)
        offset_reserved = (self.data_offset << 4)
        header_wo_checksum = struct.pack(
            self.HEADER_FORMAT,
            self.src_port,
            self.dst_port,
            self.seq_num,
            self.ack_num,
            offset_reserved,
            self.flags,
            self.window,
            0,  # Placeholder for checksum
            self.urgent_pointer
        )

        # Hitung checksum
        checksum = compute_checksum(header_wo_checksum + self.payload)

        # Pack header dengan checksum
        header = struct.pack(
            self.HEADER_FORMAT,
            self.src_port,
            self.dst_port,
            self.seq_num,
            self.ack_num,
            offset_reserved,
            self.flags,
            self.window,
            checksum,
            self.urgent_pointer
        )
        return header + self.payload
    
    @classmethod
    def from_bytes(cls, raw: bytes) -> 'Segment' :
        #Ambil header
        header = raw[:cls.HEADER_SIZE]
        
        # Unpack header
        unpacked = struct.unpack(cls.HEADER_FORMAT, header)
        (src_port, dst_port, seq_num, ack_num, offset_reserved, flags, window, checksum, urgent_pointer) = unpacked

        # Hitung data offset
        data_offset = (offset_reserved >> 4)
        header_len = data_offset * 4

        # Ambil payload
        payload = raw[header_len:]

        # Verifikasi checksum
        zero_checksum = struct.pack(
            cls.HEADER_FORMAT,
            src_port, dst_port, seq_num, ack_num,
            offset_reserved, flags, window, 0, urgent_pointer
        )
        if not verify_checksum(zero_checksum + payload, checksum):
            raise ValueError("Checksum verification failed")
        
        # Buat instance Segment
        segment = cls(src_port, dst_port, seq_num, ack_num, flags, window, payload)
        segment.urgent_pointer = urgent_pointer
        return segment