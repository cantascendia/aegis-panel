/*
 * Frontend types for the audit-log read API (S-AL Phase 3).
 *
 * Wire shape mirrors `ops.audit.schemas` (Pydantic ResponseModel).
 * Keep these in sync with the backend SPEC §How.5 — the dashboard
 * is the only consumer of the AL.3 endpoint today.
 */

export type AuditResult = "success" | "failure" | "denied";

export type AuditActorType = "sudo_admin" | "admin" | "anonymous";

export interface AuditEventSummary {
    id: number;
    actor_id: number | null;
    actor_type: AuditActorType;
    actor_username: string | null;
    action: string;
    method: string;
    path: string;
    target_type: string | null;
    target_id: string | null;
    result: AuditResult;
    status_code: number;
    error_message: string | null;
    ip: string;
    user_agent: string | null;
    request_id: string | null;
    ts: string; // ISO-8601 UTC
}

export interface AuditEventDetail extends AuditEventSummary {
    before_state: unknown | null;
    after_state: unknown | null;
}

export interface AuditEventListResponse {
    items: AuditEventSummary[];
    next_cursor: number | null;
    total_returned: number;
}

export interface AuditListParams {
    actor_username?: string;
    action?: string;
    target_type?: string;
    target_id?: string;
    result?: AuditResult;
    since?: string;
    until?: string;
    limit?: number;
    cursor?: number;
}
