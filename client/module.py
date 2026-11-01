"""클라이언트의 통신 기능입니다. 처음에는 main.py만 읽어도 됩니다."""

import queue
import socket
import threading


def connect_server(host, port):
    """서버에 접속합니다. 실패하면 None을 돌려줍니다."""
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.settimeout(3)
    try:
        connection.connect((host, port))
        connection.settimeout(None)
        return connection
    except OSError:
        print("[오류] 서버에 접속할 수 없습니다. 서버를 먼저 실행해 주세요.")
        connection.close()
        return None


def start_chat(connection):
    """키보드 입력과 서버의 메시지를 동시에 기다리기 시작합니다."""
    messages = queue.Queue()
    receiver = threading.Thread(
        target=_receive_messages, args=(connection, messages), daemon=True
    )
    keyboard = threading.Thread(target=_read_keyboard, args=(messages,), daemon=True)
    receiver.start()
    keyboard.start()
    return messages


def read_message(chat):
    """사용자가 입력한 한 줄을 돌려줍니다. Ctrl+C도 종료로 처리합니다."""
    try:
        return chat.get()
    except KeyboardInterrupt:
        return "/종료"


def send_message(connection, text):
    """한 줄을 보냅니다. 성공하면 True, 연결이 끊겼으면 False입니다."""
    try:
        connection.sendall((text + "\n").encode("utf-8"))
        return True
    except OSError:
        print("[안내] 연결이 끊겨 메시지를 보낼 수 없습니다.")
        return False


def disconnect(connection):
    """서버와의 연결을 닫습니다."""
    try:
        connection.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    connection.close()


def _read_keyboard(messages):
    try:
        while True:
            message = input()
            messages.put(message)
            if message == "/종료":
                return
    except EOFError:
        messages.put("/종료")


def _receive_messages(connection, messages):
    try:
        with connection.makefile("r", encoding="utf-8") as reader:
            for line in reader:
                print(line.rstrip("\n"), flush=True)
    except (OSError, UnicodeError):
        pass
    finally:
        print("[안내] 서버와의 연결이 끝났습니다.", flush=True)
        # 입력 중이어도 main.py의 반복문이 끝나도록 알려줍니다.
        messages.put("/종료")
