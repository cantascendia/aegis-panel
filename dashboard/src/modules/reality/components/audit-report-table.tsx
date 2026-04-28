import { type FC } from "react";
import { useTranslation } from "react-i18next";
import { FetchError } from "ofetch";

import type { Report } from "../types";
import { useRealityAudit } from "../api";

import { AuditSummaryCard } from "./audit-summary-card";
import { AuditTargetRow } from "./audit-target-row";

/*
 * Top-level renderer for the Reality audit page.
 *
 * Owns:
 *   - The mutation (`useRealityAudit`)
 *   - Empty / loading / error / report states
 *   - The summary card + per-target table layout
 *
 * The page route (routes/_dashboard/reality.lazy.tsx) just wraps this
 * in <SudoRoute><Page>...</Page></SudoRoute>.
 *
 * Initial state: no report, summary card shows "Run audit" CTA only.
 * Post-success: summary card + table.
 * Post-error: summary card stays so operator can retry; an inline
 * error block appears above the table area with the error message
 * (401/403 → friendly auth text; 504 → relay backend's WHOIS-hang
 * message; other → generic).
 */

const isAuthError = (err: unknown): boolean => {
    if (err instanceof FetchError) {
        const status = err.response?.status;
        return status === 401 || status === 403;
    }
    return false;
};

const isTimeout = (err: unknown): boolean => {
    if (err instanceof FetchError) {
        return err.response?.status === 504;
    }
    return false;
};

export const AuditReportTable: FC = () => {
    const { t } = useTranslation();
    const mutation = useRealityAudit();
    const report: Report | null = mutation.data ?? null;

    const colHost = t("page.reality.column.host");
    const colSni = t("page.reality.column.sni");
    const colPort = t("page.reality.column.port");
    const colScore = t("page.reality.column.score");
    const colGrade = t("page.reality.column.grade");
    const colFindings = t("page.reality.column.findings");
    const emptyText = t("page.reality.empty");
    const errAuth = t("page.reality.error.unauthorized");
    const errTimeout = t("page.reality.error.timeout");
    const errGeneric = t("page.reality.error.failed");
    const noTargetsText = t("page.reality.no_targets");

    const handleRun = () => {
        mutation.mutate({ source: "db" });
    };

    let errorMessage: string | null = null;
    if (mutation.isError) {
        if (isAuthError(mutation.error)) errorMessage = errAuth;
        else if (isTimeout(mutation.error)) errorMessage = errTimeout;
        else errorMessage = errGeneric;
    }

    return (
        <div className="space-y-4">
            <AuditSummaryCard
                summary={report?.summary ?? null}
                auditedAt={report?.audited_at ?? null}
                isPending={mutation.isPending}
                onRun={handleRun}
            />

            {errorMessage && (
                <div className="rounded border border-destructive/50 bg-destructive/10 p-4">
                    <p className="text-sm text-destructive">{errorMessage}</p>
                </div>
            )}

            {!report && !mutation.isPending && !errorMessage && (
                <div className="rounded border border-dashed bg-muted/20 p-8 text-center text-sm text-muted-foreground">
                    {emptyText}
                </div>
            )}

            {report && report.targets.length === 0 && (
                <div className="rounded border border-dashed bg-muted/20 p-8 text-center text-sm text-muted-foreground">
                    {noTargetsText}
                </div>
            )}

            {report && report.targets.length > 0 && (
                <div className="overflow-x-auto rounded border">
                    <table className="w-full text-left">
                        <thead className="bg-muted/40">
                            <tr>
                                <th className="px-3 py-2 w-8" />
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colHost}
                                </th>
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colSni}
                                </th>
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colPort}
                                </th>
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colScore}
                                </th>
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colGrade}
                                </th>
                                <th className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {colFindings}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {report.targets.map((target) => (
                                <AuditTargetRow
                                    key={`${target.host}-${target.sni}-${target.port}`}
                                    target={target}
                                />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};
