import socket
import threading
import os

# ─── Configurare ───────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000
BANNED_WORDS_FILE = os.path.join(os.path.dirname(__file__), "banned_words.txt")

# ─── Date globale (protejate cu lock) ──────────────────────────
lock = threading.Lock()

# channels[nume] = {"description": str, "owner": str}
channels = {}

# subscriptions[nume_canal] = set() de client sockets
subscriptions = {}

# clients[socket] = {"name": str, "addr": tuple}
clients = {}

# Lista de cuvinte interzise
banned_words = []


def load_banned_words():
    """Incarca cuvintele interzise din fisier."""
    global banned_words
    try:
        with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
            banned_words = [w.strip().lower() for w in f.readlines() if w.strip()]
        print(f"[SERVER] S-au incarcat {len(banned_words)} cuvinte interzise: {banned_words}")
    except FileNotFoundError:
        print("[SERVER] ATENTIE: banned_words.txt nu a fost gasit. Niciun cuvant interzis.")
        banned_words = []


def send_msg(client_socket, message):
    """Trimite un mesaj catre un client. Adauga newline la sfarsit."""
    try:
        client_socket.sendall((message + "\n").encode("utf-8"))
    except Exception:
        pass


def broadcast(message, exclude=None):
    """Trimite un mesaj catre toti clientii conectati, optional excludand unul."""
    with lock:
        for sock in list(clients.keys()):
            if sock != exclude:
                send_msg(sock, message)


def contains_banned_word(text):
    """Verifica daca textul contine cuvinte interzise (case-insensitive)."""
    text_lower = text.lower()
    for word in banned_words:
        if word in text_lower:
            return True
    return False


