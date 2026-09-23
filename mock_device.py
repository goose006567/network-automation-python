import paramiko
import socket
import threading

HOST = "127.0.0.1"
PORT = 2222
USERNAME = "admin"
PASSWORD = "secret"

PROMPT = "R1#"

BASE_CONFIG = """! mock device running-config - baseline
hostname R1
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.0
!
interface GigabitEthernet0/1
 ip address 10.0.1.1 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 10.0.0.254
!
end"""

DRIFTED_CONFIG = """! mock device running-config - CHANGED BY AN ENGINEER
hostname R1
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.0
!
interface GigabitEthernet0/1
 ip address 10.0.1.1 255.255.255.0
!
interface Vlan100
 ip address 172.16.0.1 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 10.0.0.254
!
end"""

CONFIGS = [BASE_CONFIG, DRIFTED_CONFIG]

_lock = threading.Lock()
_session_count = 0


def next_config():
    global _session_count
    with _lock:
        config = CONFIGS[_session_count % len(CONFIGS)]
        _session_count += 1
        return config


class MockServer(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if username == USERNAME and password == PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def get_allowed_auths(self, username):
        return "password"


def client_thread(conn, addr):
    session_config = next_config()
    try:
        transport = paramiko.Transport(conn)
        transport.add_server_key(paramiko.RSAKey.generate(2048))
        transport.start_server(server=MockServer())
        chan = transport.accept(20)
        if chan is None:
            return
        chan.send(PROMPT + "\r\n")
        buf = b""
        while True:
            data = chan.recv(1024)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                print("[mock]", repr(raw), flush=True)
                cmd = raw.strip()
                if not cmd:
                    chan.send(PROMPT + "\r\n")
                elif b"show running-config" in cmd:
                    chan.send(
                        raw
                        + b"\r\n"
                        + session_config.encode()
                        + b"\r\n"
                        + PROMPT.encode()
                        + b"\r\n"
                    )
                elif b"terminal length" in cmd or b"terminal width" in cmd:
                    chan.send(raw + b"\r\n" + PROMPT.encode() + b"\r\n")
                else:
                    chan.send(raw + b"\r\n" + PROMPT.encode() + b"\r\n")
    except Exception as e:
        print(f"[mock-device] connection error: {e}")
    finally:
        try:
            transport.close()
        except Exception:
            pass


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)
    print(f"[mock-device] SSH server on {HOST}:{PORT} (user={USERNAME} pass={PASSWORD})")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
