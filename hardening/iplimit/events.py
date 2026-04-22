"""Connection event collection from existing Marznode clients."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"\bemail:\s*(?P<username>[\w.-]{1,128})\b")
_FROM_RE = re.compile(
    r"\bfrom\s+(?:(?:tcp|udp):)?(?P<host>\[[0-9a-fA-F:.]+\]|[^:\s]+)"
)


@dataclass(frozen=True)
class ConnectionEvent:
    """One user source-IP observation."""

    user_id: int
    username: str
    source_ip: str


def parse_xray_access_line(
    line: str, username_to_id: Mapping[str, int]
) -> ConnectionEvent | None:
    """Extract a connection event from one Xray access-log line.

    Expected Xray shape includes ``from tcp:<ip>:<port>`` and
    ``email: <username>``. Unknown users and malformed IPs are ignored.
    """

    user_match = _EMAIL_RE.search(line)
    source_match = _FROM_RE.search(line)
    if not user_match or not source_match:
        return None

    username = user_match.group("username")
    user_id = username_to_id.get(username)
    if user_id is None:
        return None

    host = source_match.group("host").strip("[]")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None

    return ConnectionEvent(
        user_id=user_id,
        username=username,
        source_ip=str(ip),
    )


async def collect_events_from_nodes(
    nodes: Mapping[int, object],
    username_to_id: Mapping[str, int],
    *,
    max_lines_per_node: int,
    read_timeout_seconds: float,
) -> list[ConnectionEvent]:
    """Collect bounded recent access-log events from existing nodes."""

    results = await asyncio.gather(
        *[
            _collect_node_events(
                node_id=node_id,
                node=node,
                username_to_id=username_to_id,
                max_lines=max_lines_per_node,
                read_timeout_seconds=read_timeout_seconds,
            )
            for node_id, node in nodes.items()
        ],
        return_exceptions=True,
    )

    events: list[ConnectionEvent] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("iplimit node event collection failed: %s", result)
            continue
        events.extend(result)
    return events


async def _collect_node_events(
    *,
    node_id: int,
    node: object,
    username_to_id: Mapping[str, int],
    max_lines: int,
    read_timeout_seconds: float,
) -> list[ConnectionEvent]:
    get_logs = getattr(node, "get_logs", None)
    if get_logs is None:
        return []

    events: list[ConnectionEvent] = []
    stream: AsyncIterator[str] = get_logs("xray", include_buffer=True)
    for _ in range(max_lines):
        try:
            line = await asyncio.wait_for(
                anext(stream), timeout=read_timeout_seconds
            )
        except (StopAsyncIteration, TimeoutError):
            break

        event = parse_xray_access_line(line, username_to_id)
        if event:
            events.append(event)

    logger.debug(
        "iplimit collected %d events from node %s", len(events), node_id
    )
    return events
