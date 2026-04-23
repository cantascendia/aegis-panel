# Xray Access Log Samples for IP Limiter

Purpose: provide traceable access-log variants for hardening
`hardening/iplimit/events.py`. The samples below are normalized from
public issue reports and docs: real IPs, domains, UUIDs, and user labels
are replaced with RFC 5737 / RFC 3849 documentation values and
`alice` / `bob` / `charlie`.

Do not treat this as an exhaustive grammar. Treat it as a regression
fixture list for the current parser. Any new parser widening should map
back to a sample ID here.

## Sources

- Xray official LogObject docs: access logs are configured via the
  `log.access` field and may mask IP addresses with `maskAddress`.
  Source: https://xtls.github.io/en/config/log.html
- XTLS/Xray-core issue #3904: VLESS mux access lines with
  `from tcp:<ip>:<port> accepted tcp:<domain>:<port> ... email:`.
  Source: https://github.com/XTLS/Xray-core/issues/3904
- XTLS/Xray-core issue #4354: Xray 1.8.24+ traffic examples with
  microsecond timestamps, masked addresses, UDP destination lines,
  DNS pseudo-source rows, metrics rows, and IPv6 bracketed endpoints.
  Source: https://github.com/XTLS/Xray-core/issues/4354
- 2dust/v2rayN issue #7798: local socks-mode examples with
  `from tcp:127.0.0.1:<port> accepted tcp:<ip>:443`.
  Source: https://github.com/2dust/v2rayN/issues/7798
- Community DNS-over-Xray report: short-form examples where the
  source protocol prefix may be absent and destination protocol is UDP.
  Source: https://www.reddit.com/r/dumbclub/comments/1himzif

## Positive parser samples

These should become `ConnectionEvent` rows when the username exists.

| ID | Variant | Normalized sample | Expected source IP | Expected username | Timestamp expected |
|---|---|---|---|---|---|
| XLOG-001 | VLESS mux, seconds timestamp, IPv4 source, domain destination | `2024/10/11 22:12:29 from tcp:203.0.113.10:46438 accepted tcp:security.example:80 [Direct] email: alice` | `203.0.113.10` | `alice` | yes |
| XLOG-002 | VLESS mux, repeated source port, different destination | `2024/10/11 22:12:30 from tcp:203.0.113.10:46438 accepted tcp:archive.example:80 [Direct] email: alice` | `203.0.113.10` | `alice` | yes |
| XLOG-003 | v2rayN/socks local client, fractional timestamp | `2025/08/18 20:17:34.148046 from tcp:127.0.0.1:7738 accepted tcp:10.10.34.36:443 [socks -> direct] email: bob` | `127.0.0.1` | `bob` | yes |
| XLOG-004 | Source protocol omitted, IPv4 source | `2025/12/19 07:29:17.449333 from 192.0.2.44:38824 accepted tcp:www.example:443 [vless-in -> direct] email: charlie` | `192.0.2.44` | `charlie` | yes |
| XLOG-005 | UDP destination with source protocol prefix | `2025/02/05 20:51:51.724977 from tcp:198.51.100.7:0 accepted udp:203.0.113.77:62641 [vless_grpc -> direct] email: alice` | `198.51.100.7` | `alice` | yes |
| XLOG-006 | UDP source and UDP destination | `2025/02/05 16:51:50 from udp:198.51.100.8:52525 accepted udp:8.8.8.8:53 [socksIn -> dnsOut] email: bob` | `198.51.100.8` | `bob` | yes |
| XLOG-007 | IPv6 source and IPv6 destination | `2025/02/05 16:51:50 from tcp:[2001:db8::10]:60946 accepted tcp:[2001:4860:4860::8888]:443 [socksIn >> proxy] email: charlie` | `2001:db8::10` | `charlie` | yes |
| XLOG-008 | IPv6 source, IPv4 destination, UDP | `2025/02/05 16:51:55 from udp:[2001:db8::20]:53956 accepted udp:216.58.210.162:443 [socksIn >> proxy] email: alice` | `2001:db8::20` | `alice` | yes |
| XLOG-009 | No timestamp, short DNS-over-Xray shape | `from tcp:198.51.100.9:55000 accepted udp:1.1.1.1:53 email: bob` | `198.51.100.9` | `bob` | no |
| XLOG-010 | Email-like Xray client label | `2024/10/11 22:12:29 from tcp:203.0.113.11:46438 accepted tcp:security.example:80 [Direct] email: alice@example.com` | `203.0.113.11` | `alice@example.com` | yes |

## Negative / ignore samples

These are real shapes that should not emit a user event unless future
Xray behavior adds a user label.

| ID | Variant | Normalized sample | Expected behavior |
|---|---|---|---|
| XLOG-N01 | Masked source IP from `maskAddress`; original user can be known but IP cannot | `2025/02/05 20:51:25.484206 from [Masked IPv4]:0 accepted udp:[Masked IPv4]:53 [vless_grpc -> direct] email: alice` | ignore, source IP is not recoverable |
| XLOG-N02 | DNS pseudo-source, no IP | `2025/02/05 16:51:50 from DNS accepted udp:8.8.8.8:53 [dnsQuery -> proxy]` | ignore |
| XLOG-N03 | Metrics loopback row, no email | `2025/02/05 16:52:40 from [::1]:61700 accepted tcp:[::1]:0 [metricsIn -> metricsOut]` | ignore |
| XLOG-N04 | Normal traffic row but no `email:` label | `2025/02/05 16:51:50 from tcp:[2001:db8::30]:60948 accepted tcp:[2001:4860:4860::8888]:443 [socksIn >> proxy]` | ignore |

## Parser risk notes

- Current `_EMAIL_RE` must accept Xray client labels containing `@`.
  Xray configs commonly describe `email` as an arbitrary user label,
  not necessarily a valid email address, but public samples include
  both plain names and email-like values.
- Fractional timestamps should parse to the same second-level
  `observed_at`; the IP limiter does not need sub-second precision.
- Masked IP rows must stay ignored. Counting `[Masked IPv4]` as an IP
  would collapse many users into one fake source.
- Rows with no `email:` should stay ignored; the limiter is per user and
  cannot safely infer ownership from inbound tag alone.
