import { type FC } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@marzneshin/common/components";

import type { SubsystemHealth, HealthStatus } from "../types";

/*
 * One-row view of a single subsystem probe outcome.
 *
 * The backend response (`hardening/health/endpoint.py`,
 * `SubsystemHealth.to_dict`) gives us:
 *   - name     — stable identifier, e.g. "billing_scheduler"
 *   - status   — "ok" | "degraded" | "down"
 *   - message  — operator-facing single-line detail
 *   - details  — free-form key/value dict
 *
 * Note: the backend currently does NOT return a `latency_ms` field on
 * subsystems. The page renders `message` as the human-readable detail
 * column. If a future probe surfaces latency in the `details` map, the
 * latency formatter below is ready — see formatLatency().
 */

const variantFor = (
    status: HealthStatus,
): "positive" | "warning" | "destructive" => {
    if (status === "ok") return "positive";
    if (status === "degraded") return "warning";
    return "destructive";
};

const labelFor = (status: HealthStatus, t: (k: string) => string): string => {
    if (status === "ok") return t("page.health.overall.green");
    if (status === "degraded") return t("page.health.overall.yellow");
    return t("page.health.overall.red");
};

const subsystemLabel = (
    name: string,
    t: (k: string) => string,
): string => {
    // Friendly name lookup. i18next returns the key string itself when
    // the translation is missing; we fall back to the raw subsystem
    // name in that case rather than printing the bare key.
    const key = `page.health.subsystem.${name}`;
    const translated = t(key);
    return translated === key ? name : translated;
};

// Drift-gate visibility (per L-017): the dynamic key above is invisible
// to the line-based extractor in tools/check_translations.sh. The
// literals below mirror every subsystem name the backend can return,
// so the JSON entries register as referenced. Tree-shaken in prod
// (no side effects).
const _drift_gate_subsystems = (t: (k: string) => string) => [
    t("page.health.subsystem.db"),
    t("page.health.subsystem.billing_scheduler"),
    t("page.health.subsystem.iplimit_scheduler"),
    t("page.health.subsystem.trc20"),
    t("page.health.subsystem.reality_seeds"),
    t("page.health.subsystem.sni_seeds"),
    t("page.health.overall.unknown"),
];
void _drift_gate_subsystems;

/**
 * Format a latency in milliseconds: `<1000ms` shows as `<n>ms`,
 * `>=1000ms` as `<n.n>s`. Exposed for any future probe that surfaces
 * a latency_ms inside the details dict.
 */
export const formatLatency = (ms: number): string => {
    if (!Number.isFinite(ms) || ms < 0) return "—";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
};

const pickLatency = (details: Record<string, unknown>): number | null => {
    const raw = details["latency_ms"];
    return typeof raw === "number" ? raw : null;
};

export interface HealthStatusCardProps {
    subsystem: SubsystemHealth;
}

export const HealthStatusCard: FC<HealthStatusCardProps> = ({ subsystem }) => {
    const { t } = useTranslation();
    const latencyMs = pickLatency(subsystem.details);
    return (
        <tr className="border-b last:border-b-0">
            <td className="px-3 py-2 align-top font-mono text-sm">
                {subsystemLabel(subsystem.name, t)}
            </td>
            <td className="px-3 py-2 align-top">
                <Badge variant={variantFor(subsystem.status)}>
                    {labelFor(subsystem.status, t)}
                </Badge>
            </td>
            <td className="px-3 py-2 align-top text-sm tabular-nums">
                {latencyMs !== null ? formatLatency(latencyMs) : "—"}
            </td>
            <td className="px-3 py-2 align-top text-sm text-muted-foreground">
                {subsystem.message || "—"}
            </td>
        </tr>
    );
};
