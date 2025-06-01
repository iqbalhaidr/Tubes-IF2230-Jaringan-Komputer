import socket
import threading
from datetime import datetime
from protocol.socket_wrapper import BetterUDPSocket

# Dictionary untuk menyimpan koneksi client yang aktif.
connected_clients: dict[tuple, BetterUDPSocket] = {}
client_locks: dict[tuple, threading.Lock] = {} # Untuk mengamankan akses ke socket client jika diperlukan

def get_formatted_time():
    """Mengembalikan waktu saat ini dalam format [HH:MM AM/PM] tanpa leading zero di jam."""
    return datetime.now().strftime("[%I:%M %p]").lstrip("0")

def client_handler(client_conn: BetterUDPSocket, client_address: tuple):
    """
    Fungsi ini akan dijalankan di thread terpisah untuk setiap klien yang terhubung.
    Tugasnya adalah menerima pesan dari klien dan mengirim balasan.
    """
    print(f"[HANDLER] Memulai penanganan untuk klien {client_address}")
    try:
        while client_conn.connected:
            try:
                msg = client_conn.receive(timeout=3)
                if msg:
                    decoded_msg = msg.decode()
                    print(f"[{get_formatted_time()}][{client_address}] Menerima: {decoded_msg}")

                    if decoded_msg == "!quit":
                        print(f"[{get_formatted_time()}][{client_address}] Klien meminta keluar.")
                        break 

                    if decoded_msg != "!heartbeat":
                        full_message = f"{get_formatted_time()} <{client_address[1]}>: {decoded_msg}".encode()

                        for addr, conn in list(connected_clients.items()): 
                            if conn.connected: 
                                try:
                                    conn.send(full_message)
                                except Exception as e:
                                    print(f"[{get_formatted_time()}] Gagal mengirim ke {addr}: {e}")
            except socket.timeout:
                pass
            except RuntimeError as e:

                print(f"[{get_formatted_time()}][{client_address}] Runtime error: {e}. Menutup koneksi.")
                break
            except Exception as e:
                print(f"[{get_formatted_time()}][{client_address}] Error dalam handler klien: {e}")
                break
    finally:

        print(f"[{get_formatted_time()}][{client_address}] Menutup koneksi klien.")
        if client_address in connected_clients:
            del connected_clients[client_address]
        if client_address in client_locks:
            del client_locks[client_address]
        client_conn.close()

def listen_for_new_connections(server_listener_socket: BetterUDPSocket):
    """
    Fungsi ini dijalankan di thread terpisah untuk terus menerima koneksi baru.
    """
    print(f"[{get_formatted_time()}] Thread listener aktif.")
    while True:
        try:

            conn_socket, client_address = server_listener_socket.accept(timeout=1.0)
            
            if client_address in connected_clients:
                print(f"[{get_formatted_time()}] Klien {client_address} mencoba terhubung ulang. Mengabaikan.")
                conn_socket.close() # Tutup socket duplikat
                continue

            connected_clients[client_address] = conn_socket
            client_locks[client_address] = threading.Lock() 
            print(f"[{get_formatted_time()}] Klien baru terhubung: {client_address}")

            # thread baru untuk menangani komunikasi dengan klien ini
            client_thread = threading.Thread(
                target=client_handler,
                args=(conn_socket, client_address),
                daemon=True 
            )
            client_thread.start()

        except socket.timeout:
            pass
        except Exception as e:
            print(f"[{get_formatted_time()}] Error saat menerima koneksi baru: {e}")
            break

def main():
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 55555

    server_listener_socket = BetterUDPSocket()
    server_listener_socket.listen(SERVER_IP, SERVER_PORT)
    print(f"[{get_formatted_time()}] Server mendengarkan di {SERVER_IP}:{SERVER_PORT}\n")

    # Jalankan thread untuk terus menerima koneksi baru
    listener_thread = threading.Thread(
        target=listen_for_new_connections,
        args=(server_listener_socket,),
        daemon=True
    )
    listener_thread.start()


    try:
        while True:
            time.sleep(1) 
    except KeyboardInterrupt:
        print(f"[{get_formatted_time()}] Server dimatikan oleh pengguna.")
    finally:
        server_listener_socket.close() 

        for addr, conn in list(connected_clients.items()):
            print(f"[{get_formatted_time()}] Menutup koneksi sisa dengan {addr}...")
            conn.close()
        print(f"[{get_formatted_time()}] Server telah berhenti.")

if __name__ == "__main__":
    import time
    main()