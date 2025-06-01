# server.py - Fixed version
import socket
import threading
import time
from datetime import datetime
from ..protocol.socket_wrapper import BetterUDPSocket


# Event untuk memberi sinyal shutdown server
shutdown_event = threading.Event()
SERVER_KILL_PASSWORD = "admin123"


# Thread-safe client management
connected_clients = {}
clients_lock = threading.Lock()

def get_formatted_time():
    """Returns current time in format [HH:MM AM/PM] without leading zero."""
    return datetime.now().strftime("[%I:%M %p]").lstrip("0").replace(" 0", " ")

def broadcast_message(message: bytes, sender_addr: tuple = None, exclude_sender: bool = True):
    """Safely broadcast message to all connected clients."""
    with clients_lock:
        disconnected_clients = []
        
        for addr, conn in connected_clients.items():
            if exclude_sender and addr == sender_addr:
                continue
                
            try:
                if conn.connected:
                    conn.send(message)
                else:
                    disconnected_clients.append(addr)
            except Exception as e:
                print(f"[{get_formatted_time()}] Failed to send to {addr}: {e}")
                disconnected_clients.append(addr)
        
        # Clean up disconnected clients
        for addr in disconnected_clients:
            if addr in connected_clients:
                print(f"[{get_formatted_time()}] Removing disconnected client {addr}")
                try:
                    if connected_clients[addr].connected:
                         connected_clients[addr].close()
                except:
                    pass
                del connected_clients[addr]

def client_handler(client_conn: BetterUDPSocket, client_address: tuple):
    """Handle individual client communication in separate thread."""
    print(f"[{get_formatted_time()}] Started handler for client {client_address}")
    username = f"User-{client_address[1]}" # Default username, bisa diubah dengan mekanisme login
    
    try:
        # Kirim pesan selamat datang atau notifikasi user bergabung ke semua klien
        join_message = f"[{get_formatted_time()}] [SERVER]: {username} has joined the chat."
        print(join_message)
        broadcast_message(join_message.encode(), sender_addr=client_address, exclude_sender=False)

        while client_conn.connected and not shutdown_event.is_set(): # Periksa shutdown_event
            try:
                msg_bytes = client_conn.receive(timeout=1.0)
                if not msg_bytes:
                    if shutdown_event.is_set(): # Jika server mau shutdown, keluar
                        break
                    continue
                    
                decoded_msg = msg_bytes.decode().strip()
                
                if not decoded_msg:
                    continue
                    
                print(f"[{get_formatted_time()}] <{username}> ({client_address}): {decoded_msg}")

                # Handle special commands
                if decoded_msg == "!disconnect":
                    print(f"[{get_formatted_time()}] <{username}> ({client_address}) requested disconnect.")
                    # Pesan broadcast akan ditangani di finally block saat keluar
                    break
                
            
                elif decoded_msg.startswith("!kill"):
                    parts = decoded_msg.split(" ", 1)
                    if len(parts) == 2 and parts[0] == "!kill":
                        password_attempt = parts[1]
                        if password_attempt == SERVER_KILL_PASSWORD:
                            print(f"[{get_formatted_time()}] SERVER SHUTDOWN INITIATED BY {username} ({client_address}).")
                            shutdown_message = f"[{get_formatted_time()}] [SERVER]: Server is shutting down NOW. (Initiated by {username})"
                            broadcast_message(shutdown_message.encode(), exclude_sender=False)
                            shutdown_event.set() # Memberi sinyal ke main thread dan listener thread
                            break # Keluar dari handler
                        else:
                            error_msg = f"[{get_formatted_time()}] [SERVER]: Incorrect password for !kill command."
                            client_conn.send(error_msg.encode())
                    else:
                        error_msg = f"[{get_formatted_time()}] [SERVER]: Invalid !kill command format. Use: !kill <password>"
                        client_conn.send(error_msg.encode())
                    continue
                elif decoded_msg == "!heartbeat":
                    # Respond to heartbeat if needed
                    continue
                elif decoded_msg.startswith("!"): # Perintah tidak dikenal
                    unknown_cmd_msg = f"[{get_formatted_time()}] [SERVER]: Unknown command: {decoded_msg.split(' ')[0]}"
                    client_conn.send(unknown_cmd_msg.encode())
                    continue
                else:
                    # Regular chat message
                    timestamp = get_formatted_time()
                    full_message = f"{timestamp} {username}: {decoded_msg}" # Sudah ada namanya
                    broadcast_message(full_message.encode(), sender_addr=client_address, exclude_sender=True)


            except socket.timeout:
                # Check if client is still connected or if server is shutting down
                if shutdown_event.is_set():
                    break
                continue # Kembali ke awal loop while client_conn.connected
            except ConnectionResetError:
                print(f"[{get_formatted_time()}] Connection reset by {username} ({client_address}).")
                break
            except Exception as e:
                print(f"[{get_formatted_time()}] <{username}> ({client_address}) Handler error: {e}")
                break
                
    except Exception as e:
        print(f"[{get_formatted_time()}] <{username}> ({client_address}) Fatal handler error: {e}")
    finally:
        print(f"[{get_formatted_time()}] <{username}> ({client_address}) Closing client connection.")
        
    
        # Kirim pesan bahwa user telah keluar, hanya jika bukan karena server shutdown
        if not shutdown_event.is_set() and client_conn.connected: # Cek apakah masih connected sebelum broadcast
            disconnect_broadcast_message = f"[{get_formatted_time()}] [SERVER]: {username} has left the chat."
            broadcast_message(disconnect_broadcast_message.encode(), sender_addr=client_address, exclude_sender=False)

        with clients_lock:
            if client_address in connected_clients:
                del connected_clients[client_address]
                print(f"[{get_formatted_time()}] Client {client_address} removed from active list. Total: {len(connected_clients)}")
        
        try:
            if client_conn.connected:
                 client_conn.close()
        except Exception as e:
            print(f"[{get_formatted_time()}] Error closing connection for {client_address}: {e}")


