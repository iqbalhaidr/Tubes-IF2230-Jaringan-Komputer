# DISCLAIMER: server.py pada branch client HANYA UNTUK TESTING! (AKAN DIHAPUS NANTINYA)
# UNTUK SAAT INI HANYA BISA CONNECT 1 KLIEN ENTAH KENAPA
# 1. Buka terminal -> python server.py
# 2. Buka terminal baru -> python client.py 127.0.0.1 -p 55555

from protocol.socket_wrapper import BetterUDPSocket
import threading
from datetime import datetime

def listenForNewClient(serverSocket: BetterUDPSocket, connectedClients: list[BetterUDPSocket]):
    while True:
        try:
            connSocket, clientAddr = serverSocket.accept(timeout=0.1) # clientAddr = (IP, Port)
            connectedClients.append(connSocket)
            print(f"Client baru terhubung: {clientAddr}")

            client_thread = threading.Thread(target=clientHandler, args=(connSocket,), daemon=True)
            client_thread.start()
        except Exception:
            pass

def clientHandler(client: BetterUDPSocket):
    while True:
        try:
            msg = client.receive(timeout=0.1)
            if msg:
                decoded_msg = msg.decode()
                print(f"[Dari client] {decoded_msg}")
        except Exception:
            pass

def get_formatted_time():
    return datetime.now().strftime("[%I:%M %p]").lstrip("0")  # Hapus 0 di awal jam

def main():
    SERVER_IP = '127.0.0.1' # Local host
    SERVER_PORT = 55555     # Generally save unused port 

    connSocks = []  # Menyimpan socket client yang sedang terhubung
    msgs = []       # Menyimpan seluruh percakapan

    serverSock = BetterUDPSocket() # Socket listener
    serverSock.listen(SERVER_IP, SERVER_PORT)
    print(f"Server listen on {SERVER_IP}:{SERVER_PORT}!\n")
    while True:
        try:
            connSocket, clientAddr = serverSock.accept(timeout=0.1)
            connSocks.append(connSocket)
            print(f"Client baru terhubung: {clientAddr}")

            while True:
                try:
                    msg = connSocket.receive(timeout=0.1)
                    if msg:
                        decoded_msg = msg.decode()
                        print(f"[Dari client] {decoded_msg}")
                        if (decoded_msg != "!heartbeat"):
                            connSocket.send(f"{get_formatted_time()}: {decoded_msg}".encode())
                except Exception:
                    pass

        except Exception:
            pass

if __name__ == "__main__":
    main()