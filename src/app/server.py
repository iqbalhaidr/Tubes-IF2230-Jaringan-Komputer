# server.py - Fixed version
import socket
import threading
import time
from datetime import datetime
from protocol.socket_wrapper import BetterUDPSocket

# Thread-safe client management
connected_clients = {}
clients_lock = threading.Lock()

def get_formatted_time():
    """Returns current time in format [HH:MM AM/PM] without leading zero."""
    return datetime.now().strftime("[%I:%M %p]").lstrip("0")

def broadcast_message(message: bytes, sender_addr: tuple = None):
    """Safely broadcast message to all connected clients except sender."""
    with clients_lock:
        disconnected_clients = []
        
        for addr, conn in connected_clients.items():
            if addr == sender_addr:  # Don't send back to sender
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
                    connected_clients[addr].close()
                except:
                    pass
                del connected_clients[addr]

def client_handler(client_conn: BetterUDPSocket, client_address: tuple):
    """Handle individual client communication in separate thread."""
    print(f"[{get_formatted_time()}] Started handler for client {client_address}")
    
    try:
        while client_conn.connected:
            try:
                msg = client_conn.receive(timeout=5.0)
                if not msg:
                    continue
                    
                decoded_msg = msg.decode().strip()
                
                if not decoded_msg:
                    continue
                    
                print(f"[{get_formatted_time()}][{client_address}] Received: {decoded_msg}")

                # Handle special commands
                if decoded_msg == "!disconnect":
                    print(f"[{get_formatted_time()}][{client_address}] Client requested disconnect.")
                    break
                elif decoded_msg == "!heartbeat":
                    # Respond to heartbeat if needed
                    continue
                elif decoded_msg.startswith("!"):
                    # Handle other special commands
                    continue
                else:
                    # Regular chat message - broadcast to all other clients
                    timestamp = get_formatted_time()
                    full_message = f"{timestamp} <{client_address[0]}:{client_address[1]}>: {decoded_msg}"
                    broadcast_message(full_message.encode(), sender_addr=client_address)

            except socket.timeout:
                # Check if client is still connected
                continue
            except Exception as e:
                print(f"[{get_formatted_time()}][{client_address}] Handler error: {e}")
                break
                
    except Exception as e:
        print(f"[{get_formatted_time()}][{client_address}] Fatal handler error: {e}")
    finally:
        # Cleanup client connection
        print(f"[{get_formatted_time()}][{client_address}] Closing client connection.")
        
        with clients_lock:
            if client_address in connected_clients:
                del connected_clients[client_address]
        
        try:
            client_conn.close()
        except:
            pass

def listen_for_connections(server_socket: BetterUDPSocket):
    """Listen for new client connections in separate thread."""
    print(f"[{get_formatted_time()}] Connection listener thread started.")
    
    while True:
        try:
            # Accept new connection with timeout to allow clean shutdown
            conn_socket, client_address = server_socket.accept(timeout=2.0)
            
            # Check for duplicate connections
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
            # Normal timeout, continue listening
            continue
        except Exception as e:
            print(f"[{get_formatted_time()}] Error accepting connection: {e}")
            # Don't break, continue listening for other connections
            time.sleep(1)

def main():
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 12354

    # Create server socket
    server_socket = BetterUDPSocket()
    
    try:
        server_socket.listen(SERVER_IP, SERVER_PORT)
        print(f"[{get_formatted_time()}] Server listening on {SERVER_IP}:{SERVER_PORT}")
        print(f"[{get_formatted_time()}] Press Ctrl+C to stop server\n")

        # Start connection listener thread
        listener_thread = threading.Thread(
            target=listen_for_connections,
            args=(server_socket,),
            daemon=True
        )
        listener_thread.start()

        # Main server loop
        while True:
            time.sleep(1)
            
            # Periodically check and clean up dead connections
            with clients_lock:
                if connected_clients:
                    active_clients = len([c for c in connected_clients.values() if c.connected])
                    if active_clients != len(connected_clients):
                        print(f"[{get_formatted_time()}] Active clients: {active_clients}")

    except KeyboardInterrupt:
        print(f"\n[{get_formatted_time()}] Server shutdown requested by user.")
    except Exception as e:
        print(f"[{get_formatted_time()}] Server error: {e}")
    finally:
        # Cleanup
        print(f"[{get_formatted_time()}] Shutting down server...")
        
        # Close all client connections
        with clients_lock:
            for addr, conn in list(connected_clients.items()):
                print(f"[{get_formatted_time()}] Closing connection to {addr}")
                try:
                    conn.close()
                except:
                    pass
            connected_clients.clear()
        
        # Close server socket
        try:
            server_socket.close()
        except:
            pass
            
        print(f"[{get_formatted_time()}] Server stopped.")

if __name__ == "__main__":
    main()