def listen_for_connections(server_socket: BetterUDPSocket):
    """Listen for new client connections in separate thread."""
    print(f"[{get_formatted_time()}] Connection listener thread started.")
    

    while not shutdown_event.is_set(): # Terus berjalan selama shutdown_event belum di-set
    
        try:
            # Accept new connection with timeout to allow check on shutdown_event
            conn_socket, client_address = server_socket.accept(timeout=1.0) # Timeout lebih pendek
            
        
            if shutdown_event.is_set(): # Jika server mau shutdown, jangan terima koneksi baru
                try:
                    conn_socket.close() # Tutup koneksi yang baru saja diterima
                except: pass
                break # Keluar dari loop listener
    
            with clients_lock:
                if client_address in connected_clients:
                    print(f"[{get_formatted_time()}] Duplicate connection from {client_address}. Rejecting.")
                    try:
                        conn_socket.close()
                    except:
                        pass
                    continue

                # Add new client
                connected_clients[client_address] = conn_socket
                client_count = len(connected_clients)
            
            print(f"[{get_formatted_time()}] New client connected: {client_address} (Total: {client_count})")
            
            # Start handler thread for this client
            client_thread = threading.Thread(
                target=client_handler,
                args=(conn_socket, client_address),
                daemon=True
            )
            client_thread.start()

        except socket.timeout:
            # Normal timeout, continue listening (dan periksa shutdown_event di awal loop)
            continue
        except Exception as e:
            if not shutdown_event.is_set(): # Hanya print error jika bukan karena sedang shutdown
                 print(f"[{get_formatted_time()}] Error accepting connection: {e}")
            # time.sleep(0.1) # Beri jeda singkat jika ada error non-timeout
    print(f"[{get_formatted_time()}] Connection listener thread stopped.") # Pesan saat listener berhenti


def main():
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 12354

    server_socket = BetterUDPSocket()
    listener_thread = None
    
    try:
        server_socket.listen(SERVER_IP, SERVER_PORT)
        print(f"[{get_formatted_time()}] Server listening on {SERVER_IP}:{SERVER_PORT}")
        print(f"[{get_formatted_time()}] Press Ctrl+C to stop server\n")

        listener_thread = threading.Thread(
            target=listen_for_connections,
            args=(server_socket,),
            daemon=True
        )
        listener_thread.start()

        # Main server loop, periksa shutdown_event
        while not shutdown_event.is_set():
            time.sleep(0.5) # Cek setiap setengah detik
            
            # Opsi: Pemeriksaan periodik koneksi mati (bisa juga dipindahkan ke dalam broadcast_message)
            # with clients_lock:
            #     if connected_clients:
            #         # Ini bisa menjadi mahal jika banyak klien, pertimbangkan frekuensi
            #         # For simplicity, assuming client_conn.connected is reliable enough for now
            #         pass
        
        print(f"\n[{get_formatted_time()}] Shutdown event received, initiating server shutdown sequence...")

    except KeyboardInterrupt:
        print(f"\n[{get_formatted_time()}] Server shutdown requested by user (Ctrl+C).")
        shutdown_event.set() # Set event untuk memberi tahu thread lain
    except Exception as e:
        print(f"[{get_formatted_time()}] Server error: {e}")
        shutdown_event.set() # Set event jika ada error tak terduga
    finally:
        print(f"[{get_formatted_time()}] Shutting down server...")

    
        # Tunggu listener thread selesai jika masih berjalan (setelah shutdown_event di-set)
        if listener_thread and listener_thread.is_alive():
            print(f"[{get_formatted_time()}] Waiting for connection listener to stop...")
            listener_thread.join(timeout=5.0) # Beri timeout untuk join
            if listener_thread.is_alive():
                print(f"[{get_formatted_time()}] Listener thread did not stop in time.")
        
        # Kirim pesan terakhir ke semua klien yang masih terhubung
        final_shutdown_msg = f"[{get_formatted_time()}] [SERVER]: Server has been shut down. You are disconnected."
        broadcast_message(final_shutdown_msg.encode(), exclude_sender=False) # Kirim ke semua
        time.sleep(0.5) # Beri waktu pesan terkirim

        # Tutup semua koneksi klien
        print(f"[{get_formatted_time()}] Closing all client connections...")
        with clients_lock:
            client_list = list(connected_clients.items()) # Salin list untuk iterasi aman
        
        for addr, conn in client_list: # Iterasi pada salinan
            print(f"[{get_formatted_time()}] Closing connection to {addr}")
            try:
                if conn.connected: # Hanya tutup jika masih 'connected' menurut state objek
                    conn.close()
            except Exception as e:
                print(f"[{get_formatted_time()}] Error closing connection to {addr} during final shutdown: {e}")
        
        with clients_lock:
            connected_clients.clear()
        
        # Tutup server socket
        try:
            print(f"[{get_formatted_time()}] Closing server socket...")
            server_socket.close()
        except Exception as e:
            print(f"[{get_formatted_time()}] Error closing server socket: {e}")
            
        print(f"[{get_formatted_time()}] Server stopped.")

if __name__ == "__main__":
    main()