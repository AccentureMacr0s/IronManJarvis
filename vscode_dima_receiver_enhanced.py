
import socket
import os
import sys
from datetime import datetime

PORT = 8765
DEFAULT_FILE = "вставка_от_димы.py"

def get_target_file():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.getenv("DIMA_VSCODE_TARGET", DEFAULT_FILE)

def log(message):
    with open("receiver_log.txt", "a") as logf:
        logf.write(f"[{datetime.now()}] {message}\n")

def start_receiver():
    sock = socket.socket()
    sock.bind(("localhost", PORT))
    sock.listen(1)
    print(f"🎧 Слушаю порт {PORT} для вставок от Димы...")
    log(f"Приёмник запущен на порту {PORT}")

    while True:
        conn, _ = sock.accept()
        data = conn.recv(8192).decode("utf-8").strip()
        target_file = get_target_file()
        if data:
            print(f"📝 Получено: {data}")
            log(f"Получено и вставлено в {target_file}: {data}")
            with open(target_file, "a") as f:
                f.write("\n" + data)
            print(f"✅ Вставлено в {target_file}")
        conn.close()

if __name__ == "__main__":
    start_receiver()