def handle_client(client_socket, addr):
    """Handler pentru un client conectat. Ruleaza intr-un thread separat."""
    print(f"[SERVER] Client conectat: {addr}")
    client_name = None

    with lock:
        clients[client_socket] = {"name": None, "addr": addr}

    try:
        buffer = ""
        while True:
            data = client_socket.recv(4096)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                parts = line.split("|")
                command = parts[0].upper()

                # ── SET_NAME ──
                if command == "SET_NAME" and len(parts) >= 2:
                    client_name = parts[1].strip()
                    with lock:
                        clients[client_socket]["name"] = client_name
                    send_msg(client_socket, f"OK|Bine ai venit, {client_name}!")
                    print(f"[SERVER] Client {addr} s-a identificat ca: {client_name}")

                # ── LIST ──
                elif command == "LIST":
                    with lock:
                        if not channels:
                            send_msg(client_socket, "CHANNELS|")
                        else:
                            ch_list = ",".join(
                                f"{name}:{info['description']}"
                                for name, info in channels.items()
                            )
                            send_msg(client_socket, f"CHANNELS|{ch_list}")

                # ── CREATE ──
                elif command == "CREATE" and len(parts) >= 3:
                    ch_name = parts[1].strip()
                    ch_desc = parts[2].strip()

                    if not client_name:
                        send_msg(client_socket, "ERROR|Trebuie sa te identifici mai intai (SET_NAME)")
                        continue

                    with lock:
                        if ch_name in channels:
                            send_msg(client_socket, f"ERROR|Canalul '{ch_name}' exista deja")
                        else:
                            channels[ch_name] = {
                                "description": ch_desc,
                                "owner": client_name
                            }
                            subscriptions[ch_name] = set()
                            send_msg(client_socket, f"OK|Canalul '{ch_name}' a fost creat")
                            print(f"[SERVER] Canal creat: {ch_name} de {client_name}")

                    # Notifica toti clientii (in afara lock-ului pentru a evita deadlock)
                    if ch_name in channels:
                        broadcast(f"NOTIFY_NEW_CHANNEL|{ch_name}|{ch_desc}", exclude=client_socket)

                # ── DELETE ──
                elif command == "DELETE" and len(parts) >= 2:
                    ch_name = parts[1].strip()

                    if not client_name:
                        send_msg(client_socket, "ERROR|Trebuie sa te identifici mai intai (SET_NAME)")
                        continue

                    deleted = False
                    with lock:
                        if ch_name not in channels:
                            send_msg(client_socket, f"ERROR|Canalul '{ch_name}' nu exista")
                        elif channels[ch_name]["owner"] != client_name:
                            send_msg(client_socket, "ERROR|Nu poti sterge un canal care nu iti apartine")
                        else:
                            del channels[ch_name]
                            del subscriptions[ch_name]
                            deleted = True
                            send_msg(client_socket, f"OK|Canalul '{ch_name}' a fost sters")
                            print(f"[SERVER] Canal sters: {ch_name} de {client_name}")

                    if deleted:
                        broadcast(f"NOTIFY_DEL_CHANNEL|{ch_name}", exclude=client_socket)

                # ── SUBSCRIBE ──
                elif command == "SUBSCRIBE" and len(parts) >= 2:
                    ch_name = parts[1].strip()

                    with lock:
                        if ch_name not in channels:
                            send_msg(client_socket, f"ERROR|Canalul '{ch_name}' nu exista")
                        elif client_socket in subscriptions[ch_name]:
                            send_msg(client_socket, f"ERROR|Esti deja abonat la '{ch_name}'")
                        else:
                            subscriptions[ch_name].add(client_socket)
                            send_msg(client_socket, f"OK|Te-ai abonat la '{ch_name}'")
                            print(f"[SERVER] {client_name} s-a abonat la {ch_name}")

                # ── UNSUBSCRIBE ──
                elif command == "UNSUBSCRIBE" and len(parts) >= 2:
                    ch_name = parts[1].strip()

                    with lock:
                        if ch_name not in channels:
                            send_msg(client_socket, f"ERROR|Canalul '{ch_name}' nu exista")
                        elif client_socket not in subscriptions[ch_name]:
                            send_msg(client_socket, f"ERROR|Nu esti abonat la '{ch_name}'")
                        else:
                            subscriptions[ch_name].discard(client_socket)
                            send_msg(client_socket, f"OK|Te-ai dezabonat de la '{ch_name}'")
                            print(f"[SERVER] {client_name} s-a dezabonat de la {ch_name}")

                # ── PUBLISH ──
                elif command == "PUBLISH" and len(parts) >= 3:
                    ch_name = parts[1].strip()
                    news_text = parts[2].strip()

                    if not client_name:
                        send_msg(client_socket, "ERROR|Trebuie sa te identifici mai intai (SET_NAME)")
                        continue

                    with lock:
                        if ch_name not in channels:
                            send_msg(client_socket, f"ERROR|Canalul '{ch_name}' nu exista")
                            continue
                        if channels[ch_name]["owner"] != client_name:
                            send_msg(client_socket, "ERROR|Doar proprietarul canalului poate publica stiri")
                            continue

                        # Filtrare cuvinte interzise
                        if contains_banned_word(news_text):
                            send_msg(client_socket, f"ERROR|Stirea contine cuvinte interzise si a fost blocata")
                            print(f"[SERVER] Stire blocata pe {ch_name}: {news_text}")
                            continue

                        # Trimite stirea catre toti abonatii
                        subscribers = list(subscriptions[ch_name])

                    send_msg(client_socket, f"OK|Stirea a fost publicata pe '{ch_name}'")
                    for sub_sock in subscribers:
                        send_msg(sub_sock, f"NEWS|{ch_name}|{news_text}")
                    print(f"[SERVER] Stire publicata pe {ch_name}: {news_text}")

                # ── QUIT ──
                elif command == "QUIT":
                    send_msg(client_socket, "OK|La revedere!")
                    break

                # ── Comanda necunoscuta ──
                else:
                    send_msg(client_socket, "ERROR|Comanda necunoscuta")

    except ConnectionResetError:
        print(f"[SERVER] Client deconectat brusc: {addr}")
    except Exception as e:
        print(f"[SERVER] Eroare la client {addr}: {e}")
    finally:
        # Curatare la deconectare
        with lock:
            # Elimina din toate subscrierile
            for ch_name in subscriptions:
                subscriptions[ch_name].discard(client_socket)

            # Elimina din lista de clienti
            if client_socket in clients:
                del clients[client_socket]

        client_socket.close()
        print(f"[SERVER] Client deconectat: {addr} ({client_name})")


def main():
    load_banned_words()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"[SERVER] Serverul ruleaza pe {HOST}:{PORT}")
    print("[SERVER] Astept conexiuni...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Serverul se opreste...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
