from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

import pytest

from hardening.iplimit.events import parse_xray_access_line


@dataclass(frozen=True)
class PositiveLogSample:
    sample_id: str
    line: str
    username: str
    source_ip: str
    timestamp: str | None


POSITIVE_SAMPLES = [
    PositiveLogSample(
        "XLOG-001",
        "2024/10/11 22:12:29 from tcp:203.0.113.10:46438 "
        "accepted tcp:security.example:80 [Direct] email: alice",
        "alice",
        "203.0.113.10",
        "2024/10/11 22:12:29",
    ),
    PositiveLogSample(
        "XLOG-002",
        "2024/10/11 22:12:30 from tcp:203.0.113.10:46438 "
        "accepted tcp:archive.example:80 [Direct] email: alice",
        "alice",
        "203.0.113.10",
        "2024/10/11 22:12:30",
    ),
    PositiveLogSample(
        "XLOG-003",
        "2025/08/18 20:17:34.148046 from tcp:127.0.0.1:7738 "
        "accepted tcp:10.10.34.36:443 [socks -> direct] email: bob",
        "bob",
        "127.0.0.1",
        "2025/08/18 20:17:34",
    ),
    PositiveLogSample(
        "XLOG-004",
        "2025/12/19 07:29:17.449333 from 192.0.2.44:38824 "
        "accepted tcp:www.example:443 [vless-in -> direct] email: charlie",
        "charlie",
        "192.0.2.44",
        "2025/12/19 07:29:17",
    ),
    PositiveLogSample(
        "XLOG-005",
        "2025/02/05 20:51:51.724977 from tcp:198.51.100.7:0 "
        "accepted udp:203.0.113.77:62641 [vless_grpc -> direct] "
        "email: alice",
        "alice",
        "198.51.100.7",
        "2025/02/05 20:51:51",
    ),
    PositiveLogSample(
        "XLOG-006",
        "2025/02/05 16:51:50 from udp:198.51.100.8:52525 "
        "accepted udp:8.8.8.8:53 [socksIn -> dnsOut] email: bob",
        "bob",
        "198.51.100.8",
        "2025/02/05 16:51:50",
    ),
    PositiveLogSample(
        "XLOG-007",
        "2025/02/05 16:51:50 from tcp:[2001:db8::10]:60946 "
        "accepted tcp:[2001:4860:4860::8888]:443 [socksIn >> proxy] "
        "email: charlie",
        "charlie",
        "2001:db8::10",
        "2025/02/05 16:51:50",
    ),
    PositiveLogSample(
        "XLOG-008",
        "2025/02/05 16:51:55 from udp:[2001:db8::20]:53956 "
        "accepted udp:216.58.210.162:443 [socksIn >> proxy] email: alice",
        "alice",
        "2001:db8::20",
        "2025/02/05 16:51:55",
    ),
    PositiveLogSample(
        "XLOG-009",
        "from tcp:198.51.100.9:55000 accepted udp:1.1.1.1:53 email: bob",
        "bob",
        "198.51.100.9",
        None,
    ),
    PositiveLogSample(
        "XLOG-010",
        "2024/10/11 22:12:29 from tcp:203.0.113.11:46438 "
        "accepted tcp:security.example:80 [Direct] email: alice@example.com",
        "alice@example.com",
        "203.0.113.11",
        "2024/10/11 22:12:29",
    ),
]


NEGATIVE_SAMPLES = [
    pytest.param(
        "XLOG-N01",
        "2025/02/05 20:51:25.484206 from [Masked IPv4]:0 "
        "accepted udp:[Masked IPv4]:53 [vless_grpc -> direct] email: alice",
        id="masked-source-ip",
    ),
    pytest.param(
        "XLOG-N02",
        "2025/02/05 16:51:50 from DNS accepted udp:8.8.8.8:53 "
        "[dnsQuery -> proxy]",
        id="dns-pseudo-source",
    ),
    pytest.param(
        "XLOG-N03",
        "2025/02/05 16:52:40 from [::1]:61700 accepted tcp:[::1]:0 "
        "[metricsIn -> metricsOut]",
        id="metrics-no-email",
    ),
    pytest.param(
        "XLOG-N04",
        "2025/02/05 16:51:50 from tcp:[2001:db8::30]:60948 "
        "accepted tcp:[2001:4860:4860::8888]:443 [socksIn >> proxy]",
        id="traffic-no-email",
    ),
]


@pytest.mark.parametrize(
    "sample",
    [pytest.param(sample, id=sample.sample_id) for sample in POSITIVE_SAMPLES],
)
def test_parse_xray_real_world_positive_variants(
    sample: PositiveLogSample,
) -> None:
    users = {"alice": 1, "bob": 2, "charlie": 3, "alice@example.com": 4}

    event = parse_xray_access_line(sample.line, users)

    assert event is not None
    assert event.user_id == users[sample.username]
    assert event.username == sample.username
    assert event.source_ip == sample.source_ip
    assert event.observed_at == _local_ts(sample.timestamp)


@pytest.mark.parametrize(("sample_id", "line"), NEGATIVE_SAMPLES)
def test_parse_xray_real_world_ignored_variants(
    sample_id: str, line: str
) -> None:
    _ = sample_id
    users = {"alice": 1, "bob": 2, "charlie": 3}

    assert parse_xray_access_line(line, users) is None


def _local_ts(value: str | None) -> int | None:
    if value is None:
        return None
    parsed = datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
    return int(time.mktime(parsed.timetuple()))
