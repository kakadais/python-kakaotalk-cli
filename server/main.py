# 소켓 통신과 스레드 처리는 module.py에 들어 있습니다.
from module import start_server, wait_for_clients, close_server_waiting, relay_messages

host = "0.0.0.0"
port = 12345

print("=== 미니 카카오톡 서버 ===")
# 클라이언트의 접속을 받을 준비를 합니다.
server = start_server(host, port)

if server is not None:
    print("클라이언트 2명을 기다립니다.")
    # 두 사람이 연결될 때까지 이 함수에서 기다립니다.
    # 두 사람이 모이면 연결 정보를 room에 담고 다음 줄로 넘어갑니다.
    room = wait_for_clients(server)

    # 새로운 사람의 접속 대기만 끝냅니다.
    # 이미 접속한 두 사람의 대화용 연결은 유지됩니다.
    close_server_waiting(server)

    if room is not None:
        print("두 사람이 연결되었습니다. 대화를 전달합니다.")
        # 한 사람이 나갈 때까지 이 함수에서 메시지를 계속 전달합니다.
        relay_messages(room)

    # 대화가 끝났거나 접속 대기가 취소되면 실행됩니다.
    print("서버를 종료합니다.")
