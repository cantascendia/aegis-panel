/**
 * Unit tests for AuditTargetRow.
 *
 * Locks the grade → Badge variant mapping (the on-wire `grade` field
 * is the source of truth; the row never recomputes it from `score`).
 *
 * Coverage targets (issue #102 acceptance):
 *   - grade=green    → variant=positive
 *   - grade=yellow   → variant=warning
 *   - grade=red      → variant=destructive
 *   - score, host, sni, port render in their cells
 *   - findings count summary (issue/total) reflects severity filter
 *
 * The Badge component encodes the variant into a CSS class via cva.
 * We assert on a stable per-variant token (`bg-success`, `bg-accent/20`,
 * `bg-destructive`) — those tokens come from common/components/ui/badge.tsx
 * and are part of the public design vocabulary, so they're a safer
 * assertion target than the variant prop name (which isn't reflected in
 * the DOM).
 *
 * AEGIS fork rebrand (v0.4.6): badge variants migrated from hardcoded
 * Tailwind palette names (`bg-emerald-800`, `bg-amber-200`) to semantic
 * HSL tokens so they inherit the Nilou theme. Tests updated to match.
 *
 * Rendering note: AuditTargetRow returns a <tr>, so the test wraps it
 * in <table><tbody> to avoid React's "tr cannot appear as a child of
 * div" warning.
 */

import { describe, expect, it } from "vitest";
import { render as plainRender, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import "@testing-library/jest-dom";

import i18n from "@marzneshin/features/i18n";

import type { Finding, Grade, TargetResult } from "../types";
import { AuditTargetRow } from "./audit-target-row";

const FINDING_OK: Finding = {
    check: "sni_coldness",
    ok: true,
    severity: "info",
    score_delta: 0,
    evidence: "SNI is cold (rank > 1M)",
    remediation: "",
    data: {},
};

const FINDING_WARN: Finding = {
    check: "asn_match",
    ok: false,
    severity: "warning",
    score_delta: -10,
    evidence: "ASN drift",
    remediation: "Pick same-ASN SNI",
    data: {},
};

const FINDING_CRIT: Finding = {
    check: "port_canonical",
    ok: false,
    severity: "critical",
    score_delta: -25,
    evidence: "Non-canonical port",
    remediation: "Use 443",
    data: {},
};

function makeTarget(
    grade: Grade,
    score: number,
    findings: Finding[] = [],
    overrides: Partial<TargetResult> = {},
): TargetResult {
    return {
        host: "example.com",
        sni: "example.com",
        port: 443,
        score,
        grade,
        findings,
        ...overrides,
    };
}

function renderRow(target: TargetResult) {
    return plainRender(
        <I18nextProvider i18n={i18n}>
            <table>
                <tbody>
                    <AuditTargetRow target={target} />
                </tbody>
            </table>
        </I18nextProvider>,
    );
}

describe("AuditTargetRow", () => {
    it("maps grade=green to the positive Badge variant", () => {
        renderRow(makeTarget("green", 95, [FINDING_OK]));
        // page.reality.score.green is the badge label key.
        const badge = screen.getByText("page.reality.score.green");
        expect(badge).toBeInTheDocument();
        // positive variant ships with bg-success (semantic HSL token).
        expect(badge.className).toMatch(/bg-success/);
    });

    it("maps grade=yellow to the warning Badge variant", () => {
        renderRow(makeTarget("yellow", 65, [FINDING_WARN]));
        const badge = screen.getByText("page.reality.score.yellow");
        expect(badge).toBeInTheDocument();
        // warning variant ships with bg-accent/20 (Nilou gold tint).
        expect(badge.className).toMatch(/bg-accent\/20/);
    });

    it("maps grade=red to the destructive Badge variant", () => {
        renderRow(makeTarget("red", 40, [FINDING_CRIT]));
        const badge = screen.getByText("page.reality.score.red");
        expect(badge).toBeInTheDocument();
        expect(badge.className).toMatch(/bg-destructive/);
    });

    it("renders the numeric score prominently", () => {
        renderRow(makeTarget("yellow", 65));
        // Score lives in a font-mono cell; getByText with exact match.
        const scoreCell = screen.getByText("65");
        expect(scoreCell).toBeInTheDocument();
        expect(scoreCell.className).toMatch(/font-mono/);
    });

    it("renders host, sni, and port values from the wire payload", () => {
        renderRow(
            makeTarget(
                "green",
                90,
                [],
                {
                    host: "fastly.com",
                    sni: "fastly.com",
                    port: 8443,
                },
            ),
        );
        // host + sni are identical here so getAllByText to match both.
        expect(screen.getAllByText("fastly.com").length).toBeGreaterThanOrEqual(2);
        expect(screen.getByText("8443")).toBeInTheDocument();
    });

    it("displays issue/total when findings include warnings or critical", () => {
        renderRow(
            makeTarget("yellow", 65, [
                FINDING_OK,
                FINDING_WARN,
                FINDING_CRIT,
            ]),
        );
        // 2 issues (warning + critical) out of 3 total findings → "2/3".
        expect(screen.getByText("2/3")).toBeInTheDocument();
    });

    it("displays only the total when all findings are info-level", () => {
        renderRow(makeTarget("green", 100, [FINDING_OK, FINDING_OK]));
        // No issues → just "2".
        expect(screen.getByText("2")).toBeInTheDocument();
    });
});
