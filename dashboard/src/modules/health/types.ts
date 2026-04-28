/*
 * Frontend mirror of `hardening/health/models.py`.
 *
 * The backend serialises through `HealthReport.to_dict()` and
 * `SubsystemHealth.to_dict()`, so these types match the wire shape
 * returned by `GET /api/aegis/health/extended` exactly.
 *
 * Subsystem `name` is a stable identifier the backend emits as
 * lowercase snake_case (e.g. "billing_scheduler"). We don't enum it
 * here: new probes added on the backend should appear in the table
 * without a frontend change. The i18n `subsystem.<name>` lookup is
 * the friendly label, with a fallback to the raw name when no key
 * exists yet.
 */

export type HealthStatus = "ok" | "degraded" | "down";

export interface SubsystemHealth {
    name: string;
    status: HealthStatus;
    message: string;
    details: Record<string, unknown>;
}

export interface HealthReport {
    status: HealthStatus;
    version: string;
    uptime_seconds: number;
    subsystems: SubsystemHealth[];
}
