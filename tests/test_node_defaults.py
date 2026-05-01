"""Regression tests for fork-owned defaults on app/models/node.py.

Wave-6 PR #169 flipped the NodeCreate default connection_backend from
``grpclib`` (upstream Marzneshin) to ``grpcio`` (matches our
docker-compose.{prod,sqlite}.yml marznode INSECURE=True default).

These tests pin the fork-owned diff so an upstream sync that
reverts back to grpclib will fail loudly in CI.

Refs: L-034 wave-6, L-036 wave-4 (marznode v0.5.x INSECURE=True
default → panel grpclib backend wraps SSL → "Missing content-type
header" GRPCError on every RPC).
"""

from __future__ import annotations

from app.models.node import Node, NodeConnectionBackend, NodeCreate


def test_node_default_backend_is_grpcio_not_grpclib() -> None:
    """The fork default must stay grpcio. Upstream Marzneshin defaults
    to grpclib — if a sync merge regressed this back, panel↔marznode
    RPC would silently fail on every fresh install (operator never
    creates a node with explicit backend, so default fires)."""
    n = Node(name="t", address="127.0.0.1", port=62051)
    assert n.connection_backend is NodeConnectionBackend.grpcio
    assert n.connection_backend == "grpcio"

    # Also via the NodeCreate alias
    nc = NodeCreate(name="t2", address="127.0.0.1", port=62051)
    assert nc.connection_backend is NodeConnectionBackend.grpcio


def test_node_explicit_grpclib_still_accepted() -> None:
    """Operators wanting full mTLS (multi-host, marznode INSECURE=False)
    must be able to opt back into grpclib. Default flip must not
    remove the option."""
    n = Node(
        name="t",
        address="127.0.0.1",
        port=62051,
        connection_backend=NodeConnectionBackend.grpclib,
    )
    assert n.connection_backend is NodeConnectionBackend.grpclib


def test_node_connection_backend_enum_only_has_two_values() -> None:
    """Pin the enum membership so an upstream addition (e.g. a hypothetical
    'grpc-web' or 'rest') gets surfaced in CI before merge — it would
    need decision on default behavior + compose alignment."""
    members = {m.value for m in NodeConnectionBackend}
    assert members == {"grpcio", "grpclib"}
