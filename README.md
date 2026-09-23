# Project 1: Network Automation with Python

Four scripts that automate day-to-day network chores, all tested end-to-end against **local mock servers** (no internet, no real gear needed).

## Scripts

| Script | What it does | How to run |
|--------|--------------|------------|
| `backup_configs.py` | SSH (Netmiko/Paramiko) into devices in `config.yaml`, pull `show running-config`, save timestamped copies to `backups/` | `python backup_configs.py config.local.yaml` |
| `drift_detection.py` | Pulls the current config, diffs it against the latest backup using `difflib.unified_diff`, flags DRIFT or OK | `python drift_detection.py config.local.yaml` |
| `netbox_ipam.py` | NetBox REST API via stdlib `urllib`: list IPs, check prefix free space, reserve an address | `python netbox_ipam.py list` |
| `cert_expiry.py` | Reads TLS cert `notAfter` over the socket, classifies OK/WARN/CRITICAL/EXPIRED, logs alerts + optional Slack | `python cert_expiry.py` |

## Files / structure

```
01-network-automation-with-python/
├── backup_configs.py     # step 1: SSH config backups
├── drift_detection.py    # step 2: drift detection (baseline vs current)
├── netbox_ipam.py        # step 3: NetBox REST API (IPAM)
├── cert_expiry.py        # step 4: SSL certificate expiry monitoring
├── config.yaml           # devices + netbox + certs config (real-world targets)
├── config.local.yaml     # test config pointing at the mock servers
├── requirements.txt
├── mock_device.py        # fake router: SSH server that answers "show running-config"
├── mock_netbox.py        # fake NetBox: HTTP API at /api/ipam/...
├── mock_tls_server.py    # fake HTTPS server serving a cert you pass in
├── certs/                # self-signed test certs (365d / 10d / 3d) - regenerate, do not commit
├── backups/              # generated backups (not committed)
└── .venv/                # Python 3.12 env (not committed)
```

## Getting it running

```bash
python3.12 -m venv .venv
.venv/bin/pip install PyYAML paramiko netmiko

# terminal 1: fake router
.venv/bin/python mock_device.py

# terminal 2: backup + drift detection
.venv/bin/python backup_configs.py config.local.yaml
.venv/bin/python drift_detection.py config.local.yaml
```

NetBox IPAM (fake NetBox on port 8001):

```bash
.venv/bin/python mock_netbox.py
.venv/bin/python netbox_ipam.py list
.venv/bin/python netbox_ipam.py check-prefix 10.0.0.0/24
.venv/bin/python netbox_ipam.py reserve 10.0.0.10
```

SSL expiry (3 fake HTTPS servers, one per cert lifespan — `cert_expiry.py` then sees OK / WARN / CRITICAL):

```bash
.venv/bin/python mock_tls_server.py 8443 certs/ok.crt   certs/ok.key
.venv/bin/python mock_tls_server.py 8444 certs/warn.crt certs/warn.key
.venv/bin/python mock_tls_server.py 8445 certs/crit.crt certs/crit.key
.venv/bin/python cert_expiry.py
```

Regenerate the test certs (they contain throwaway private keys, so they are gitignored):

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=localhost" -keyout certs/ok.key   -out certs/ok.crt
openssl req -x509 -newkey rsa:2048 -nodes -days 10  -subj "/CN=localhost" -keyout certs/warn.key -out certs/warn.crt
openssl req -x509 -newkey rsa:2048 -nodes -days 3   -subj "/CN=localhost" -keyout certs/crit.key -out certs/crit.crt
```

## Things learned along the way

- `netmiko.ConnectHandler` needs the right `device_type` (e.g. `cisco_ios`) — it handles enable mode, paging and prompts for you; Paramiko is the raw SSH layer underneath.
- Real SSH servers must answer a **PTY request** and **echo commands** — that's why the mock replies to `terminal width/length` with the command echoed back.
- Drift detection compares the *current* config to the *latest saved backup*; normalization strips whitespace and the trailing prompt so it never triggers false drift.
- NetBox API returns paginated JSON (`count`, `next`, `results`); follow `next` until `null`.
- `SSLSocket.getpeercert()` returns `{}` unless the chain verifies — treat the self-signed cert as a trusted CA (`cafile`) for the mocks.
- Timezone-aware expiry math: `(expire - now).total_seconds()/86400`, not `.days`.

## Resume-ready summary

> Wrote Python scripts to automate configuration backups and detect configuration drift across network devices. Used REST APIs and NetBox for IP address management and infrastructure documentation. Automated SSL certificate expiry monitoring to prevent unplanned outages.
