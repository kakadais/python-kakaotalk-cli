# 메시지를 주고받는 자세한 방법은 module.py에 들어 있습니다.
from module import connect_server, start_chat, read_message, send_message, disconnect

host = "127.0.0.1"
port = 12345

print("=== 미니 카카오톡 ===")
nickname = input("닉네임: ")
if nickname == "":
    nickname = "익명"

connection = connect_server(host, port)

if connection is not None:
    print("메시지를 입력하고 Enter를 누르세요. 끝내려면 /종료를 입력하세요.")
    chat = start_chat(connection)

    while True:
        message = read_message(chat)

        if message == "/종료":
            break

        if message != "":
            text = nickname + ": " + message
            if not send_message(connection, text):
                break

    disconnect(connection)
    print("대화를 종료했습니다.")
