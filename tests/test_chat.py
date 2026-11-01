"""실제 main.py를 실행하는 통신 검사입니다. 수업에서는 생략해도 됩니다."""

from datetime import datetime
import json
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Program:
    def __init__(self, folder, root=ROOT):
        self.lines = queue.Queue()
        self.output = []
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(root / folder / "main.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        self.reader = threading.Thread(target=self._read_output, daemon=True)
        self.reader.start()

    def _read_output(self):
        for line in self.process.stdout:
            self.output.append(line)
            self.lines.put(line)

    def send(self, text):
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()

    def expect(self, text):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                line = self.lines.get(timeout=0.1)
            except queue.Empty:
                continue
            if text in line:
                return
        raise AssertionError("출력에 없음: " + text + "\n" + "".join(self.output))

    def wait(self):
        result = self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        if result != 0:
            raise AssertionError("비정상 종료: " + "".join(self.output))

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.programs = []
        self.temporary = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temporary.name)
        shutil.copytree(
            ROOT / "server",
            self.test_root / "server",
            ignore=shutil.ignore_patterns("__pycache__", "log.json", "log.json.tmp"),
        )
        self.log_path = self.test_root / "server" / "log.json"

    def tearDown(self):
        for program in self.programs:
            program.close()
        self.temporary.cleanup()

    def start(self, folder):
        root = self.test_root if folder == "server" else ROOT
        program = Program(folder, root)
        self.programs.append(program)
        return program

    def start_server(self):
        server = self.start("server")
        server.expect("클라이언트 2명을 기다립니다.")
        return server

    def start_client(self, nickname):
        client = self.start("client")
        client.send(nickname)
        return client

    def start_pair(self):
        server = self.start_server()
        first = self.start_client("민수")
        first.expect("상대방의 접속을 기다립니다.")
        second = self.start_client("수지")
        first.expect("1:1 대화를 시작합니다.")
        second.expect("1:1 대화를 시작합니다.")
        return server, first, second

    def test_chat_and_quit(self):
        server = self.start_server()
        first = self.start_client("민수")
        first.expect("상대방의 접속을 기다립니다.")
        first.send("먼저 보낸 메시지")
        second = self.start_client("수지")
        first.expect("1:1 대화를 시작합니다.")
        second.expect("1:1 대화를 시작합니다.")
        second.expect("민수: 먼저 보낸 메시지")

        first.send("")
        first.send("안녕! 😊")
        first.send("두 번째 메시지")
        second.expect("민수: 안녕! 😊")
        second.expect("민수: 두 번째 메시지")
        second.send("반가워요! " + "가" * 5000)
        first.expect("수지: 반가워요! " + "가" * 5000)

        first.send("/종료")
        for program in (first, second, server):
            program.wait()

        history = json.loads(self.log_path.read_text(encoding="utf-8"))
        self.assertEqual([entry["message"] for entry in history], [
            "민수: 먼저 보낸 메시지",
            "민수: 안녕! 😊",
            "민수: 두 번째 메시지",
            "수지: 반가워요! " + "가" * 5000,
        ])
        for entry in history:
            self.assertIsNotNone(datetime.fromisoformat(entry["time"]).tzinfo)
        self.assertIn("안녕! 😊", self.log_path.read_text(encoding="utf-8"))

    def test_client_leaves_while_waiting(self):
        server = self.start_server()
        client = self.start_client("")
        client.expect("상대방의 접속을 기다립니다.")
        client.send("기다리는 중입니다.")
        client.send("/종료")
        client.wait()
        server.wait()
        history = json.loads(self.log_path.read_text(encoding="utf-8"))
        self.assertEqual([entry["message"] for entry in history], ["익명: 기다리는 중입니다."])

    def test_log_keeps_messages_after_server_restart(self):
        for message in ("첫 대화", '다음 대화: "한글" 😊 \\'):
            server, first, second = self.start_pair()
            first.send(message)
            second.expect("민수: " + message)
            first.send("/종료")
            for program in (server, first, second):
                program.wait()
        history = json.loads(self.log_path.read_text(encoding="utf-8"))
        self.assertEqual([entry["message"] for entry in history], [
            "민수: 첫 대화",
            '민수: 다음 대화: "한글" 😊 \\',
        ])

    def test_messages_from_both_clients_are_all_logged(self):
        server, first, second = self.start_pair()
        first_messages = ["민수의 메시지 " + str(number) for number in range(10)]
        second_messages = ["수지의 메시지 " + str(number) for number in range(10)]
        first.send("\n".join(first_messages))
        second.send("\n".join(second_messages))
        for message in first_messages:
            second.expect("민수: " + message)
        for message in second_messages:
            first.expect("수지: " + message)
        first.send("/종료")
        for program in (server, first, second):
            program.wait()

        history = json.loads(self.log_path.read_text(encoding="utf-8"))
        expected = ["민수: " + message for message in first_messages]
        expected += ["수지: " + message for message in second_messages]
        self.assertCountEqual([entry["message"] for entry in history], expected)

    def test_invalid_log_is_preserved_and_chat_continues(self):
        original = "잘못된 JSON 파일"
        self.log_path.write_text(original, encoding="utf-8")
        server, first, second = self.start_pair()
        first.send("저장이 안 되어도 대화합니다.")
        server.expect("log.json에 대화를 기록할 수 없습니다:")
        second.expect("민수: 저장이 안 되어도 대화합니다.")
        first.send("/종료")
        for program in (server, first, second):
            program.wait()
        self.assertEqual(self.log_path.read_text(encoding="utf-8"), original)

    def test_file_error_does_not_stop_chat(self):
        self.log_path.mkdir()
        server, first, second = self.start_pair()
        first.send("파일 오류가 있어도 대화합니다.")
        server.expect("log.json에 대화를 기록할 수 없습니다:")
        second.expect("민수: 파일 오류가 있어도 대화합니다.")
        first.send("/종료")
        for program in (server, first, second):
            program.wait()
        self.assertTrue(self.log_path.is_dir())

    def test_server_stops_while_clients_wait_for_input(self):
        server, first, second = self.start_pair()
        server.process.send_signal(signal.SIGINT)
        for program in (server, first, second):
            program.wait()

    def test_client_reports_missing_server(self):
        client = self.start_client("민수")
        client.expect("서버에 접속할 수 없습니다.")
        client.wait()

    def test_server_reports_port_in_use(self):
        self.start_server()
        duplicate = self.start("server")
        duplicate.expect("서버를 열 수 없습니다:")
        duplicate.wait()


if __name__ == "__main__":
    unittest.main()
