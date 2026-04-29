import { type FC } from "react";
import { useTranslation } from "react-i18next";
import { Play, RefreshCw } from "lucide-react";

import { Button } from "@marzneshin/common/components";
import { cn } from "@marzneshin/common/utils";

import type { Grade, ReportSummary } from "../types";

/*
 * Top-of-page summary box.
 *
 * Two roles:
 *   1. Render the latest report's roll-up (total / green / yellow / red
 *      / worst_score) when a report is available.
 *   2. Host the "Run audit" button that kicks the mutation. The button
 *      stays visible after a successful audit so operators can re-run.
 *
 * Worst-score color uses the same green/amber/red mapping as the
 * per-target grade pill, so glancing at the card communicates overall
 * health without reading every row.
 *
 * Pre-audit state (no `summary` prop): only the run button + helper
 * text. Empty placeholders for the count cells would just be visual
 * noise.
 */

const worstScoreClass = (worst: number): string => {
    if (worst >= 70) return "text-emerald-700 dark:text-emerald-400";
    if (worst >= 60) return "text-amber-600 dark:text-amber-500";
    return "text-destructive";
};

const worstGradeFor = (worst: number): Grade => {
    if (worst >= 70) return "green";
    if (worst >= 60) return "yellow";
    return "red";
};

export interface AuditSummaryCardProps {
    summary: ReportSummary | null;
    auditedAt: string | null;
    isPending: boolean;
    onRun: () => void;
}

export const AuditSummaryCard: FC<AuditSummaryCardProps> = ({
    summary,
    auditedAt,
    isPending,
    onRun,
}) => {
    const { t } = useTranslation();
    const subtitleText = t("page.reality.subtitle");
    const runText = t("page.reality.run");
    const rerunText = t("page.reality.rerun");
    const runningText = t("page.reality.running");
    const totalText = t("page.reality.summary.total");
    const greenText = t("page.reality.summary.green");
    const yellowText = t("page.reality.summary.yellow");
    const redText = t("page.reality.summary.red");
    const worstText = t("page.reality.summary.worst");
    const auditedAtText = t("page.reality.summary.audited_at");

    const buttonLabel = isPending
        ? runningText
        : summary
          ? rerunText
          : runText;

    const ButtonIcon = isPending ? RefreshCw : Play;

    return (
        <div className="rounded border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-sm text-muted-foreground">
                        {subtitleText}
                    </p>
                    {auditedAt && (
                        <p className="mt-1 text-xs text-muted-foreground">
                            {auditedAtText}:{" "}
                            <span className="font-mono">{auditedAt}</span>
                        </p>
                    )}
                </div>
                <Button onClick={onRun} disabled={isPending}>
                    <ButtonIcon
                        className={cn(
                            "mr-2 h-4 w-4",
                            isPending && "animate-spin",
                        )}
                    />
                    {buttonLabel}
                </Button>
            </div>

            {summary && (
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <SummaryStat
                        label={totalText}
                        value={summary.total}
                        accent="text-foreground"
                    />
                    <SummaryStat
                        label={greenText}
                        value={summary.green}
                        accent="text-emerald-700 dark:text-emerald-400"
                    />
                    <SummaryStat
                        label={yellowText}
                        value={summary.yellow}
                        accent="text-amber-600 dark:text-amber-500"
                    />
                    <SummaryStat
                        label={redText}
                        value={summary.red}
                        accent="text-destructive"
                    />
                    <SummaryStat
                        label={worstText}
                        // total === 0 means the audit has no targets.
                        // The backend uses worst_score=100 as its
                        // empty-state sentinel, but rendering a literal
                        // "100" next to "0 targets" reads as a perfect
                        // result (security theater — see issue #119).
                        // Show an em-dash instead so operators
                        // immediately see "no data", not "all green".
                        value={
                            summary.total === 0
                                ? "—"
                                : summary.worst_score
                        }
                        accent={
                            summary.total === 0
                                ? "text-muted-foreground"
                                : worstScoreClass(summary.worst_score)
                        }
                        title={
                            summary.total === 0
                                ? undefined
                                : `grade=${worstGradeFor(summary.worst_score)}`
                        }
                    />
                </div>
            )}
        </div>
    );
};

interface SummaryStatProps {
    label: string;
    // Accepts a string fallback for empty-state placeholder ("—")
    // alongside the normal numeric counts.
    value: number | string;
    accent: string;
    title?: string;
}

const SummaryStat: FC<SummaryStatProps> = ({ label, value, accent, title }) => (
    <div className="rounded border bg-background p-3" title={title}>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
        </p>
        <p className={cn("mt-1 text-2xl font-bold tabular-nums", accent)}>
            {value}
        </p>
    </div>
);
