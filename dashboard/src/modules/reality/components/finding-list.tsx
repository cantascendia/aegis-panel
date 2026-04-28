import { type FC } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@marzneshin/common/utils";

import type { Finding, Severity } from "../types";

/*
 * Expandable list of findings under a target row.
 *
 * Severity → visual mapping per SPEC scoring table & R.4 brief:
 *   info     → muted gray bullet — informational, score_delta == 0
 *   warning  → amber bullet
 *   critical → red bullet
 *
 * Each finding renders three lines:
 *   - bullet + check name + score_delta tag (e.g. "-15")
 *   - evidence (single human-readable sentence from backend)
 *   - remediation (omitted if empty — info findings often have none)
 *
 * Backend check identifiers are lowercase snake_case (`sni_coldness`,
 * `asn_match`, etc.). We render via a `page.reality.check.<name>`
 * lookup with a fallback to the raw identifier — same pattern the
 * health page uses for subsystems. New backend checks land in the
 * dashboard without a frontend change.
 */

const bulletClassFor = (severity: Severity): string => {
    if (severity === "critical") return "bg-destructive";
    if (severity === "warning") return "bg-amber-500";
    return "bg-muted-foreground";
};

const textClassFor = (severity: Severity): string => {
    if (severity === "critical") return "text-destructive";
    if (severity === "warning") return "text-amber-600 dark:text-amber-500";
    return "text-muted-foreground";
};

const checkLabel = (name: string, t: (k: string) => string): string => {
    const key = `page.reality.check.${name}`;
    const translated = t(key);
    return translated === key ? name : translated;
};

// Drift-gate visibility (per L-017): the dynamic key above is invisible
// to the line-based extractor in tools/check_translations.sh. The
// literals below mirror every check identifier the backend emits, so
// the JSON entries register as referenced. Tree-shaken in prod.
const _drift_gate_checks = (t: (k: string) => string) => [
    t("page.reality.check.sni_coldness"),
    t("page.reality.check.asn_match"),
    t("page.reality.check.port_canonical"),
    t("page.reality.check.shortid_compliance"),
    t("page.reality.check.timeout_config"),
];
void _drift_gate_checks;

export interface FindingListProps {
    findings: Finding[];
}

export const FindingList: FC<FindingListProps> = ({ findings }) => {
    const { t } = useTranslation();
    const remediationLabel = t("page.reality.finding.remediation");
    const noFindingsText = t("page.reality.finding.empty");

    if (findings.length === 0) {
        return (
            <p className="px-3 py-2 text-sm text-muted-foreground">
                {noFindingsText}
            </p>
        );
    }

    return (
        <ul className="space-y-3 px-3 py-3">
            {findings.map((f) => (
                <li key={f.check} className="flex gap-3 text-sm">
                    <span
                        className={cn(
                            "mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full",
                            bulletClassFor(f.severity),
                        )}
                        aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-2">
                            <span
                                className={cn(
                                    "font-medium",
                                    textClassFor(f.severity),
                                )}
                            >
                                {checkLabel(f.check, t)}
                            </span>
                            {f.score_delta !== 0 && (
                                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                                    {f.score_delta}
                                </span>
                            )}
                        </div>
                        <p className="text-muted-foreground">{f.evidence}</p>
                        {f.remediation && (
                            <p className="mt-0.5 text-xs text-muted-foreground">
                                <span className="font-medium">
                                    {remediationLabel}:
                                </span>{" "}
                                {f.remediation}
                            </p>
                        )}
                    </div>
                </li>
            ))}
        </ul>
    );
};
