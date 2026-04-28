/*
 * Frontend mirror of `hardening/reality/models.py`.
 *
 * The backend serializes via `Report.to_dict()` (see endpoint.py R.3),
 * so these types match the v1.0 wire schema returned by
 * `POST /api/reality/audit` exactly.
 *
 * Per SPEC §"Output schema (v1.0)":
 *   - `schema_version` is a string, currently "1.0"; additive changes
 *     bump to 1.x without breaking consumers.
 *   - `audited_at` is ISO-8601 UTC, injected server-side for
 *     byte-deterministic diff property.
 *   - `source` discriminates DB-driven audits from caller-supplied
 *     xray config dry-runs.
 *   - `findings[].data` is `Record<string, unknown>` rather than
 *     `any`: machine-readable supplementary fields (asn, tranco_rank,
 *     etc.) the dashboard does not interpret here but might surface
 *     in a future "details" expandable.
 */

export type Grade = "green" | "yellow" | "red";

export type Severity = "critical" | "warning" | "info";

export type AuditSource = "db" | "config";

export interface Finding {
    check: string;
    ok: boolean;
    severity: Severity;
    score_delta: number;
    evidence: string;
    remediation: string;
    data: Record<string, unknown>;
}

export interface TargetResult {
    host: string;
    sni: string;
    port: number;
    score: number;
    grade: Grade;
    findings: Finding[];
}

export interface ReportSummary {
    total: number;
    green: number;
    yellow: number;
    red: number;
    worst_score: number;
}

export interface Report {
    schema_version: string;
    audited_at: string;
    source: AuditSource;
    targets: TargetResult[];
    summary: ReportSummary;
}

/*
 * Request body shape for POST /api/reality/audit.
 *
 * The backend (`hardening/reality/endpoint.py::AuditRequest`) mutexes
 * source/config: `source="db"` forbids `config`, `source="config"`
 * requires it. `vps_asn` is optional — without it `asn_match` returns
 * a graceful warning (-10) rather than a hard fail.
 */
export interface AuditRequestBody {
    source: AuditSource;
    config?: Record<string, unknown>;
    vps_asn?: number;
}
