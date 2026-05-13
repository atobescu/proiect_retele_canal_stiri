import socket
import threading
import sys

# ─── Configurare ───────────────────────────────────────────────
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000


def receive_messages(sock):
    """Thread care asculta mesaje de la server si le afiseaza."""
    try:
        buffer = ""
        while True:
            data = sock.recv(4096)
            if not data:
                print("\n[!] Conexiunea cu serverul a fost inchisa.")
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                parts = line.split("|")
                msg_type = parts[0]

                if msg_type == "OK":
                    print(f"\n  ✓ {parts[1] if len(parts) > 1 else 'OK'}")

                elif msg_type == "ERROR":
                    print(f"\n  ✗ {parts[1] if len(parts) > 1 else 'Eroare'}")

                elif msg_type == "CHANNELS":
                    channel_data = parts[1] if len(parts) > 1 else ""
                    if not channel_data:
                        print("\n  Nu exista canale.")
                    else:
                        print("\n  ╔══════════════════════════════════════╗")
                        print("  ║         CANALE DISPONIBILE           ║")
                        print("  ╠══════════════════════════════════════╣")
                        for ch in channel_data.split(","):
                            if ":" in ch:
                                name, desc = ch.split(":", 1)
                                print(f"  ║  📺 {name:<15} - {desc:<15} ║")
                        print("  ╚══════════════════════════════════════╝")

                elif msg_type == "NOTIFY_NEW_CHANNEL":
                    ch_name = parts[1] if len(parts) > 1 else "?"
                    ch_desc = parts[2] if len(parts) > 2 else ""
                    print(f"\n  🆕 Canal nou: '{ch_name}' — {ch_desc}")

                elif msg_type == "NOTIFY_DEL_CHANNEL":
                    ch_name = parts[1] if len(parts) > 1 else "?"
                    print(f"\n  🗑️  Canalul '{ch_name}' a fost sters!")

                elif msg_type == "NEWS":
                    ch_name = parts[1] if len(parts) > 1 else "?"
                    news_text = parts[2] if len(parts) > 2 else ""
                    print(f"\n  📰 [{ch_name}] {news_text}")

                else:
                    print(f"\n  [SERVER] {line}")

                print("  > ", end="", flush=True)

    except ConnectionResetError:
        print("\n[!] Conexiunea a fost resetata de server.")
    except Exception as e:
        print(f"\n[!] Eroare la primirea mesajelor: {e}")


def print_menu():
    """Afiseaza meniul de comenzi."""
    print("""
  ╔══════════════════════════════════════╗
  ║       CANALE DE STIRI - CLIENT      ║
  ╠══════════════════════════════════════╣
  ║  1. list       - Lista canale       ║
  ║  2. create     - Creaza canal       ║
  ║  3. delete     - Sterge canal       ║
  ║  4. subscribe  - Aboneaza-te        ║
  ║  5. unsubscribe- Dezaboneaza-te     ║
  ║  6. publish    - Publica stire      ║
  ║  7. help       - Arata meniul       ║
  ║  8. quit       - Deconectare        ║
  ╚══════════════════════════════════════╝
    """)


def main():
    # Parametri conexiune
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    print(f"\n  Conectare la server {host}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("  ✓ Conectat la server!")
    except ConnectionRefusedError:
        print("  ✗ Nu ma pot conecta la server. Verifica daca serverul ruleaza.")
        return
    except Exception as e:
        print(f"  ✗ Eroare la conectare: {e}")
        return

    # Thread pentru primirea mesajelor
    recv_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    recv_thread.start()

    # Identificare
    name = input("\n  Introdu numele tau: ").strip()
    if not name:
        name = "Anonim"
    sock.sendall(f"SET_NAME|{name}\n".encode("utf-8"))

    print_menu()

    # Bucla principala
    try:
        while True:
            cmd = input("  > ").strip().lower()

            if not cmd:
                continue

            if cmd == "list" or cmd == "1":
                sock.sendall("LIST\n".encode("utf-8"))

            elif cmd == "create" or cmd == "2":
                ch_name = input("  Nume canal: ").strip()
                ch_desc = input("  Descriere: ").strip()
                if ch_name:
                    sock.sendall(f"CREATE|{ch_name}|{ch_desc}\n".encode("utf-8"))
                else:
                    print("  ✗ Numele canalului nu poate fi gol.")

            elif cmd == "delete" or cmd == "3":
                ch_name = input("  Nume canal de sters: ").strip()
                if ch_name:
                    sock.sendall(f"DELETE|{ch_name}\n".encode("utf-8"))
                else:
                    print("  ✗ Numele canalului nu poate fi gol.")

            elif cmd == "subscribe" or cmd == "4":
                ch_name = input("  Nume canal: ").strip()
                if ch_name:
                    sock.sendall(f"SUBSCRIBE|{ch_name}\n".encode("utf-8"))
                else:
                    print("  ✗ Numele canalului nu poate fi gol.")

            elif cmd == "unsubscribe" or cmd == "5":
                ch_name = input("  Nume canal: ").strip()
                if ch_name:
                    sock.sendall(f"UNSUBSCRIBE|{ch_name}\n".encode("utf-8"))
                else:
                    print("  ✗ Numele canalului nu poate fi gol.")

            elif cmd == "publish" or cmd == "6":
                ch_name = input("  Nume canal: ").strip()
                news = input("  Text stire: ").strip()
                if ch_name and news:
                    sock.sendall(f"PUBLISH|{ch_name}|{news}\n".encode("utf-8"))
                else:
                    print("  ✗ Canalul si textul stirii sunt obligatorii.")

            elif cmd == "help" or cmd == "7":
                print_menu()

            elif cmd == "quit" or cmd == "8":
                sock.sendall("QUIT\n".encode("utf-8"))
                break

            else:
                print("  ✗ Comanda necunoscuta. Scrie 'help' pentru meniu.")

    except (KeyboardInterrupt, EOFError):
        print("\n  Deconectare...")
        try:
            sock.sendall("QUIT\n".encode("utf-8"))
        except Exception:
            pass
    finally:
        sock.close()
        print("  ✓ Deconectat.")


if __name__ == "__main__":
    main()
