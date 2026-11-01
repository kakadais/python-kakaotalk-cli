# 소켓 통신과 스레드 처리는 module.py에 들어 있습니다.
from module import start_server, wait_for_clients, close_server, relay_messages

host = "0.0.0.0"
port = 12345

print("=== 미니 카카오톡 서버 ===")
server = start_server(host, port)

if server is not None:
    print("클라이언트 2명을 기다립니다.")
    room = wait_for_clients(server)
    close_server(server)

    if room is not None:
        print("두 사람이 연결되었습니다. 대화를 전달합니다.")
        relay_messages(room)

    print("서버를 종료합니다.")
