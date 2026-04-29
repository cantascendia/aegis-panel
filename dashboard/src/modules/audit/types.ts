/**
 * Frontend mirror of `ops/audit/schemas.py`.
 *
 * Wire format: `GET /api/audit/events` returns `AuditEventRow[]`.
 * `GET /api/audit/events/{id}` returns `AuditEventDetail` (with decrypted
 * before/after state — sudo-admin only).
 */

export type AuditResult = "success" | "failure" | "denied";

export type AuditActorType = "sudo_admin" | "admin" | "anonymous";

export interface AuditEventRow {
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
    ts: string;
}

export interface AuditEventDetail extends AuditEventRow {
    before_state: Record<string, unknown> | null;
    after_state: Record<string, unknown> | null;
}

export interface AuditStatsResponse {
    total_7d: number;
    by_result: Record<string, number>;
    by_actor_type: Record<string, number>;
    top_actions: Array<{ action: string; count: number }>;
}

export interface AuditEventFilters {
    actor_username?: string;
    actor_type?: AuditActorType | "";
    result?: AuditResult | "";
    before_id?: number;
    limit?: number;
}
