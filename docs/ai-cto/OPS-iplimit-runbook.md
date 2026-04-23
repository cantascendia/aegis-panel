# OPS: IP Limiter Production Runbook

This runbook covers operational checks required before enabling
`violation_action = "disable"` for paying users.

## Deployment prerequisite

Run the panel container and every Marznode container with the same
timezone. Prefer UTC everywhere:

```yaml
environment:
  TZ: UTC
```

Why this matters: `hardening/iplimit/events.py` parses Xray timestamps
as naive local time. Xray writes access-log timestamps in the Marznode
container's local time. If the panel and Marznode containers use
different timezones, parsed `observed_at` scores can drift by hours and
the rolling window may prune real events as stale.

## Timezone validation

Run this before production rollout and after every container image or
compose change:

```bash
docker exec marzneshin-panel date
docker exec marznode-1 date
docker exec marznode-2 date
```

The displayed timezone and wall-clock time must match. If nodes are
deployed outside the compose project, run the equivalent command on
each host or container runtime.

## Symptoms of timezone mismatch

- The user is actively connected, but the IP limiter tab shows zero
  observed IPs.
- Redis has `aegis:iplimit:observed:{user_id}` ZSET members, but their
  scores are hours behind or ahead of `date +%s` in the panel
  container.
- Audit logs stay empty even though Xray access logs contain traffic
  for the user's `email:` label.

Inspect Redis scores:

```bash
redis-cli ZRANGE aegis:iplimit:observed:<user_id> 0 -1 WITHSCORES
date +%s
```

## Recovery

1. Set the same `TZ` value on the panel and all Marznode containers.
   UTC is preferred.
2. Restart the panel and Marznode containers so Xray and the detector
   see the same local time basis.
3. Clear stale runtime observations for affected users if the window is
   polluted with wrong scores:

   ```bash
   redis-cli DEL aegis:iplimit:observed:<user_id>
   ```

4. Re-check the user's IP limiter tab after fresh activity.

No SQL data fix is required for timezone mismatch. Policy and audit
tables remain valid.

## Real-log parser validation

Before enabling `disable`, capture a small access-log sample from each
node type in production:

```bash
docker exec marznode-1 sh -lc 'tail -n 50 /var/log/xray/access.log'
```

Verify that each user-owned traffic row has:

- a parseable source IP after `from`
- an `email:` label matching a panel username
- a timestamp with the same timezone basis as the panel

Compare new shapes against
`docs/ai-cto/XRAY-ACCESS-LOG-SAMPLES.md`. If a production row has an
unlisted shape, add it to the samples doc and a parser regression test
before turning on automatic disable.

## Safe rollout sequence

1. Keep global `violation_action = "warn"` for at least 24 hours.
2. Review audit events for false positives, especially mobile and CGNAT
   users.
3. Add CIDR allowlists for operator, monitoring, and known carrier
   ranges before switching selected users to `disable`.
4. Enable `disable` on one low-risk test account first.
5. Monitor Telegram alerts, audit rows, and user support tickets for one
   full business day before broad rollout.

## Long-term parser decision

The current production-hardening round keeps local-time parsing and
documents the timezone requirement. A future breaking-change PR may
switch parser semantics to UTC-only, but that must be coordinated with
Marznode container configuration and migration notes.
