# SPEC — SNI Intelligent Selector (MVP)

> Round 2 v0.2 opening — per `docs/ai-cto/ROADMAP.md` differentiator #1 and
> `docs/ai-cto/VISION.md`.
>
> Status: draft → implementation in the `hardening/sni/` branch(es) that
> follow. This PR only introduces the spec.
>
> Template: follows the D-005 Spec-Driven shape established by
> `SPEC-postgres-redis.md`.

---

## What

A CLI (`python -m hardening.sni.selector`) + library that, given a VPS's
public egress IP, returns a ranked JSON list of candidate Reality
`serverName` values — each one verified against six hard indicators and
one soft indicator at probe time.

MVP surface:

```bash
python -m hardening.sni.selector --ip 1.2.3.4 --count 10 --region auto
# -> JSON on stdout, exit 0 on success, non-zero if <1 candidate passes
```

```python
from hardening.sni.selector import select_candidates
candidates = select_candidates(vps_ip="1.2.3.4", count=10, region="auto")
# -> list[Candidate] with score + rationale per candidate
```

**Scope boundaries (MVP)**:

- ✅ Six hard indicators, all verified at probe time, not just cached.
- ✅ Same-ASN neighbor-scan mode (passive: lookup the /24 or ASN's
  published IP list, *not* the aggressive RealiTLScanner approach).
- ✅ Regional candidate seeds (JP / KR / US / global) pulled from a
  checked-in YAML so operators can edit without a code change.
- ✅ Rate-limited external probes; all HTTP timeouts bounded.
- ✅ Dashboard integration point defined (JSON contract), but the
  dashboard PR is separate.
- ❌ **No aggressive /24 SYN-scan**. RealiTLScanner-style /24 sweep is
  fast but noisy; it can get a VPS flagged. We start with candidate-list
  probing and add scan mode later if demand justifies it.
- ❌ **No live DPI-blacklist maintenance UI**. MVP ships a static
  blacklist bundled in the repo (`hardening/sni/blacklist.yaml`) and a
  clear story for updating it manually. A "subscribe to external
  intelligence feed" feature is v0.3+.
