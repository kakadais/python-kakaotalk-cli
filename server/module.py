"""서버의 통신 기능입니다. 처음에는 main.py만 읽어도 됩니다."""

from datetime import datetime
import json
from pathlib import Path
import queue
import socket
import threading


LOG_PATH = Path(__file__).with_name("log.json")
LOG_LOCK = threading.Lock()


def start_server(host, port):
    """접속을 받을 서버를 만듭니다. 실패하면 None을 돌려줍니다."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(0.2)
    try:
        server.bind((host, port))
        server.listen(2)
        return server
    except OSError as error:
        print("[오류] 서버를 열 수 없습니다:", error)
        server.close()
        return None


def wait_for_clients(server):
    """두 사람을 기다리고, 대화에 필요한 정보를 묶어서 돌려줍니다."""
    clients = []
    messages = queue.Queue()
    finished = threading.Event()

    try:
        while len(clients) < 2:
            if finished.is_set():
                print("기다리던 클라이언트가 나갔습니다.")
                break
            try:
                connection, address = server.accept()
            except socket.timeout:
                continue

            clients.append(connection)
            print(str(len(clients)) + "번 클라이언트가 접속했습니다.")
            if len(clients) == 1:
                _send_text(connection, "[안내] 상대방의 접속을 기다립니다.")
            thread = threading.Thread(
                target=_receive_messages,
                args=(connection, messages, finished),
                daemon=True,
            )
            thread.start()

        if len(clients) == 2:
            return clients, messages
    except KeyboardInterrupt:
        print("\n서버를 중지합니다.")
    except OSError as error:
        print("[오류] 접속을 기다릴 수 없습니다:", error)

    _close_clients(clients)
    return None


def relay_messages(room):
    """받은 메시지를 상대방에게 전달합니다. 한 명이 나가면 끝납니다."""
    clients, messages = room
    try:
        for connection in clients:
            _send_text(connection, "[안내] 1:1 대화를 시작합니다. /종료로 나갈 수 있습니다.")

        while True:
            sender, message = messages.get()
            if message is None:
                break
            for connection in clients:
                if connection is not sender:
                    _send_text(connection, message)
    except KeyboardInterrupt:
        print("\n서버를 중지합니다.")
    except OSError:
        print("클라이언트와의 연결이 끊어졌습니다.")
    finally:
        _close_clients(clients)


def close_server_waiting(server):
    """새로운 접속 대기만 끝냅니다. 이미 연결된 두 사람은 계속 대화합니다."""
    server.close()


def _receive_messages(connection, messages, finished):
    # 한 줄씩 읽으면 한글이나 메시지가 여러 조각으로 도착해도 처리됩니다.
    try:
        with connection.makefile("r", encoding="utf-8") as reader:
            for line in reader:
                message = line.rstrip("\n")
                _save_message(message)
                messages.put((connection, message))
    except (OSError, UnicodeError):
        pass
    finally:
        finished.set()
        messages.put((connection, None))


def _save_message(message):
    """받은 메시지를 시각과 함께 server/log.json에 이어서 기록합니다."""
    # 두 클라이언트가 동시에 보내도 한 번에 한 메시지씩 파일을 수정합니다.
    with LOG_LOCK:
        try:
            history = []
            if LOG_PATH.exists():
                with LOG_PATH.open("r", encoding="utf-8") as file:
                    history = json.load(file)
            if not isinstance(history, list):
                raise ValueError("log.json의 내용은 JSON 배열이어야 합니다.")

            history.append({
                "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                "message": message,
            })

            # 먼저 임시 파일에 쓰고 교체해 기존 기록이 쓰는 도중 손상되지 않게 합니다.
            temporary_path = LOG_PATH.with_name("log.json.tmp")
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(history, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(LOG_PATH)
        except (OSError, ValueError) as error:
            # 기록에 실패하더라도 채팅은 계속하고 기존 기록은 유지합니다.
            print("[오류] log.json에 대화를 기록할 수 없습니다:", error, flush=True)


def _send_text(connection, text):
    connection.sendall((text + "\n").encode("utf-8"))


def _close_clients(clients):
    for connection in clients:
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        connection.close()
