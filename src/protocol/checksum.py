def compute_checksum(data: bytes) -> int:
    """
    Hitung checksum untuk data yang diberikan.
    Menggunakan algoritma checksum 16-bit.
    :param data: Data yang akan dihitung checksum-nya.
    :return: Nilai checksum 16-bit.
    """
    # 1) Jika panjang data ganjil, tambahkan byte nol di akhir
    if len(data) % 2 != 0:
        data += b'\x00'

    total = 0
    # 2) Hitung jumlah dari setiap 16-bit word
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
        # wrap around jika total lebih dari 16 bit
        total = (total & 0xFFFF) + (total >> 16)

    # 3) Ambil komplemen dari total
    checksum = ~total & 0xFFFF
    return checksum

def verify_checksum(data: bytes, checksum: int) -> bool:
    """
    Verifikasi checksum untuk data yang diberikan.
    :param data: Data yang akan diverifikasi.
    :param checksum: Nilai checksum yang diharapkan.
    :return: True jika checksum valid, False jika tidak.
    """
    chk_bytes = checksum.to_bytes(2, byteorder='big')
    # 1) Hitung checksum untuk data
    computed_checksum = compute_checksum(data)
    # 2) Bandingkan dengan checksum yang diberikan
    return computed_checksum == checksum