- ❌ **No continuous re-probing / health monitoring**. That's the
  "Reality 健康度仪表盘" (VISION differentiator #3), scheduled for v0.3.
  MVP is one-shot: operator asks, we answer once.
- ❌ **No Sing-box / other protocol support**. Reality / `serverName` only.

## Why

Quoting `VISION.md`:

> **SNI 智能选型器** | ⏳ 待建(差异化 #1) | 同 ASN 邻居扫描 +
> TLS 1.3/H2/X25519 验证 + DPI 黑名单

And the `compass_artifact_wf-*.md` executive summary:

> 最安全的组合是 VLESS + XTLS-Vision + Reality,SNI 挑选同数据中心且
> 支持 TLS 1.3 / H2 / X25519 的冷门域名 ... 2024 年 Iran MCCI 在数小时
> 内封锁了大量以 `speedtest.net` 为 SNI 的节点,证明"热门 SNI + 脏 IP
> 段"组合已进入 DPI 黑名单.

Currently operators must:

1. Read the compass spec
2. Know the six indicators
3. Manually `xray tls ping` a dozen domains
4. Compare against the /24 of the VPS by hand
5. Keep a personal mental blacklist of "dead" SNIs

This takes 30-60 minutes per node, is error-prone, and goes stale
within weeks. **No competitor automates this** (3X-UI / Hiddify / S-UI
/ Remnawave all ship static candidate lists at best). This is
differentiator #1's entire pitch.

**Business gate**: Round 2 v0.2 acceptance says the new-node flow
auto-populates a valid `serverName` in 80% of operator scenarios. This
feature is the *mechanism* for that number.

## How

### The six hard indicators (each a pass/fail check)

Order matters for efficiency — cheap checks first so we reject most
candidates before paying for TLS probes.

| # | Indicator | Implementation | Cost |
|---|---|---|---|
| 1 | Not on the DPI blacklist | Exact-match against `blacklist.yaml` | ~free (dict lookup) |
| 2 | Resolves without 301/302 | HTTP HEAD + 1 follow; reject if `301`/`302` points to a different hostname | ~50ms |
| 3 | Same ASN as the VPS IP | Compare ASN via Team Cymru's `whois.cymru.com` | ~100ms, cacheable |
| 4 | TLS 1.3 handshake succeeds | Python `ssl.SSLContext(PROTOCOL_TLS_CLIENT)` + `set_min_proto_version(TLSv1_3)` | ~200ms |
| 5 | ALPN negotiates `h2` | Set `set_alpn_protocols(["h2"])`, check `selected_alpn_protocol()` after handshake | ~free (piggybacks on #4) |
| 6 | X25519 curve in ECDHE | Read `SSLObject.shared_ciphers()` → verify `X25519` is in the advertised ECDHE groups; requires OpenSSL 3.2+ | ~free (piggybacks on #4) |

**Soft indicator** (contributes to score but doesn't fail the candidate):

- **S1 — OCSP Stapling on + fast handshake** (compass's `dl.google.com` example). Boosts score by +10% if both present. Not a hard fail because some otherwise-excellent candidates don't staple.

### Scoring

Score = 1.0 if all six hard pass, plus soft bonuses, minus penalties:

- +0.1 same datacenter (subnet match, not just ASN)
- +0.1 OCSP Stapling on
- -0.2 if TLS handshake RTT > 200ms from the VPS (probable cross-ocean)
- -0.1 if `Set-Cookie` present (session state = real users = auditable logs of proxy traffic, not ideal)

Sort descending by score; return top `--count`.

### Candidate seed pool

Bundled at `hardening/sni/seeds/`:

- `global.yaml` — ~40 entries: Microsoft / Apple / Mozilla / CDN-Anycast giants
- `jp.yaml` — ~20 entries for Asia deployments (per compass recommendations)
- `kr.yaml`
- `us.yaml`
- `eu.yaml`

Each entry: `{host: str, category: str, notes: str}`. Operators can edit
without code changes. The CLI's `--region auto` inspects the VPS IP's
country (via Team Cymru) and merges `global.yaml` + matching region.

### ASN / geo lookup

Use **Team Cymru's free whois service** (`whois.cymru.com`, port 43 TCP
or `origin.asn.cymru.com` DNS mode). Free, no API key, gives ASN +
country + allocation date in one query. Wrap behind a small
`hardening/sni/asn.py` module with a local LRU cache keyed by `/24`.

Alternatives evaluated and rejected for MVP:

- **MaxMind GeoLite2** — free but requires license-key signup, DB update
  every few days. Adds ops complexity for 0 accuracy gain at MVP scale.
- **IPinfo / IP2Proxy** — paid for the good data. Out of budget for MVP.
- **RIPE NCC / ARIN WHOIS** — authoritative but rate-limited and slow;
  use as fallback if Team Cymru is down.

### DPI blacklist

`hardening/sni/blacklist.yaml`:

```yaml
# Known-bad SNIs. Format:
#   - host: <fqdn>
#     reason: <short story>
#     source: <url-or-doc>
#     added: <YYYY-MM-DD>
blocked:
  - host: speedtest.net
    reason: "Iran MCCI DPI mass-block Nov 2024"
    source: "compass_artifact_wf-*.md section 'SNI 选择'"
    added: "2026-04-22"
  - host: www.google.com
    reason: "Unreachable in CN → fallback failure"
    source: "compass_artifact"
    added: "2026-04-22"
```

Operators can pull new entries via a follow-up PR. MVP does not ship a
live feed subscription — that's a v0.3 concern once we see real
operational need.

### Probe implementation

Synchronous-in-structure, concurrent-in-execution:

```python
import asyncio

async def check_candidate(host: str, vps_asn: int) -> Candidate:
    ...  # runs all six checks with aiohttp + asyncio ssl

async def select_candidates(vps_ip: str, count: int, region: str):
    vps_asn = await asn_lookup(vps_ip)
    seeds = load_seeds(region)
    # cap concurrency — we don't want to look like a scanner
    sem = asyncio.Semaphore(5)
    results = await asyncio.gather(*[
        bounded(sem, check_candidate(s, vps_asn)) for s in seeds
    ])
    return rank(results)[:count]
```

Constraints: `aiohttp` timeout=5s per probe, total wall-clock budget 30s
for `--count 10` from a 40-entry seed list.

### Output format (the dashboard contract)

```json
{
  "vps_ip": "1.2.3.4",
  "vps_asn": 14061,
  "vps_country": "US",
  "probed_at": "2026-04-22T10:15:30Z",
  "elapsed_seconds": 12.3,
  "candidates": [
    {
      "host": "www.microsoft.com",
      "score": 0.95,
      "checks": {
        "blacklist_ok": true,
        "no_redirect": true,
        "same_asn": false,
        "tls13_ok": true,
        "alpn_h2_ok": true,
        "x25519_ok": true,
        "ocsp_stapling": true,
        "rtt_ms": 45
      },
      "notes": "global CDN anycast; no datacenter match"
    },
    ...
  ],
  "rejected": [
    {"host": "speedtest.net", "reason": "blacklist: Iran MCCI mass-block Nov 2024"},
    ...
  ]
}
```

The `rejected` section is intentional: operators who are surprised by
absent candidates can see **why** without re-running the tool in
verbose mode.

### Dashboard integration point (separate PR)

`app/routes/node.py` gets a new endpoint:

```
POST /api/nodes/sni-suggest
Body: {"vps_ip": "1.2.3.4", "count": 5}
→ invokes `hardening.sni.selector.select_candidates(...)` with a 60s timeout
→ returns the JSON above directly
```

Dashboard "新建节点" form calls this on blur of the IP field, displays
the top 5 as radio options, defaults to the top-scored one. This PR
does *not* implement that endpoint — it's the third PR of Round 2 v0.2,
after the selector + CLI are stable.

### Testing

- Unit tests for each hard indicator as a pure function (mock ssl /
  aiohttp responses)
- Golden file for the JSON output format (guards against accidental
  schema drift)
- Integration test with **VCR.py**-style recorded responses for the top
  5 seed hosts; avoids hitting the real internet in CI
- No test that actually connects to external hosts — CI can run
  sandboxed

## Risks

| Risk | Mitigation |
|---|---|
| Team Cymru being down / rate-limited | Fall back to RIPE/ARIN WHOIS (slower but works); cache by /24 for 24h |
| OpenSSL < 3.2 on the host misses X25519 detection | Document minimum OpenSSL in DEVELOPMENT.md; the dockerized path is fine (Alpine 3.19+ ships 3.2) |
| Our probe looking like a scanner to the SNI target | Semaphore caps concurrency, user-agent mimics real browsers, HTTPS only, no port sweeps |
| Static blacklist goes stale | Acknowledged. MVP accepts this; v0.3 ships feed-subscription. Manual PRs in the meantime |
| Operator runs from a dev laptop with a different ASN than the VPS | `--ip <vps>` is required; the tool doesn't guess from local IP. Documented with loud warning if `--ip` happens to match local interface |
| Candidate with same ASN but different **datacenter** (common on AWS/Azure) | Soft score only; not a hard fail. Still useful |

## Acceptance criteria

- [ ] CLI returns ≥ 3 candidates in ≤ 30 seconds for a DigitalOcean / Vultr / Hetzner VPS
- [ ] Every hard indicator has ≥ 1 positive and ≥ 1 negative unit test
- [ ] JSON output schema has a golden file + schema-drift guard test
- [ ] `hardening/sni/blacklist.yaml` and `seeds/*.yaml` are editable without code changes (load + validate at CLI startup)
- [ ] No network call in the CI test suite
- [ ] DEVELOPMENT.md section added describing how to use the CLI locally
- [ ] `hardening/panel/README.md` updated to cross-reference SNI selector
- [ ] CI `lint (ruff)` + `test (pytest)` + `pip-audit` all green

## Follow-up PRs (Round 2 v0.2)

After this SPEC PR lands:

1. **`feat(hardening): sni selector core + 6 indicators`** — `hardening/sni/` module, seeds, blacklist, CLI, tests
2. **`feat(hardening): sni dashboard endpoint`** — `app/routes/node.py` + dashboard form integration
3. **`docs(hardening): sni runbook`** — `deploy/README.md` addition: "how to read the output when none of the candidates pass"

If the feedback on #1 suggests the scan-based approach (RealiTLScanner-style /24 probe) is actually needed, that's a separate PR (`feat(hardening): sni scan mode`) not bundled.
