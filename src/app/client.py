# DISCLAIMER: server.py pada branch client HANYA UNTUK TESTING! (AKAN DIHAPUS NANTINYA)
# UNTUK SAAT INI HANYA BISA CONNECT 1 KLIEN ENTAH KENAPA
# 1. Buka terminal -> python server.py
# 2. Buka terminal baru -> python client.py 127.0.0.1 -p 55555

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from collections import deque
from protocol.socket_wrapper import BetterUDPSocket
import threading, time, os, argparse

# Fungsi menerima data chat dari server
def receiveDataServer(clientSocket: BetterUDPSocket, msgs: deque, server_ip: str):
    while True:
        try:
            msg = clientSocket.receive() # Asumsi sementara server kirim msg per baris 
            if msg:
                decoded_msg = msg.decode()
                msgs.append(decoded_msg)
                displayChat(msgs, server_ip)
        except Exception:
            pass

# Fungsi heartbeat sekaligus tanda request data ke server
def heartbeat(clientSocket: BetterUDPSocket):
    while True:
        try:
            clientSocket.send("!heartbeat".encode()) # Sementara dikirim dalam format "!heartbeat"
            time.sleep(1)
        except Exception:
            pass

# Mendisplay chat 20 terakhir dalam msgs
def displayChat(msgs: deque, server_ip):
    os.system('cls' if os.name == 'nt' else 'clear')
    # TODO: Mekanisme passing online usernya gimana?
    print(f"Connected to {server_ip}'s chat room (x online users)")
    print("---------------------------------------------------------------------", end='')
    print("\n" + "\n".join(msgs))
    print("---------------------------------------------------------------------")

def main():
    parser = argparse.ArgumentParser(description="Chat client for TCP-over-UDP.")
    parser.add_argument("host", help="Server IP address")
    parser.add_argument("-p", "--port", type=int, required=True, help="Server port")

    args = parser.parse_args()
    SERVER_IP = args.host
    SERVER_PORT = args.port

    clientSock = BetterUDPSocket()

    while not clientSock.connected: # Paksa untuk connect
        try:
            # TODO: Mekanisme passing usernamenya gimana?
            print(f"Mencoba menghubungi server {SERVER_IP} : {SERVER_PORT} ...\n")
            clientSock.connect(SERVER_IP, SERVER_PORT)
            print(f"Berhasil terhubung ke server {SERVER_IP} : {SERVER_PORT}!")
            time.sleep(2)
            os.system('cls' if os.name == 'nt' else 'clear')
        except Exception:
            pass

    session = PromptSession()
    msgs = deque(maxlen=20) # Sementara kepikirannya pake deque untuk simpan chat

    threading.Thread(target=receiveDataServer, args=(clientSock, msgs, SERVER_IP), daemon=True).start()
    # threading.Thread(target=heartbeat, args=(clientSock,), daemon=True).start()
    
    with patch_stdout():
        # TODO: deteksi server mati
        while True:
            try:
                msg = session.prompt("Enter text message: ")

                if msg == "!disconnect":
                    clientSock.send(msg.encode())
                    break
                elif msg.startswith("!kill"):
                    clientSock.send(msg.encode())
                elif msg.startswith("!change"):
                    clientSock.send(msg.encode())
                
                # TODO: jika kalimat terlalu panjang maka dia kepotong karena kena batas maksimum MTU
                clientSock.send(msg.encode()) # .encode() merubah String menjadi bytes

            except Exception:
                pass

if __name__ == "__main__":
    main()