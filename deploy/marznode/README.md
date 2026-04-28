# Aegis Panel — standalone marznode installer (D.2)

Provisions a **data-plane-only** VPS that runs `marznode` + `xray-core`
and accepts gRPC connections from a remote control plane (the host where
`deploy/install/install.sh` ran).

This directory is the operator path for **scenario S3** in
`docs/ai-cto/SPEC-deploy.md` §"场景矩阵" — 1 control plane + N nodes.
For S1 / S2 (same-host marznode) use `deploy/install/install.sh
--marznode same-host` instead; this directory is only for nodes whose
panel lives elsewhere.

License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
(<https://github.com/marzneshin/marzneshin>). See `../../NOTICE.md`.

---

## Prerequisites

1. **Control plane already running and reachable** — the URL given to
   `--control-plane` must resolve and accept HTTPS from this VPS. Verify
   before running:
   ```bash
   curl -sI https://<control-plane>/api/system/info
   ```
2. **OS** — Ubuntu 22.04 / 24.04 LTS or Debian 12 (tier-1, same as D.1).
3. **Hardware floors** — RAM >= 1 GiB, vCPU >= 1, free disk on
   `/var/lib` >= 5 GiB. (Lighter than the control plane: no DB, no UI.)
4. **Dependencies** — `docker` (>= 24), `docker compose` v2 plugin,
   `curl`, `openssl`. The script detects and prints `apt-get install`
   hints if anything is missing; it does NOT auto-install.

---

## Cert-mode flows

The panel and node authenticate each other with a shared TLS cert.
Pick one of two delivery modes:

### A. `--cert-mode bootstrap` (recommended for hand-rolled installs)

The panel mints a one-time bootstrap token in **Nodes > New > Generate
bootstrap token**; copy it and pass to `install-node.sh`. The script
fetches the cert via:

```
GET https://<control-plane>/api/nodes/bootstrap?token=<one-time-token>
```

Token TTL is 5 minutes server-side. Used once, then revoked.

```bash
sudo ./install-node.sh \
  --control-plane panel.example.com \
  --node-name node-tokyo-01 \
  --cert-mode bootstrap \
  --cert-token tok_abcdef0123456789
```

### B. `--cert-mode file` (recommended for Ansible / pre-provisioned)

The cert is already on disk (e.g. delivered via Ansible Vault, scp from
a secure jump host, or rsync from a config repo). Pass the path:

```bash
sudo ./install-node.sh \
  --control-plane panel.example.com \
  --node-name node-singapore-01 \
  --cert-mode file \
  --cert-file ./marznode-cert.pem
```

The file is copied into `/opt/aegis-marznode/marznode-cert.pem`
(mode 600). The original on the install path is **not** removed.

---

## After install — register the node in the panel

`install-node.sh` does NOT call the panel API to register the node; that
keeps the install path AGPL-compliant and source-disclosure free from
panel auth quirks. Register manually:

1. Open `https://<control-plane>/<DASHBOARD_PATH>/nodes` in the panel UI.
2. Click **Add node**.
3. Fill:
   - **Name** — exact match to `--node-name` (the panel prints a hint
     if mismatch is detected during the gRPC handshake).
   - **Address** — public IP of the node VPS.
   - **Port** — value of `--grpc-port` (default `62051`).
4. The panel attempts a gRPC handshake immediately. Expected: green
   indicator within 30 s. If red, check the troubleshooting table below.

---

## Operator-side runbook (S3 — 2-node provisioning ≤ 30 min)

This satisfies AC-D.2.1 / AC-D.2.3 in SPEC-deploy.md. For two fresh
nodes, the path is roughly:

| Step | What | Time |
|---|---|---|
| 1 | SSH into node A, `git clone` repo, run `install-node.sh` (cert-mode bootstrap) | 5 min |
| 2 | Register node A in panel UI | 1 min |
| 3 | `ufw` allow 22 + gRPC port (limit source to control-plane IP) | 2 min |
| 4 | Repeat 1-3 for node B | 8 min |
| 5 | Verify subscription URL routes traffic through both nodes | 4 min |

Total: ~20-25 min for two nodes. The Ansible playbook in D.3 (next PR)
parallelizes steps 1-4 and brings this under 10 min.

To add a 3rd node later: re-run `install-node.sh` on the new VPS — no
control-plane reconfiguration needed. (AC-D.2.* "add 3rd node" path.)

---

## Reconnect behavior (AC-D.2.2)

The cert lives on disk at `/opt/aegis-marznode/marznode-cert.pem`. When
the control plane restarts, the panel re-initiates the gRPC handshake
using the same cert; the node accepts and resumes. No re-bootstrap, no
token re-issue. Verify with:

```bash
sudo systemctl restart docker  # or just restart the panel container
# wait ~30s, then check the node green status in the panel
```

If `restart: always` (set in our compose) the marznode container also
auto-recovers if it crashes.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `step 1: dependency missing: docker compose` | v1 standalone instead of v2 plugin | `apt-get install docker-compose-plugin` |
| `step 5 FATAL: bootstrap GET ... failed` | Control plane unreachable, token expired (5-min TTL), or `/api/nodes/bootstrap` not enabled on panel version | Re-issue token in panel; verify `curl -sI https://<control-plane>` returns 200; if panel is older than v0.2.0 use `--cert-mode file` instead |
| `step 5 FATAL: not a PEM cert` | Token re-used, panel returned an error page | Generate fresh token; ensure URL has no trailing whitespace |
| `step 4 FATAL: gRPC port ... occupied` | Another marznode or unrelated service on `62051` | Pick a free port via `--grpc-port` and update panel registration to match |
| `step 8 gRPC listener wait failed` | Container crashed mid-boot; check `docker logs aegis-marznode` | Usually a cert/path mismatch — confirm `/opt/aegis-marznode/marznode-cert.pem` exists and mode 600 |
| Panel shows node red, "connection refused" | Firewall blocks the port from control-plane source | `sudo ufw allow from <control-plane-ip> to any port 62051 proto tcp` |
| Panel shows node red, "TLS handshake failed" | Cert mismatch (different from what panel issued) | Re-run with `--cert-mode bootstrap` and a fresh token; the new cert overwrites the old |
| Panel shows node red, NAT/CGNAT VPS | Node has no public IP | Use a CF Tunnel (D.4) for the gRPC port — out of scope for D.2 |

Live logs:

```bash
sudo docker compose -f /path/to/repo/deploy/marznode/docker-compose.yml \
     --env-file /opt/aegis-marznode/.env logs -f marznode
```

---

## Idempotency

`install-node.sh` writes sentinel files
`/opt/aegis-marznode/.install-step-{1..8}.done`. Re-running on the same
VPS skips completed steps. To force a full redo:

```bash
sudo rm -f /opt/aegis-marznode/.install-step-*.done
sudo ./install-node.sh --control-plane ... --node-name ... --cert-mode ...
```

Same flag set + same `.env` -> no diff. Different flag set ->
`/opt/aegis-marznode/.env` is rewritten on step 6 (and the cert is
re-fetched on step 5 if the cert sentinel is removed).

---

## Uninstall

```bash
sudo docker compose -f deploy/marznode/docker-compose.yml down -v
sudo rm -rf /opt/aegis-marznode/
# Remove the node from the panel UI as well — Nodes > <node-name> > Delete.
```

The `down -v` removes the marznode container + named volumes. The
`/opt/aegis-marznode/` rmrf nukes the .env, sentinel files, cert, and
xray data dir. The cert is now revoked-by-loss; if you redeploy on the
same VPS later, fetch a new bootstrap token from the panel.

---

## Cross-references

- `deploy/install/install.sh` — D.1 single-node installer; for same-host
  marznode use `--marznode same-host` there instead of running this
  directory.
- `deploy/cloudflare/install-tunnel.sh` — D.4 CF Tunnel; only relevant
  for the panel host, not the data-plane node.
- `docs/ai-cto/SPEC-deploy.md` §"D.2 — 独立 marznode" — authoritative
  acceptance criteria.
