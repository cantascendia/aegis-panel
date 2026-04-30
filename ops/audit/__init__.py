"""Panel-wide audit log (S-AL session, v0.3 #4).

Captures all admin mutate actions into ``aegis_audit_events`` for
operator追责 / 客诉举证 / RBAC actor-role 联动.

See ``docs/ai-cto/SPEC-audit-log.md`` for the contract; D-018 for the
sealed TBD decisions.

Phase 1 (this PR): schema + Alembic migration only. Middleware /
endpoint / dashboard land in subsequent PRs (AL.2 / AL.3 / AL.4).
"""
