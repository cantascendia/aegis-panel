# Aegis Panel — Ansible multi-node deployment (D.3)

This directory provisions an Aegis Panel control plane plus N marznode data plane
hosts from one operator workstation. Backed by `docs/ai-cto/SPEC-deploy.md` §"Ansible
职责(D.3,多节点)" and acceptance criteria AC-D.3.1..AC-D.3.4.

## What this delivers

| Layer | Role | What it does |
|---|---|---|
| Every host | `roles/common` | Docker CE + compose v2 (apt, NOT snap), ufw, fail2ban, `aegis` system user, `/opt/aegis` dir tree |
| Control plane | `roles/marzneshin` | git clone, render `.env`, invoke `deploy/install/install.sh` (D.1), optionally chain `deploy/cloudflare/install-tunnel.sh` (D.4), install `marzneshin-panel.service` |
| Data plane | `roles/marznode` | git clone, distribute mTLS cert from Ansible Vault, invoke `deploy/marznode/install-node.sh` (D.2), install `marznode-node.service` |

Sibling work referenced by these roles:

- D.1 — `deploy/install/install.sh` and `deploy/compose/docker-compose.prod.yml` (PR #95, merged)
- D.2 — `deploy/marznode/install-node.sh` (sibling PR `feat/deploy-d2-marznode-install`, in flight)
- D.4 — `deploy/cloudflare/install-tunnel.sh` (PR #94, merged)

If D.2 has not landed by the time you run this, the `marznode` role will fail at
the `install-node.sh` step. Stub the script or re-run after the merge.

## Prerequisites

On the **operator workstation** (the laptop you run `ansible-playbook` from):

- Ansible >= 2.16 (`pipx install --include-deps ansible`)
- `community.general` collection (`ansible-galaxy collection install community.general`)
- SSH access to every host in inventory, keys not passwords
- For Cloudflare: `CF_API_TOKEN` exported (Tunnel:Edit + DNS:Edit + Access:Edit; see `deploy/cloudflare/README.md`)

On every **target host**:

- Ubuntu 22.04 / 24.04 LTS or Debian 12 (other distros are rejected by `roles/common`)
- 2+ vCPU, 2 GiB RAM minimum (4 GiB recommended on the control plane)
- 20 GiB free under `/var/lib`
- Reachable on TCP/22 from your workstation

## Inventory walkthrough

Start from `inventory.example.yml`:

```bash
cp deploy/ansible/inventory.example.yml deploy/ansible/inventory.yml
$EDITOR deploy/ansible/inventory.yml
```

Required edits:

- `aegis_repo_tag` — version to pin (e.g. `v0.2.0`); use a tag in production
- `aegis_domain` — public FQDN that resolves to the control plane host
- `control_plane.hosts.<name>.ansible_host` — public IP of the panel host
- `data_plane.hosts.<name>.ansible_host` — public IP of each marznode host
- `data_plane.hosts.<name>.marznode_id` — unique integer per node

Optional:

- `cf_tunnel_enabled: true` to chain into Cloudflare Tunnel install
- `aegis_admin_username` / `aegis_admin_password` — pre-set initial admin
  creds; leave blank to let `install.sh` generate randoms

## Vault setup (recommended for marznode certs)

The `marznode` role expects mTLS material to come from Ansible Vault. Generate
it once on the workstation, encrypt, and reference from inventory:

```bash
# Generate a CA and per-node cert pair however you like — one common path:
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt -days 3650 -nodes \
    -subj "/CN=Aegis Marznode CA"
openssl req -newkey rsa:4096 -keyout node-tokyo.key -out node-tokyo.csr -nodes \
    -subj "/CN=node-tokyo"
openssl x509 -req -in node-tokyo.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out node-tokyo.crt -days 365

# Encrypt into a per-host vault file
ansible-vault create deploy/ansible/host_vars/node-tokyo/vault.yml
# Inside the editor, paste:
#   marznode_cert_pem: |
#     -----BEGIN CERTIFICATE-----
#     ...contents of node-tokyo.crt...
#     -----END CERTIFICATE-----
#   marznode_cert_key_pem: |
#     -----BEGIN PRIVATE KEY-----
#     ...contents of node-tokyo.key...
#     -----END PRIVATE KEY-----
#   marznode_client_cert_pem: |
#     -----BEGIN CERTIFICATE-----
#     ...contents of ca.crt (control plane peer auth)...
#     -----END CERTIFICATE-----
```

Run any playbook with `--vault-password-file ~/.vault-pass` or `--ask-vault-pass`.
The role's `no_log: true` prevents PEM bytes from leaking into Ansible logs.

`bootstrap` mode (one-time token exchange against the control plane) is reserved
for the offline install path and not implemented in v0.2; SPEC §risks marks it
"production not recommended". Stick with `marznode_cert_mode: file`.

## 3-command flow

```bash
# 1. Dry-run the entire fleet — green output means no changes pending.
ansible-playbook -i deploy/ansible/inventory.yml \
                 deploy/ansible/site.yml --check --diff

# 2. Real run — provisions control plane, then 2 marznode hosts in parallel.
ansible-playbook -i deploy/ansible/inventory.yml \
                 deploy/ansible/site.yml --ask-vault-pass

# 3. Verify panel reachable. Replace with your AEGIS_DOMAIN.
curl -sI https://panel.example.com/api/system/info
```

Acceptance budget: ≤30 minutes from a zero-state inventory of 2 marznode hosts
to a green panel (AC-D.3.1).

## Adding a 3rd node

Append a host block to `data_plane` in `inventory.yml`:

```yaml
node-frankfurt:
  ansible_host: "13.14.15.16"
  marznode_id: 3
  marznode_region: "eu-fra"
```

Add its vault file (`host_vars/node-frankfurt/vault.yml`), then:

```bash
ansible-playbook -i deploy/ansible/inventory.yml \
                 deploy/ansible/site.yml \
                 --limit node-frankfurt \
                 --ask-vault-pass
```

`--limit` ensures the existing control plane and other nodes are not touched
(AC-D.3.2). Run a `--check` against the full fleet afterwards to confirm
zero drift on untouched hosts (AC-D.3.3).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | SSH key not loaded on workstation | `ssh-add ~/.ssh/id_ed25519`, or set `ansible_ssh_private_key_file` per host |
| `sudo: a password is required` | `ansible_user` is not root and has no NOPASSWD | Pass `--ask-become-pass` once; for unattended, configure NOPASSWD in `/etc/sudoers.d/aegis` on the target |
| `marznode_cert_pem: empty` assert fails | Vault not loaded or var typo'd | `ansible-vault view host_vars/<host>/vault.yml`; check key spelling matches `defaults/main.yml` |
| `cf_tunnel_enabled=true but CF_API_TOKEN unset` | Token not exported on workstation | `export CF_API_TOKEN=...` before re-running; the playbook never reads it from disk |
| `install-node.sh: command not found` | D.2 PR not yet merged into your `aegis_repo_tag` | Bump `aegis_repo_tag` to a tag/branch that includes D.2, or temporarily skip with `--tags common,control_plane` |
| `Job for marzneshin-panel.service failed` | docker compose pull / up errored | `journalctl -u marzneshin-panel.service -n 100`; common causes are tag mismatch in `.env` AEGIS_VERSION or postgres startup race |
| `--check` reports changes on a deployed fleet | someone edited files on the host out-of-band | Reconcile by re-running without `--check`; long-term, lock down with config attestation |

## What this PR does NOT cover

- Certificate **rotation** — see SPEC §risks "证书轮换" for the future
  `cert-rotate.yml` playbook (D.3 follow-up).
- HTTP rate-limit smoke tests — covered by D.1 install.sh + D.4 nginx config.
- Adversarial regions / SNI selection — covered by S-R session.

## Idempotency notes

Every task uses one of: `state: present`, `creates:`, `when:` guard, or template
diff that triggers a handler restart only. Re-running `site.yml` against an
already-deployed fleet should report 0 changes (AC-D.3.3). Sentinel files
written by `install.sh` (`/opt/aegis/.install-step-N.done`) are the authoritative
truth — the role's `creates:` arg references the step-9 (full success) sentinel
so a partial install resumes from where it stopped.
