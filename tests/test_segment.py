import unittest
from src.protocol.segment import Segment
from src.protocol.checksum import compute_checksum, verify_checksum

class TestSegmentAndChecksum(unittest.TestCase):
    def test_checksum_basic(self):
        data = b"hello"
        chk = compute_checksum(data)
        # verify_checksum harus True untuk data + checksum
        self.assertTrue(verify_checksum(data, chk))

    def test_checksum_odd_length(self):
        data = b"abc"  # panjang ganjil
        chk = compute_checksum(data)
        self.assertTrue(verify_checksum(data, chk))

    def test_segment_pack_unpack(self):
        # Buat segment contoh
        seg1 = Segment(
            src_port=1234,
            dst_port=5678,
            seq_num=42,
            ack_num=0,
            flags=0x02,    # SYN
            payload=b"ping"
        )
        raw = seg1.to_bytes()

        # Parse kembali
        seg2 = Segment.from_bytes(raw)

        # Bandingkan atribut
        self.assertEqual(seg2.src_port, 1234)
        self.assertEqual(seg2.dst_port, 5678)
        self.assertEqual(seg2.seq_num, 42)
        self.assertEqual(seg2.ack_num, 0)
        self.assertEqual(seg2.flags, 0x02)
        self.assertEqual(seg2.payload, b"ping")

    def test_checksum_in_segment(self):
        seg = Segment(1000, 2000, 1, payload=b"data")
        raw = seg.to_bytes()
        # Ambil 20 byte header + payload
        # Cek bahwa verify_checksum(header_without_chk + payload, chk) True
        header = raw[:Segment.HEADER_SIZE]
        payload = raw[Segment.HEADER_SIZE:]
        # Unpack header untuk ambil field checksum
        import struct
        fmt = Segment.HEADER_FORMAT
        fields = struct.unpack(fmt, header)
        chk = fields[7]  # index checksum
        # Buat header tanpa chk
        hdr_wo_chk = struct.pack(
            fmt,
            fields[0], fields[1], fields[2], fields[3],
            fields[4], fields[5], fields[6],
            0, fields[8]
        )
        from src.protocol.checksum import verify_checksum
        self.assertTrue(verify_checksum(hdr_wo_chk + payload, chk))

if __name__ == "__main__":
    unittest.main()
