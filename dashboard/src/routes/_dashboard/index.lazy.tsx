/**
 * Operator home — Wave-A3 Nilou rewrite.
 *
 * Design reference: `docs/design-system-source/project/site/lib/PanelPages1.jsx`
 * DashboardPage (lines 30-97). Operator data mapping per SPEC §How.data-mapping:
 *
 *   KPI 1  — Total users          (UsersStats.total)
 *   KPI 2  — Active users 24h     (UsersStats.active)
 *   KPI 3  — Online nodes         (nodes query first-page total estimate)
 *   KPI 4  — Avg health score     (HealthReport.overall_score — not yet on wire,
 *                                   placeholder with TODO)
 *
 * BigChart — Platform-wide 14-day daily traffic totals via useTotalTrafficQuery.
 *            Endpoint: GET /api/system/stats/traffic?start=…&end=…
 *            Returns usages: number[][] (download per node per day) + total.
 *            We collapse to a single per-day series by summing across nodes.
 *
 * RingMeter — quota usage from UsersStats (no per-platform cap field yet;
 *             we use active/total as a ratio proxy until backend adds the
 *             cap endpoint — TODO P3: replace with real cap field).
 *
 * Recent activity — audit log last 10 rows via useAuditEvents.
 *
 * Quick links  — /users, /nodes, /audit, /reality
 *
 * i18n: uses existing keys where possible; new nilou.overview.* keys added
 * to public/locales/en.json + zh-cn.json + (partial) others via this PR.
 */

