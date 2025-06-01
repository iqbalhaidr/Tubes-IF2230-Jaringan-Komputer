# client.py
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from collections import deque
from protocol.socket_wrapper import BetterUDPSocket
import threading, time, os, argparse, socket

thread_lock = threading.Lock()

# Fungsi menerima data chat dari server, merangkai segmen hingga newline
def receiveDataServer(clientSocket: BetterUDPSocket, msgs: deque, server_ip: str):
    cnt = 0
    buffer = b""
    while True:
        try:
            chunk = clientSocket.receive(timeout=0.1)
            if not chunk:
                continue

            buffer += chunk

            # Selama ada newline, proses satu baris utuh
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                decoded_msg = line.decode("utf-8", errors="replace")

                if decoded_msg == "SHUTDOWN":
                    print("Exiting in 3 seconds...")
                    time.sleep(3)
                    os._exit(0)

                if decoded_msg.startswith("COUNT: "):
                    _, c = decoded_msg.split(": ", 1)
                    try:
                        cnt = int(c)
                    except:
                        pass
                    # Jangan append ke msgs, langsung lanjut
                    continue

                # Append pesan baru dan refresh tampilan
                msgs.append(decoded_msg)
            displayChat(msgs, server_ip, cnt)

        except Exception:
            continue

# Fungsi heartbeat sebagai tanda request data ke server
def heartbeat(clientSocket: BetterUDPSocket):
    while True:
        try:
            with thread_lock:
                clientSocket.send("[HEARTBEAT]: !heartbeat\n".encode("utf-8"))
            time.sleep(3)
        except Exception:
            continue

# Mendisplay chat 20 terakhir dalam msgs
def displayChat(msgs: deque, server_ip: str, cnt: int):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"Connected to {server_ip}'s chat room ({cnt} online users)")
    print("---------------------------------------------------------------------", end='')
    print("\n" + "\n".join(msgs))
    print("---------------------------------------------------------------------")

def main():
    parser = argparse.ArgumentParser(description="Chat client for TCP-over-UDP.")
    parser.add_argument("host", help="Server IP address")
    parser.add_argument("-p", "--port", type=int, required=True, help="Server port")
    parser.add_argument("-n", "--name", type=str, required=True, help="Display name")
    args = parser.parse_args()

    SERVER_IP = args.host
    SERVER_PORT = args.port
    CLIENT_NAME = args.name

    if CLIENT_NAME.upper() == "SERVER":
        print("Display name is not allowed. Please use another display name.")
        return

    clientSock = BetterUDPSocket(debug=False)

    # Loop hingga berhasil connect ke server
    while not clientSock.connected:
        try:
            print(f"Mencoba menghubungi server {SERVER_IP}:{SERVER_PORT} ...")
            clientSock.connect(SERVER_IP, SERVER_PORT)
            print(f"Berhasil terhubung ke server {SERVER_IP}:{SERVER_PORT}!")
            time.sleep(1)
            os.system('cls' if os.name == 'nt' else 'clear')
        except Exception:
            continue

    msgAwal = f"AWAL: !awal {CLIENT_NAME}\n"
    with thread_lock:
        clientSock.send(msgAwal.encode("utf-8"))

    session = PromptSession()
    msgs = deque(maxlen=20)

    # Mulai thread penerima data
    threading.Thread(
        target=receiveDataServer,
        args=(clientSock, msgs, SERVER_IP),
        daemon=True
    ).start()

    # Mulai thread heartbeat
    threading.Thread(
        target=heartbeat,
        args=(clientSock,),
        daemon=True
    ).start()

    with patch_stdout():
        while True:
            try:
                msg = session.prompt("Enter text message: ").strip()
                if not msg:
                    continue

                if msg == "!disconnect":
                    with thread_lock:
                        clientSock.send(f"{CLIENT_NAME}: {msg}\n".encode("utf-8"))
                    print("Berhasil disconnect dari server!")
                    time.sleep(1)
                    print("Menutup aplikasi...")
                    time.sleep(2)
                    os.system('cls' if os.name == 'nt' else 'clear')
                    break

                elif msg.startswith("!kill"):
                    with thread_lock:
                        clientSock.send(f"{CLIENT_NAME}: {msg}\n".encode("utf-8"))
                    continue

                elif msg.startswith("!change"):
                    OLD = CLIENT_NAME
                    CLIENT_NAME = msg.removeprefix("!change ").strip() or CLIENT_NAME

                    if CLIENT_NAME.upper() == "SERVER":
                        print("Display name is not allowed. Please use another display name.")
                        CLIENT_NAME = OLD
                        time.sleep(5)
                        continue

                    with thread_lock:
                        clientSock.send(f"[SERVER]: {OLD} changes its username to {CLIENT_NAME}\n".encode("utf-8"))
                    continue

                # Chat biasa; selalu akhiri dengan newline
                with thread_lock:
                    clientSock.send(f"{CLIENT_NAME}: {msg}\n".encode("utf-8"))

            except (EOFError, KeyboardInterrupt):
                # Ctrl+D atau Ctrl+C → disconnect gracefully
                try:
                    with thread_lock:
                        clientSock.send(f"{CLIENT_NAME}: !disconnect\n".encode("utf-8"))
                except:
                    pass
                break
            except Exception:
                continue

if __name__ == "__main__":
    main()
