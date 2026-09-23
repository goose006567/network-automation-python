import sys
import json
import yaml
import urllib.request
import urllib.parse
import urllib.error


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def api_request(method, url, token, params=None, body=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("detail", e.reason)
        except Exception:
            detail = e.reason
        return e.code, {"error": detail}


def act_list(base, token):
    url = base + "/api/ipam/ip-addresses/"
    print(f"{'ADDRESS':<18}{'DNS NAME':<26}STATUS")
    print("-" * 50)
    while url:
        status, data = api_request("GET", url, token)
        if status != 200:
            print(f"[!] {data.get('error')}")
            return
        for ip in data.get("results", []):
            dns = ip.get("dns_name") or "-"
            stat = ip.get("status", {}).get("label", "?")
            print(f"{ip['address']:<18}{dns:<26}{stat}")
        url = data.get("next")
    print()


def act_check_prefix(base, token, prefix):
    url = base + "/api/ipam/prefixes/"
    status, data = api_request("GET", url, token, params={"prefix": prefix})
    if status != 200:
        print(f"[!] {data.get('error')}")
        return
    results = data.get("results", [])
    if not results:
        print(f"[!] prefix {prefix} not found")
        return
    p = results[0]
    total = p.get("total", 0)
    allocated = p.get("allocated", 0)
    print(f"prefix {p['prefix']}: {allocated}/{total} used -> {total - allocated} free")


def act_reserve(base, token, address):
    url = base + "/api/ipam/ip-addresses/"
    status, data = api_request(
        "POST",
        url,
        token,
        body={
            "address": address,
            "status": {"value": "reserved", "label": "Reserved"},
            "dns_name": "",
        },
    )
    if status in (200, 201):
        print(f"[OK] reserved {data['address']} (id={data['id']})")
    else:
        print(f"[!] {data.get('error')}")


def main():
    args = sys.argv[1:]
    config_path = "config.yaml"
    if args and args[0] == "--config":
        config_path = args[1]
        args = args[2:]
    cfg = load_config(config_path)
    base = cfg["netbox"]["url"]
    token = cfg["netbox"]["token"]
    action = args[0] if args else "list"

    if action == "list":
        act_list(base, token)
    elif action == "check-prefix":
        if len(args) < 2:
            print("usage: netbox_ipam.py check-prefix <prefix>")
            return
        act_check_prefix(base, token, args[1])
    elif action == "reserve":
        if len(args) < 2:
            print("usage: netbox_ipam.py reserve <address>")
            return
        act_reserve(base, token, args[1])
    else:
        print("usage: netbox_ipam.py [list | check-prefix <prefix> | reserve <address>]")


if __name__ == "__main__":
    main()
