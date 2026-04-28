import { type FC } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { FetchError } from "ofetch";

import { Button } from "@marzneshin/common/components";

import { useHealthExtended } from "../api";

import { HealthOverallBadge } from "./health-overall-badge";
import { HealthStatusCard } from "./health-status-card";

/*
 * Full extended health report renderer.
 *
 * Layout: top strip with overall pill + version + uptime + manual
 * refresh button, then a small table with one row per subsystem
 * (sorted server-side by name, see hardening/health/endpoint.py).
 *
 * Auto-poll cadence (30s) is configured in
 * `useHealthExtended` — this component just consumes the hook and
 * exposes a manual refetch for impatient operators.
 */

const formatUptime = (seconds: number): string => {
    if (!Number.isFinite(seconds) || seconds < 0) return "—";
    const s = Math.floor(seconds);
    const days = Math.floor(s / 86_400);
    const hours = Math.floor((s % 86_400) / 3_600);
    const minutes = Math.floor((s % 3_600) / 60);
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
};

const isUnauthorized = (err: unknown): boolean => {
    if (err instanceof FetchError) {
        const status = err.response?.status;
        return status === 401 || status === 403;
    }
    return false;
};

export const HealthExtendedTable: FC = () => {
    const { t } = useTranslation();
    const { data, isLoading, isError, error, refetch, isFetching } =
        useHealthExtended();

    // L-017: extract long t() keys to consts before JSX use.
    const subtitleText = t("page.health.subtitle");
    const refreshText = t("page.health.refresh");
    const versionText = t("page.health.version");
    const uptimeText = t("page.health.uptime");
    const colName = t("page.health.column.name");
    const colStatus = t("page.health.column.status");
    const colLatency = t("page.health.column.latency");
    const colDetail = t("page.health.column.detail");
    const errLoad = t("page.health.error.load_failed");
    const errAuth = t("page.health.error.unauthorized");
    const loadingText = t("page.health.loading");

    if (isLoading) {
        return (
            <div className="text-sm text-muted-foreground">{loadingText}</div>
        );
    }

    if (isError) {
        const msg = isUnauthorized(error) ? errAuth : errLoad;
        return (
            <div className="rounded border border-destructive/50 bg-destructive/10 p-4">
                <p className="text-sm text-destructive">{msg}</p>
                <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => refetch()}
                    disabled={isFetching}
                >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    {refreshText}
                </Button>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 rounded border bg-card p-4">
                <HealthOverallBadge status={data.status} />
                <span className="text-sm text-muted-foreground">
                    {subtitleText}
                </span>
                <div className="ml-auto flex items-center gap-4 text-xs text-muted-foreground">
                    <span>
                        {versionText}: <span className="font-mono">{data.version}</span>
                    </span>
                    <span>
                        {uptimeText}: <span className="font-mono">{formatUptime(data.uptime_seconds)}</span>
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetch()}
                        disabled={isFetching}
                    >
                        <RefreshCw
                            className={
                                isFetching
                                    ? "mr-2 h-4 w-4 animate-spin"
                                    : "mr-2 h-4 w-4"
                            }
                        />
                        {refreshText}
                    </Button>
                </div>
            </div>

            <div className="overflow-x-auto rounded border">
                <table className="w-full text-left">
                    <thead className="bg-muted/40">
                        <tr>
                            <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                {colName}
                            </th>
                            <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                {colStatus}
                            </th>
                            <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                {colLatency}
                            </th>
                            <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                {colDetail}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.subsystems.map((s) => (
                            <HealthStatusCard key={s.name} subsystem={s} />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
