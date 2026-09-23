import os
import sys
import ssl
import socket
import json
import yaml
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import urllib.request

WARN_DAYS = 30
CRIT_DAYS = 7


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def get_expiry(host, port, cafile=None, timeout=10):
    if cafile:
        # treat the file as a trusted CA (works for our self-signed mocks)
        ctx = ssl.create_default_context(cafile=cafile)
        ctx.check_hostname = False
    else:
        # real-world: verify against public CAs + check hostname
        ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert()
    return parsedate_to_datetime(cert["notAfter"])


def classify(days_left):
    if days_left <= 0:
        return "EXPIRED"
    if days_left <= CRIT_DAYS:
        return "CRITICAL"
    if days_left <= WARN_DAYS:
        return "WARN"
    return "OK"


def slack_alert(webhook, text):
    if not webhook:
        return
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def main():
    args = sys.argv[1:]
    config_path = "config.yaml"
    if args and args[0] == "--config":
        config_path = args[1]
        args = args[2:]
    cfg = load_config(config_path)
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")

    for entry in cfg.get("certs", []):
        name = entry["name"]
        try:
            expire_dt = get_expiry(
                entry["host"], entry.get("port", 443), cafile=entry.get("cafile")
            )
        except Exception as e:
            print(f"[ERROR] {name}: cannot read certificate: {e}")
            continue

        days_left = (expire_dt - datetime.now(timezone.utc)).total_seconds() / 86400
        status = classify(days_left)
        line = f"{status:<8} {name}: expires {expire_dt:%Y-%m-%d} ({days_left:.0f} days left)"
        print(line)

        if status != "OK":
            with open(cfg.get("alert_log", "cert_alerts.log"), "a") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")
            try:
                slack_alert(webhook, line)
            except Exception as e:
                print(f"  (slack alert failed: {e})")


if __name__ == "__main__":
    main()
