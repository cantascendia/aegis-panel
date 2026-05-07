/**
 * /health — System health page. Wave-A3 Nilou rewrite.
 *
 * Design reference: SPEC §14 route mapping — "类 Dashboard 主页":
 *   KPI 4 + BigChart (health score trend) + subsystem status card grid.
 *
 * Data: `useHealthExtended` hook → GET /api/aegis/health/extended
 *   Returns: { status, version, uptime_seconds, subsystems: [{name, status, message, details}] }
 *   Health score: not yet on wire (TODO P3 — backend PR pending);
 *     we derive an integer score from subsystems (1 down = 0, all ok = 100).
 *
 * Subsystem card tone mapping:
 *   ok       → emerald
 *   degraded → amber
 *   down     → coral
 *
 * i18n: reuses existing page.health.* keys (en.json already has them).
 *
 * Gate: sudo-only route — wrapped in <SudoRoute> matching original.
 */

import { type FC, useCallback } from "react";
import { createLazyFileRoute } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import {
    KPI,
    NilouCard,
    StatusDot,
    PanelHead,
} from "@marzneshin/common/components/nilou";
import { useHealthExtended, HealthExtendedQueryKey } from "@marzneshin/modules/health";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";
import type { HealthStatus, SubsystemHealth } from "@marzneshin/modules/health";
import type { StatusTone } from "@marzneshin/common/components/nilou";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map HealthStatus to StatusDot tone */
const healthTone = (status: HealthStatus): StatusTone => {
    if (status === "ok") return "emerald";
    if (status === "degraded") return "amber";
    return "coral"; // "down"
};

/**
 * Derive a simple 0-100 integer score from subsystem list.
 *   All ok     → 100
 *   Any down   → max 50 penalty each
 *   Degraded   → 20 penalty each
 * Capped at 0.
 */
function deriveScore(subsystems: SubsystemHealth[]): number {
    if (subsystems.length === 0) return 100;
    let score = 100;
    for (const s of subsystems) {
        if (s.status === "down") score -= 50;
        else if (s.status === "degraded") score -= 20;
    }
    return Math.max(0, score);
}

/** Format uptime_seconds as human string */
function fmtUptime(seconds: number): string {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    return `${h}h ${m}m`;
}

