# Cloudflare Tunnel + Access — Aegis Panel

This directory automates the **CF Tunnel + Access** path described in
`docs/ai-cto/SPEC-deploy.md` §"CF Tunnel 自动化(D.4)" and the compass
research artifact §"CF Tunnel". Operationally:

- **Hides the origin IP** behind Cloudflare's anycast network. `dig` against
  `$PANEL_DOMAIN` returns CF edge addresses only — direct origin scans no
  longer find the panel.
- **Adds an authentication layer** in front of the panel. Even if the panel's
  own login is misconfigured (Marzban historically lacks TOTP, see compass
  artifact §"管理面板加固"), Cloudflare Access enforces email OTP or SSO.
- **Deletes cleanly** for emergency rollback (LESSONS L-022).

> AGPL §13 reminder. Routing the panel through CF Tunnel does NOT remove
> your AGPL-3.0 source-disclosure obligation. Aegis Panel is a hard fork of
> Marzneshin (see `NOTICE.md`); your dashboard / API still needs to expose a
> link to your modified source. Run `deploy/compliance/agpl-selfcheck.sh`
> after install — it checks both the upstream attribution and the source
> link reachability.

## Files

| File | Purpose |
|---|---|
| `install-tunnel.sh` | Create tunnel, render config, upsert DNS CNAME, install systemd unit. |
| `setup-access.sh` | Create Access application + policy (email OTP default). |
| `uninstall-tunnel.sh` | Tear down Access app, DNS CNAME, tunnel, local config. |
| `cloudflared.config.yml.template` | Ingress config template; rendered by `install-tunnel.sh`. |

## Prerequisite — minimal-scope API token

The operator creates a **scoped** Cloudflare API token (NOT a Global API
Key). From <https://dash.cloudflare.com/profile/api-tokens>, click
**Create Token → Custom token** and grant exactly:

| Scope | Permission | Why |
|---|---|---|
| Account → Cloudflare Tunnel | **Edit** | create / list / delete the tunnel |
| Zone → DNS | **Edit** (limited to the zone owning `$PANEL_DOMAIN`) | upsert CNAME to `<uuid>.cfargotunnel.com` |
| Account → Access: Apps and Policies | **Edit** | create the Access application + policy |
| Account → Access: Service Tokens | Read (optional) | session-duration validation |
| Zone → Zone Settings | Read (optional) | verify Always Use HTTPS / Universal SSL |

The first three are mandatory. `install-tunnel.sh` calls
`GET /user/tokens/verify` and enumerates scopes on startup — missing any
required scope **exits 5** with the missing scope listed (per AC-D.4.5 in
SPEC-deploy.md).

The token is read from the `CF_API_TOKEN` env var only. None of the scripts
write it to disk. **Do not** put the token in `.env` files committed to git
(matches the SPEC "Risks: CF token 误提 commit" mitigation).

## Step-by-step (3 commands)

```bash
# 0. Export the token in your current shell only
export CF_API_TOKEN='cf_pat_xxxxxxxxxxxxxxxxxxxxxxxx'

# 1. Provision tunnel + DNS + systemd
sudo -E ./install-tunnel.sh \
    --domain panel.example.com \
    --panel-port 8443

# 2. Lock it down with Access (email OTP — codes mailed to admins)
./setup-access.sh \
    --domain panel.example.com \
    --emails ops@example.com,cto@example.com

# 3. Verify
dig +short panel.example.com          # expect CF anycast IPs (104.x / 172.x)
curl -sI https://panel.example.com    # expect 302 to https://*.cloudflareaccess.com
```

`install.sh --cf-tunnel yes` (D.1, parallel sibling PR) chains into
`install-tunnel.sh` automatically with the values it has already collected.
Running this directory standalone is supported and is the documented path
for retrofitting an existing panel.

### Optional: Google SSO

If your CF Zero Trust account already has a Google IdP bound, swap step 2:

```bash
./setup-access.sh \
    --domain panel.example.com \
    --emails ops@example.com \
    --sso google
```

## Verifying acceptance criteria

| Check | Command | Pass condition |
|---|---|---|
| AC-D.4.1 origin hidden | `dig +short $PANEL_DOMAIN` | CF anycast IPs only |
| AC-D.4.2 Access enforced | `curl -sI https://$PANEL_DOMAIN` | `302` to `*.cloudflareaccess.com` |
| AC-D.4.3 clean uninstall | run `uninstall-tunnel.sh`, then `dig $PANEL_DOMAIN` | NXDOMAIN / no orphan record |
| AC-D.4.5 scope enforcement | run with a token missing `Zone.DNS:Edit` | exit code = 5, scope listed on stderr |

`--dry-run` is supported on all three scripts and prints intended API calls
without firing any. Use it in CI / staging before pointing at a real account.

## Token rotation procedure

1. Create a **new** token in the CF dashboard with the same scopes.
2. Confirm it works:
   `CF_API_TOKEN='<new>' ./install-tunnel.sh --domain $PANEL_DOMAIN --dry-run`
3. Update the operator's secret store / shell init.
4. Revoke the old token from the CF dashboard.

The scripts hold no token state, so rotation is a config-only change — no
re-running `install-tunnel.sh` is needed unless you also want to rotate the
underlying tunnel UUID (rare; do it during a maintenance window because
DNS propagation will follow).

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `exit 4: token verify failed` | Token revoked / typo | re-issue, re-export `CF_API_TOKEN` |
| `exit 5: missing scope X` | Token lacks Tunnel/DNS/Access edit | re-issue with the table above |
| `exit 6: zone not found` | Domain not in this CF account | move the zone in or use a domain on this account |
| `502` after install | Panel not yet listening on `--panel-port` | `systemctl status aegis-panel`; bring panel up first |
| Login page never loads | DNS not propagated | wait up to 5 min, then recheck `dig` |
| Google SSO loop | IdP not bound in CF Zero Trust | bind the IdP first in <https://one.dash.cloudflare.com> → Settings → Authentication |

## Rollback

`uninstall-tunnel.sh --domain $PANEL_DOMAIN` removes the Access app, the DNS
CNAME, the tunnel, and `/etc/cloudflared/config.yml` in that order. The
order matters: revoke auth first, redirect users second, free the tunnel
slot third. Use `--keep-config` to leave the local YAML for forensic review.

## Cross-references

- `deploy/install/install.sh` (D.1) calls `install-tunnel.sh` when invoked
  with `--cf-tunnel yes`.
- `deploy/compliance/agpl-selfcheck.sh` (#88, merged) treats
  `https://$PANEL_DOMAIN` as the "panel reachable" target — any tunnel
  outage will surface there too.
- `docs/ai-cto/SPEC-deploy.md` §"CF Tunnel 自动化(D.4)" — authoritative
  acceptance criteria.
- `compass_artifact_*.md` §"CF Tunnel" — operational rationale.

License: AGPL-3.0-or-later. Aegis Panel is a hard fork of Marzneshin
(<https://github.com/marzneshin/marzneshin>). See `../../NOTICE.md`.
