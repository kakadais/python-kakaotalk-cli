"""서버의 통신 기능입니다. 처음에는 main.py만 읽어도 됩니다."""

import queue
import socket
import threading


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
                messages.put((connection, line.rstrip("\n")))
    except (OSError, UnicodeError):
        pass
    finally:
        finished.set()
        messages.put((connection, None))


def _send_text(connection, text):
    connection.sendall((text + "\n").encode("utf-8"))


def _close_clients(clients):
    for connection in clients:
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        connection.close()