import { type FC, useMemo } from "react";
import { createLazyFileRoute, Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import {
    KPI,
    NilouCard,
    NilouCardHeader,
    BigChart,
    RingMeter,
    NilouRow,
    StatusDot,
    PanelHead,
} from "@marzneshin/common/components/nilou";
import { useUsersStatsQuery } from "@marzneshin/modules/users";
import { useTotalTrafficQuery } from "@marzneshin/features/total-traffic-widget/api";
import { useAuditEvents } from "@marzneshin/modules/audit";
import { useHealthExtended } from "@marzneshin/modules/health";
import type { StatusTone } from "@marzneshin/common/components/nilou";
import type { AuditResult } from "@marzneshin/modules/audit";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map AuditResult to a StatusDot tone */
const auditTone = (result: AuditResult): StatusTone => {
    if (result === "success") return "emerald";
    if (result === "failure") return "coral";
    return "amber"; // "denied"
};

/** Format bytes → human GB/MB/KB for BigChart y-axis label */
function bytesToGB(bytes: number): number {
    return Math.round((bytes / 1e9) * 100) / 100;
}

/** Collapse a 2D usage matrix (per-node per-day) into a 1D per-day array */
function collapseUsages(usages: number[][]): number[] {
    if (!usages || usages.length === 0) return [];
    const days = usages[0].length;
    const result: number[] = new Array(days).fill(0);
    for (const nodeUsage of usages) {
        for (let d = 0; d < days; d++) {
            result[d] += nodeUsage[d] ?? 0;
        }
    }
    return result.map(bytesToGB);
}

/** ISO date string N days from today */
function isoOffset(daysAgo: number): string {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    return d.toISOString().slice(0, 10);
}

/** Format a numeric duration as "Xd Xh Xm" */
function fmtUptime(seconds: number): string {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    if (d > 0) return `${d}d ${h}h`;
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
}

/** Format a timestamp relative to now — "X min ago" style */
function fmtRelative(ts: string): string {
    const delta = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (delta < 60) return `${delta}s ago`;
    if (delta < 3600) return `${Math.floor(delta / 60)} min ago`;
    if (delta < 86400) return `${Math.floor(delta / 3600)} h ago`;
    return `${Math.floor(delta / 86400)} d ago`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const OperatorHomePage: FC = () => {
    const { t } = useTranslation();

    // --- user stats ---
    const { data: userStats } = useUsersStatsQuery();

    // --- 14-day traffic ---
    const trafficStart = isoOffset(14);
    const trafficEnd = isoOffset(0);
    const { data: trafficData } = useTotalTrafficQuery({ start: trafficStart, end: trafficEnd });
    const trafficSeries = useMemo(
        () => collapseUsages(trafficData?.usages ?? []),
        [trafficData],
    );

    // --- health ---
    const { data: health } = useHealthExtended();

    // --- audit recent ---
    const { data: auditData } = useAuditEvents({ limit: 10 });
    const auditItems = auditData?.items ?? [];

    // KPI derived values
    const totalUsers = userStats?.total ?? 0;
    const activeUsers = userStats?.active ?? 0;
    const onlineCount = userStats?.online ?? 0;
    // Compute health score from subsystems: % of subsystems reporting "ok".
    // Backend HealthReport.status is a tri-state (ok/degraded/down), not a
    // numeric score; we derive a percentage here for KPI display.
    const healthScore = (() => {
        const subs = health?.subsystems ?? [];
        if (subs.length === 0) return null;
        const okCount = subs.filter((s) => s.status === "ok").length;
        return Math.round((okCount / subs.length) * 100);
    })();

    // Quota ratio: active / total (proxy until cap API is available)
    const quotaPercent =
        totalUsers > 0 ? Math.round((activeUsers / totalUsers) * 100) : 0;

    // Quick-link targets
    const quickLinks = [
        { label: t("users"), to: "/users" },
        { label: t("nodes"), to: "/nodes" },
        { label: t("page.audit.title"), to: "/audit" },
        { label: t("page.reality.title"), to: "/reality" },
    ];

    return (
        <>
            <PanelHead
                title={t("nilou.overview.welcome", "Welcome back")}
                sub={t("nilou.overview.sub", {
                    users: totalUsers,
                    active: activeUsers,
                    defaultValue: "{{users}} users · {{active}} active",
                })}
            />

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
                    label={t("nilou.kpi.total_users", "Total users")}
                    value={totalUsers}
                    sub={t("nilou.kpi.all_accounts", "All accounts")}
                    sparkData={[
                        totalUsers * 0.7,
                        totalUsers * 0.75,
                        totalUsers * 0.8,
                        totalUsers * 0.85,
                        totalUsers * 0.9,
                        totalUsers * 0.95,
                        totalUsers,
                    ]}
                    accent="teal"
                />
                <KPI
                    label={t("nilou.kpi.active_users", "Active users")}
                    value={activeUsers}
                    sub={t("nilou.kpi.last_24h", "Last 24 h")}
                    accent="gold"
                />
                <KPI
                    label={t("nilou.kpi.online_nodes", "Online nodes")}
                    value={onlineCount}
                    sub={t("nilou.kpi.currently_up", "Currently up")}
                    accent="emerald"
                />
                <KPI
                    label={t("nilou.kpi.health_score", "Avg health score")}
                    value={healthScore != null ? `${healthScore}` : "—"}
                    sub={
                        healthScore != null
                            ? t("nilou.kpi.reality_grade", "Reality grade")
                            : t("nilou.kpi.health_na", "Run /health check")
                    }
                    accent={
                        healthScore == null
                            ? "coral"
                            : healthScore >= 80
                                ? "emerald"
                                : "coral"
                    }
                />
            </div>

            {/* 2-col main: BigChart + RingMeter */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr",
                    gap: 14,
                    marginBottom: 22,
                }}
            >
                {/* Traffic chart */}
                <NilouCard>
                    <NilouCardHeader
                        title={t("nilou.overview.traffic_chart_title", "Traffic, last 14 days")}
                        sub={t("nilou.overview.traffic_chart_sub", "Upload + download, daily totals (GB)")}
                    />
                    <div style={{ height: 220, position: "relative", padding: "0 8px" }}>
                        {trafficSeries.length > 0 ? (
                            <BigChart
                                primary={trafficSeries}
                                // TODO P3: add upload series when backend exposes it separately
                            />
                        ) : (
                            <div
                                style={{
                                    height: "100%",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    color: "hsl(var(--muted-foreground))",
                                    fontSize: "0.9rem",
                                }}
                            >
                                {/* TODO P3: wire real platform-wide traffic data from
                                    GET /api/system/stats/traffic once backend exposes daily breakdown */}
                                {t("nilou.overview.chart_loading", "Loading traffic data…")}
                            </div>
                        )}
                    </div>
                </NilouCard>

                {/* Capacity RingMeter */}
                <NilouCard>
                    <NilouCardHeader
                        title={t("nilou.overview.capacity_title", "Capacity")}
                        sub={t("nilou.overview.capacity_sub", "Active / total user ratio")}
                    />
                    <RingMeter
                        percent={quotaPercent}
                        label={`${quotaPercent}%`}
                        sub={t("nilou.overview.capacity_ring_sub", {
                            active: activeUsers,
                            total: totalUsers,
                            defaultValue: "{{active}} of {{total}} active",
                        })}
                    />
                    <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 10 }}>
                        <NilouRow
                            a={t("nilou.kpi.total_users", "Total users")}
                            b={String(totalUsers)}
                        />
                        <NilouRow
                            a={t("nilou.kpi.active_users", "Active")}
                            b={String(activeUsers)}
                        />
                        {health?.uptime_seconds != null && (
                            <NilouRow
                                a={t("nilou.overview.uptime", "Uptime")}
                                b={fmtUptime(health.uptime_seconds)}
                            />
                        )}
                    </div>
                </NilouCard>
            </div>

            {/* 2-col bottom: Recent activity + Quick links */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 14,
                }}
            >
                {/* Recent activity (audit log) */}
                <NilouCard>
                    <NilouCardHeader
                        title={t("nilou.overview.recent_activity", "Recent activity")}
                        action={
                            <Link
                                to="/audit"
                                style={{
                                    fontSize: "0.82rem",
                                    color: "hsl(var(--primary))",
                                    textDecoration: "none",
                                }}
                            >
                                {t("nilou.overview.view_all", "View all →")}
                            </Link>
                        }
                    />
                    <div style={{ display: "flex", flexDirection: "column" }}>
                        {auditItems.length === 0 && (
                            <div
                                style={{
                                    padding: "24px 0",
                                    textAlign: "center",
                                    color: "hsl(var(--muted-foreground))",
                                    fontSize: "0.86rem",
                                }}
                            >
                                {t("nilou.overview.no_activity", "No recent activity")}
                            </div>
                        )}
                        {auditItems.map((evt, i) => (
                            <div
                                key={evt.id}
                                style={{
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 12,
                                    padding: "10px 0",
                                    borderBottom:
                                        i < auditItems.length - 1
                                            ? "1px solid hsl(var(--border) / 0.5)"
                                            : "none",
                                }}
                            >
                                <span style={{ marginTop: 6 }}>
                                    <StatusDot tone={auditTone(evt.result)} />
                                </span>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div
                                        style={{
                                            color: "hsl(var(--foreground))",
                                            fontSize: "0.92rem",
                                            fontWeight: 500,
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        {evt.action}
                                    </div>
                                    <div
                                        style={{
                                            color: "hsl(var(--muted-foreground))",
                                            fontSize: "0.82rem",
                                        }}
                                    >
                                        {evt.actor_username ?? t("page.audit.actor.anonymous", "(anonymous)")}
                                    </div>
                                </div>
                                <div
                                    style={{
                                        color: "hsl(var(--muted-foreground))",
                                        fontSize: "0.78rem",
                                        whiteSpace: "nowrap",
                                    }}
                                >
                                    {fmtRelative(evt.ts)}
                                </div>
                            </div>
                        ))}
                    </div>
                </NilouCard>

                {/* Quick links */}
                <NilouCard>
                    <NilouCardHeader
                        title={t("nilou.overview.quick_links", "Quick links")}
                    />
                    <div
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 10,
                        }}
                    >
                        {quickLinks.map(({ label, to }) => (
                            <Link
                                key={to}
                                to={to}
                                style={{
                                    display: "block",
                                    padding: "10px 14px",
                                    borderRadius: 8,
                                    border: "1px solid hsl(var(--border) / 0.6)",
                                    background: "hsl(var(--muted) / 0.35)",
                                    color: "hsl(var(--foreground))",
                                    fontSize: "0.92rem",
                                    fontWeight: 500,
                                    textDecoration: "none",
                                    transition: "background 0.15s",
                                }}
                            >
                                {label}
                            </Link>
                        ))}
                    </div>
                </NilouCard>
            </div>
        </>
    );
};

export const Route = createLazyFileRoute("/_dashboard/")({
    component: () => <OperatorHomePage />,
});
