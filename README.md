### ChatTCP - JarJarJarKom

## Deskripsi Umum

ChatTCP adalah implementasi protokol TCP di atas UDP. Proyek ini terdiri dari dua bagian utama:

1. Implementasi fitur TCP di atas UDP - Mengimplementasikan mekanisme TCP seperti three-way handshake, flow control, error detection, dan segmentasi data

2. Aplikasi chat room sederhana - Chat room berbasis command line yang menggunakan protokol TCP buatan sendiri

## Fitur

### Protokol ChatTCP

✅ TCP Segments: Segmentasi data dengan payload maksimal 64 bytes per segment

✅ Three-Way Handshake: Koneksi establishment dengan sequence number acak

✅ Flow Control: Implementasi Selective Repeat ARQ untuk pengiriman data yang efisien

✅ Error Detection: Checksum 16-bit untuk verifikasi integritas data

✅ Connection Termination: FIN-ACK handshake untuk penutupan koneksi

### Aplikasi Chat Room

✅ Multi-client support: Server dapat menangani multiple client secara bersamaan

✅ Real-time messaging: Pengiriman dan penerimaan pesan secara real-time

✅ Heartbeat mechanism: Deteksi client yang terputus (timeout 30 detik)

✅ Special commands: Command khusus untuk disconnect, kill server, dan change username

✅ User management: Tracking user online dan notifikasi join/leave

✅ GUI Client: Interface grafis menggunakan Tkinter (opsional)

## Persyaratan Sistem

<ul>
<li>Python 3.13 atau lebih baru
<li>Package manager uv (recommended) atau pip
<li>Sistem operasi: Windows, Linux, atau macOS
</ul>

## Setup dan Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/labsister22/tugas-besar-if2230-jaringan-komputer-jarjarjarkom.git

cd tugas-besar-if2230-jaringan-komputer-jarjarjarkom
```

### 2. Setup Environment dengan uv (Recommended)

```bash
# Install uv jika belum ada
# Ikuti panduan di: https://docs.astral.sh/uv/getting-started/installation/

uv python install 3.13
uv python pin 3.13

# Initialize project
uv init
```

### 3. Verifikasi Python Version

```bash
python --version
# Output harus: Python 3.13.x
```

## Cara Menjalankan

### Server

```bash
uv run --link-mode=copy -m src.app.server
```

### Client (CLI)

```bash
uv run --link-mode=copy -m src.app.client <server_ip> -p <port> -n <username>

uv run --link-mode=copy -m src.app.client 127.0.0.1 -p 55555 -n Owo
```

### Client (GUI)

```bash
uv run client_gui.py

# Masukkan server IP, port, dan username melalui interface
```

## Command Khusus

```bash
!disconnect - Keluar dari chat room
```

```bash
!kill <password> - Mematikan server (password: admin123)
```

```bash
!change <nama_baru> - Mengubah username
```

```bash
!heartbeat - Heartbeat message (otomatis setiap 1 detik)
```

## Arsitektur dan Implementasi

## TCP Segment Header

Setiap segment memiliki header dengan format:

<ul>
  <li>Source Port (16 bit)</li>
  <li>Destination Port (16 bit)</li>
  <li>Sequence Number (32 bit)</li>
  <li>ACK Number (32 bit)</li>
  <li>Data Offset + Reserved (8 bit)</li>
  <li>Flags (8 bit) - SYN, ACK, FIN</li>
  <li>Window Size (16 bit)</li>
  <li>Checksum (16 bit)</li>
  <li>Urgent Pointer (16 bit)</li>
</ul>

### Flow Control Algorithm

Menggunakan Selective Repeat ARQ dengan window size 4:

<ul>
  <li>Sender dapat mengirim multiple segment dalam window</li>
  <li>Receiver mengirim ACK untuk setiap segment yang diterima</li>
  <li>Automatic retransmission untuk segment yang timeout</li>
  <li>Window sliding setelah menerima ACK</li>
</ul>

### Three-Way Handshake

1. Client → Server
2. Server → ClientServer → Client
3. Client → Server

## Testing dan Simulasi Jaringan Buruk

## Linux

```bash
# Simulasi jaringan buruk
sudo tc qdisc add dev lo root netem delay 100ms 50ms reorder 8% corrupt 5% duplicate 2% 5% loss 5%

# Reset konfigurasi
sudo tc qdisc del dev lo root netem delay 100ms 50ms reorder 8% corrupt 5% duplicate 2% 5% loss 5%
```

## Windows

<ul>
  <li>Download Clumsy dari: <a href="https://jagt.github.io/clumsy/" target="_blank">https://jagt.github.io/clumsy/</a></li>
  <li>Jalankan <strong>clumsy.exe</strong> sebagai administrator</li>
  <li>Konfigurasi: Lag 100±50ms, Drop 5%, Duplicate 2%, Reorder 8%</li>
</ul>

## Author

<table border="5">
  <tr>
    <th>Nama</th>
    <th>NIM</th>
    <th>Pembagian Kerja</th>
  </tr>
  <tr>
    <td>Muh. Rusmin Nurwadin</td>
    <td>13523068</td>
    <td>Flow Control & Selective Repeat ARQ</td>
  </tr>
    <tr>
    <td>Muhammad Iqbal Haidar</td>
    <td>13523111</td>
    <td>Implementasi Client</td>
  </tr>
  <tr>
    <td>Guntara Hambali</td>
    <td>13523114</td>
    <td>Implementasi Server</td>
  </tr>
  <tr>
    <td>Reza Ahmad Syarif</td>
    <td>13523119</td>
    <td>Three-Way Handshake, Checksum</td>
  </tr>
</table>
