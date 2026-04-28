import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Badge } from "@marzneshin/common/components";
import { cn } from "@marzneshin/common/utils";

import type { Grade, TargetResult } from "../types";

import { FindingList } from "./finding-list";

/*
 * One row in the per-target audit table.
 *
 * Shows host / sni / port / numeric score / grade pill. Clicking the
 * chevron expands an inline FindingList. We keep this purely local
 * state — no URL hash, no shared store. Operators typically want to
 * skim grades and only drill in on a problematic target.
 *
 * Score → Badge variant mapping mirrors the SPEC §scoring table and
 * the R.4 brief:
 *   score >= 70  → "positive" (green)
 *   60 <= s < 70 → "warning"  (amber)
 *   score < 60   → "destructive" (red)
 *
 * We map from `grade` rather than recomputing from `score` so the
 * frontend stays consistent with whatever band the backend assigns —
 * if the SPEC's bands ever shift, the wire-level grade is the source
 * of truth.
 */

const variantFor = (
    grade: Grade,
): "positive" | "warning" | "destructive" => {
    if (grade === "green") return "positive";
    if (grade === "yellow") return "warning";
    return "destructive";
};

const gradeLabelFor = (grade: Grade, t: (k: string) => string): string => {
    if (grade === "green") return t("page.reality.score.green");
    if (grade === "yellow") return t("page.reality.score.yellow");
    return t("page.reality.score.red");
};

export interface AuditTargetRowProps {
    target: TargetResult;
}

export const AuditTargetRow: FC<AuditTargetRowProps> = ({ target }) => {
    const { t } = useTranslation();
    const [expanded, setExpanded] = useState(false);
    const expandLabel = t("page.reality.target.expand");
    const collapseLabel = t("page.reality.target.collapse");

    const findingsCount = target.findings.length;
    const issueCount = target.findings.filter(
        (f) => f.severity !== "info",
    ).length;

    return (
        <>
            <tr className="border-b last:border-b-0">
                <td className="px-3 py-2 align-top">
                    <button
                        type="button"
                        className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
                        onClick={() => setExpanded((v) => !v)}
                        aria-expanded={expanded}
                        aria-label={expanded ? collapseLabel : expandLabel}
                    >
                        {expanded ? (
                            <ChevronDown className="h-4 w-4" />
                        ) : (
                            <ChevronRight className="h-4 w-4" />
                        )}
                    </button>
                </td>
                <td className="px-3 py-2 align-top font-mono text-sm">
                    {target.host}
                </td>
                <td className="px-3 py-2 align-top font-mono text-sm">
                    {target.sni}
                </td>
                <td className="px-3 py-2 align-top text-sm tabular-nums">
                    {target.port}
                </td>
                <td className="px-3 py-2 align-top text-sm tabular-nums">
                    <span
                        className={cn(
                            "font-mono",
                            target.grade === "red" && "text-destructive",
                            target.grade === "yellow" &&
                                "text-amber-600 dark:text-amber-500",
                        )}
                    >
                        {target.score}
                    </span>
                </td>
                <td className="px-3 py-2 align-top">
                    <Badge variant={variantFor(target.grade)}>
                        {gradeLabelFor(target.grade, t)}
                    </Badge>
                </td>
                <td className="px-3 py-2 align-top text-xs text-muted-foreground tabular-nums">
                    {issueCount > 0
                        ? `${issueCount}/${findingsCount}`
                        : findingsCount}
                </td>
            </tr>
            {expanded && (
                <tr className="border-b last:border-b-0 bg-muted/20">
                    <td className="px-3 py-0" />
                    <td colSpan={6} className="px-0 py-0">
                        <FindingList findings={target.findings} />
                    </td>
                </tr>
            )}
        </>
    );
};