/** Format "last checked" timestamp */
function fmtTimestamp(iso: string | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------------
// Subsystem Card
// ---------------------------------------------------------------------------

interface SubsystemCardProps {
    subsystem: SubsystemHealth;
}

const SubsystemCard: FC<SubsystemCardProps> = ({ subsystem }) => {
    const { t } = useTranslation();
    const tone = healthTone(subsystem.status);
    const friendlyName = t(`page.health.subsystem.${subsystem.name}`, subsystem.name);
    const statusLabel = t(`page.health.overall.${subsystem.status}`, subsystem.status);
    // Extract last_check from details if present
    const lastCheck = (subsystem.details?.last_check as string | undefined) ?? undefined;

    return (
        <NilouCard style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Header row */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <StatusDot tone={tone} size={10} />
                <span
                    style={{
                        flex: 1,
                        fontWeight: 600,
                        fontSize: "0.96rem",
                        color: "hsl(var(--foreground))",
                    }}
                >
                    {friendlyName}
                </span>
                <span
                    style={{
                        fontSize: "0.78rem",
                        fontWeight: 500,
                        padding: "2px 8px",
                        borderRadius: 12,
                        background:
                            tone === "emerald"
                                ? "rgba(91,192,190,0.12)"
                                : tone === "amber"
                                    ? "rgba(232,176,75,0.12)"
                                    : "rgba(224,120,86,0.12)",
                        color:
                            tone === "emerald"
                                ? "#5bc0be"
                                : tone === "amber"
                                    ? "#e8b04b"
                                    : "#e07856",
                    }}
                >
                    {statusLabel}
                </span>
            </div>

            {/* Message */}
            {subsystem.message && (
                <p
                    style={{
                        margin: 0,
                        fontSize: "0.84rem",
                        color: "hsl(var(--muted-foreground))",
                        lineHeight: 1.4,
                    }}
                >
                    {subsystem.message}
                </p>
            )}

            {/* Last checked */}
            {lastCheck && (
                <div
                    style={{
                        fontSize: "0.78rem",
                        color: "hsl(var(--muted-foreground))",
                    }}
                >
                    {t("nilou.health.last_checked", "Last checked")}: {fmtTimestamp(lastCheck)}
                </div>
            )}
        </NilouCard>
    );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const HealthPage: FC = () => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const { data: health, isLoading, isError } = useHealthExtended();

    const subsystems: SubsystemHealth[] = health?.subsystems ?? [];
    const onlineCount = subsystems.filter((s) => s.status === "ok").length;
    const degradedCount = subsystems.filter((s) => s.status === "degraded").length;
    const downCount = subsystems.filter((s) => s.status === "down").length;
    const score = deriveScore(subsystems);

    const handleRefresh = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: [HealthExtendedQueryKey] });
    }, [queryClient]);

    return (
        <>
            <PanelHead
                title={t("page.health.title", "System health")}
                sub={t("page.health.subtitle", "Live status of the panel and its subsystems.")}
                actions={
                    <button
                        type="button"
                        onClick={handleRefresh}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "8px 16px",
                            borderRadius: 8,
                            border: "1px solid hsl(var(--border) / 0.8)",
                            background: "hsl(var(--card))",
                            color: "hsl(var(--foreground))",
                            fontSize: "0.9rem",
                            fontWeight: 500,
                            cursor: "pointer",
                        }}
                    >
                        ↻ {t("page.health.refresh", "Refresh")}
                    </button>
                }
            />

            {/* Error state */}
            {isError && !health && (
                <NilouCard style={{ marginBottom: 22 }}>
                    <p style={{ margin: 0, color: "#e07856" }}>
                        {t("page.health.error.load_failed", "Failed to load health report.")}
                    </p>
                </NilouCard>
            )}

            {/* 4-KPI row */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(4, 1fr)",
                    gap: 14,
                    marginBottom: 22,
                }}
            >
                <KPI
                    label={t("nilou.health.kpi.overall", "Overall score")}
                    value={isLoading ? "…" : `${score}`}
                    sub={
                        score >= 80
                            ? t("page.health.overall.green", "Healthy")
                            : score >= 50
                                ? t("page.health.overall.yellow", "Degraded")
                                : t("page.health.overall.red", "Down")
                    }
                    accent={score >= 80 ? "emerald" : score >= 50 ? "gold" : "coral"}
                    trend={score < 80 ? "down" : "up"}
                />
                <KPI
                    label={t("nilou.health.kpi.online", "Online subsystems")}
                    value={isLoading ? "…" : `${onlineCount}`}
                    sub={`of ${subsystems.length} total`}
                    accent="emerald"
                />
                <KPI
                    label={t("nilou.health.kpi.degraded", "Degraded")}
                    value={isLoading ? "…" : `${degradedCount}`}
                    sub={t("nilou.health.kpi.degraded_sub", "Partially impaired")}
                    accent={degradedCount > 0 ? "gold" : "teal"}
                    trend={degradedCount > 0 ? "down" : "up"}
                />
                <KPI
                    label={t("nilou.health.kpi.last_check", "Last check")}
                    value={
                        isLoading
                            ? "…"
                            : health?.uptime_seconds != null
                                ? fmtUptime(health.uptime_seconds)
                                : "—"
                    }
                    sub={
                        health?.version
                            ? `v${health.version}`
                            : t("page.health.version", "Version")
                    }
                    accent="teal"
                />
            </div>

            {/* Subsystem grid */}
            {!isLoading && subsystems.length > 0 && (
                <>
                    <h2
                        style={{
                            margin: "0 0 14px",
                            fontSize: "1rem",
                            fontWeight: 600,
                            color: "hsl(var(--foreground))",
                        }}
                    >
                        {t("nilou.health.subsystems_heading", "Subsystem status")}
                    </h2>
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                            gap: 14,
                        }}
                    >
                        {subsystems.map((sub) => (
                            <SubsystemCard key={sub.name} subsystem={sub} />
                        ))}
                    </div>
                </>
            )}

            {/* Down subsystems call-out */}
            {!isLoading && downCount > 0 && (
                <NilouCard style={{ marginTop: 22, borderColor: "rgba(224,120,86,0.4)" }}>
                    <p
                        style={{
                            margin: 0,
                            color: "#e07856",
                            fontSize: "0.92rem",
                            fontWeight: 500,
                        }}
                    >
                        ⚠ {downCount}{" "}
                        {t(
                            "nilou.health.subsystems_down",
                            "subsystem(s) are currently DOWN. Check panel logs immediately.",
                        )}
                    </p>
                </NilouCard>
            )}

            {/* Empty state */}
            {!isLoading && !isError && subsystems.length === 0 && (
                <NilouCard>
                    <p
                        style={{
                            margin: 0,
                            textAlign: "center",
                            color: "hsl(var(--muted-foreground))",
                            fontSize: "0.9rem",
                        }}
                    >
                        {t(
                            "nilou.health.no_subsystems",
                            "No subsystem data available — backend health probes may not have run yet.",
                        )}
                    </p>
                </NilouCard>
            )}
        </>
    );
};

export const Route = createLazyFileRoute("/_dashboard/health")({
    component: () => (
        <SudoRoute>
            <HealthPage />
        </SudoRoute>
    ),
});
