import ssl
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(sys.argv[1])
    cert = sys.argv[2]
    key = sys.argv[3]
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server = HTTPServer((HOST, port), Handler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print(f"[mock-tls] https server on {HOST}:{port} (cert={cert})")
    server.serve_forever()


if __name__ == "__main__":
    main()
