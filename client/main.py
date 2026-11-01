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

        # 아무 내용 없이 Enter만 누른 경우에는 보내지 않습니다.
        if message != "":
            # 예: "민수" + ": " + "안녕!"을 붙이면 "민수: 안녕!"이 됩니다.
            text = nickname + ": " + message

            # 서버에 메시지를 보내고 전송 결과를 변수에 저장합니다.
            # 성공하면 True, 실패하면 False가 돌아옵니다.
            send_result = send_message(connection, text)

            # 전송에 실패하면 while 반복문을 끝냅니다.
            if send_result == False:
                break

    disconnect(connection)
    print("대화를 종료했습니다.")
