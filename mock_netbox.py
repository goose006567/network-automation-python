import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8001
TOKEN = "0123456789abcdef"

PREFIXES = [{"id": 1, "prefix": "10.0.0.0/24", "total": 256, "allocated": 3}]

IP_POOL = [
    {"id": 1, "address": "10.0.0.1", "dns_name": "web-01", "status": {"value": "active", "label": "Active"}},
    {"id": 2, "address": "10.0.0.2", "dns_name": "db-01", "status": {"value": "active", "label": "Active"}},
    {"id": 3, "address": "10.0.0.3", "dns_name": "app-01", "status": {"value": "dhcp", "label": "DHCP"}},
]

_next_id = 4


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[mock-netbox]", self.command, self.path, flush=True)

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        return self.headers.get("Authorization") == f"Token {TOKEN}"

    @staticmethod
    def _paginate(results):
        return {"count": len(results), "next": None, "previous": None, "results": results}

    def do_GET(self):
        if not self._auth_ok():
            self._send(401, {"detail": "Invalid token header. No credentials provided."})
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/ipam/ip-addresses/":
            results = IP_POOL
            if "address" in query:
                wanted = query["address"][0]
                results = [ip for ip in IP_POOL if ip["address"] == wanted]
            self._send(200, self._paginate(results))
        elif parsed.path == "/api/ipam/prefixes/":
            results = PREFIXES
            if "prefix" in query:
                wanted = query["prefix"][0]
                results = [p for p in PREFIXES if p["prefix"] == wanted]
            self._send(200, self._paginate(results))
        else:
            self._send(404, {"detail": "Not found."})

    def do_POST(self):
        if not self._auth_ok():
            self._send(401, {"detail": "Invalid token header. No credentials provided."})
            return
        if urlparse(self.path).path != "/api/ipam/ip-addresses/":
            self._send(404, {"detail": "Not found."})
            return
        global _next_id
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode() or "{}")
        address = body.get("address")
        if not address:
            self._send(400, {"detail": "address is required."})
            return
        if any(ip["address"] == address for ip in IP_POOL):
            self._send(409, {"detail": f"IP address {address} already exists."})
            return
        ip_obj = {
            "id": _next_id,
            "address": address,
            "dns_name": body.get("dns_name", ""),
            "status": body.get("status", {"value": "reserved", "label": "Reserved"}),
        }
        _next_id += 1
        IP_POOL.append(ip_obj)
        self._send(201, ip_obj)


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"[mock-netbox] API server on {HOST}:{PORT} (token={TOKEN})")
    server.serve_forever()


if __name__ == "__main__":
    main()
