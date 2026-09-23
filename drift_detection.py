import os
import re
import sys
import yaml
import difflib
from datetime import datetime
from netmiko import ConnectHandler

PROMPT_PATTERN = re.compile(r"^\S+#\s*$")


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_current_config(device):
    conn = ConnectHandler(
        device_type=device["device_type"],
        host=device["host"],
        username=device["username"],
        password=device["password"],
        port=device.get("port", 22),
        secret=device.get("secret"),
    )
    output = conn.send_command("show running-config", read_timeout=30)
    conn.disconnect()
    return output


def normalize(text):
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or PROMPT_PATTERN.match(s):
            continue
        lines.append(s)
    return lines


def find_baseline(backup_dir, device_name):
    if not os.path.isdir(backup_dir):
        return None
    candidates = sorted(
        f for f in os.listdir(backup_dir)
        if f.startswith(device_name + "_") and f.endswith(".txt")
    )
    return os.path.join(backup_dir, candidates[-1]) if candidates else None


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(config_path)
    date_str = datetime.now().strftime("%Y-%m-%d")

    for device in cfg["devices"]:
        current = normalize(fetch_current_config(device))
        baseline_path = find_baseline(cfg["backup_dir"], device["name"])

        if baseline_path is None:
            filename = cfg["filename_format"].format(name=device["name"], date=date_str)
            os.makedirs(cfg["backup_dir"], exist_ok=True)
            with open(os.path.join(cfg["backup_dir"], filename), "w") as f:
                f.write("\n".join(current) + "\n")
            print(f"[BASELINE] {device['name']}: no previous backup, baseline saved")
            continue

        baseline = normalize(open(baseline_path).read())
        diff = difflib.unified_diff(
            baseline,
            current,
            fromfile=f"{device['name']} (baseline)",
            tofile=f"{device['name']} (current)",
            lineterm="",
        )
        diff_lines = list(diff)

        if diff_lines:
            print(f"[DRIFT] {device['name']}: config changed")
            for line in diff_lines:
                print(f"  {line}")
        else:
            print(f"[OK]   {device['name']}: no drift")


if __name__ == "__main__":
    main()
