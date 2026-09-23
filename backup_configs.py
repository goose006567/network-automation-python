import os
import sys
import yaml
from datetime import datetime
from netmiko import ConnectHandler

BACKUP_CMD = "show running-config"

def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

def backup_one_device(device, backup_dir, date_str, filename_format):
    try:
        conn = ConnectHandler(
            device_type=device["device_type"],
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("port", 22),
            secret=device.get("secret"),
        )
        output = conn.send_command(BACKUP_CMD, read_timeout=30)
        conn.disconnect()

        os.makedirs(backup_dir, exist_ok=True)
        filename = os.path.join(
            backup_dir, filename_format.format(name=device["name"], date=date_str)
        )
        with open(filename, "w") as f:
            f.write(output)

        print(f"[OK] {device['name']} backed up -> {filename}")
    except Exception as e:
        print(f"[FAIL] {device['name']}: {e}")

def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(config_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
    for device in cfg["devices"]:
        backup_one_device(device, cfg["backup_dir"], date_str, cfg["filename_format"])

if __name__ == "__main__":
    main()