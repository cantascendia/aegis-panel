/**
 * Unit tests for AuditSummaryCard.
 *
 * Locks the worst-score → grade colour boundaries (60 / 70 cutoffs)
 * which the page header relies on for the at-a-glance health colour.
 * If a refactor pushes a target's worst_score across the boundary by
 * one point, this is what should fail.
 *
 * Coverage targets (issue #102 acceptance):
 *   - worst_score = 70 → green (boundary green)
 *   - worst_score = 69 → yellow (boundary yellow upper)
 *   - worst_score = 60 → yellow (boundary yellow lower)
 *   - worst_score = 59 → red (boundary red)
 *   - empty targets array → no_targets state (summary still renders, neutral)
 *   - all-100 (perfect) → green
 *
 * The card encodes the grade in two visible signals:
 *   1. The accent CSS class on the worst-score stat (text-emerald-700,
 *      text-amber-600, or text-destructive)
 *   2. A `title` tooltip "grade=green|yellow|red" attached to the same
 *      cell when total > 0
 * We assert on (2) because it's stable wire-level vocabulary, not a
 * Tailwind class that a designer might rename.
 */

import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import { renderWithProviders } from "@marzneshin/test-utils/render";

import type { ReportSummary } from "../types";
import { AuditSummaryCard } from "./audit-summary-card";

function makeSummary(
    overrides: Partial<ReportSummary> = {},
): ReportSummary {
    return {
        total: 1,
        green: 0,
        yellow: 0,
        red: 0,
        worst_score: 100,
        ...overrides,
    };
}

function renderCard(overrides?: {
    summary?: ReportSummary | null;
    auditedAt?: string | null;
    isPending?: boolean;
    onRun?: () => void;
}) {
    const onRun = overrides?.onRun ?? vi.fn();
    const utils = renderWithProviders(
        <AuditSummaryCard
            summary={overrides?.summary ?? null}
            auditedAt={overrides?.auditedAt ?? null}
            isPending={overrides?.isPending ?? false}
            onRun={onRun}
        />,
    );
    return { ...utils, onRun };
}

describe("AuditSummaryCard", () => {
    it("shows green grade when worst_score is 70 (boundary green)", () => {
        renderCard({
            summary: makeSummary({ total: 1, green: 1, worst_score: 70 }),
        });
        const stat = screen.getByTitle("grade=green");
        expect(stat).toBeInTheDocument();
        // Score is rendered inside the stat cell.
        expect(stat).toHaveTextContent("70");
    });

    it("shows yellow grade when worst_score is 69 (boundary yellow upper)", () => {
        renderCard({
            summary: makeSummary({ total: 1, yellow: 1, worst_score: 69 }),
        });
        const stat = screen.getByTitle("grade=yellow");
        expect(stat).toBeInTheDocument();
        expect(stat).toHaveTextContent("69");
    });

    it("shows yellow grade when worst_score is 60 (boundary yellow lower)", () => {
        renderCard({
            summary: makeSummary({ total: 1, yellow: 1, worst_score: 60 }),
        });
        const stat = screen.getByTitle("grade=yellow");
        expect(stat).toBeInTheDocument();
        expect(stat).toHaveTextContent("60");
    });

    it("shows red grade when worst_score is 59 (boundary red)", () => {
        renderCard({
            summary: makeSummary({ total: 1, red: 1, worst_score: 59 }),
        });
        const stat = screen.getByTitle("grade=red");
        expect(stat).toBeInTheDocument();
        expect(stat).toHaveTextContent("59");
    });

    it("renders empty-targets summary without a grade tooltip (total=0 neutral)", () => {
        // total=0 path: the worst-score stat suppresses the
        // grade=... tooltip and renders muted text. The summary block
        // still renders (per component contract) so operators see
        // "0/0/0/0".
        renderCard({
            summary: makeSummary({
                total: 0,
                green: 0,
                yellow: 0,
                red: 0,
                worst_score: 0,
            }),
        });
        // No grade tooltip in the empty case.
        expect(screen.queryByTitle(/grade=/)).not.toBeInTheDocument();
        // But the summary stats are visible (multiple zeros render —
        // we just assert at least one summary cell is present).
        expect(
            screen.getByText("page.reality.summary.total"),
        ).toBeInTheDocument();
    });

    it("shows green when worst_score is 100 (perfect)", () => {
        renderCard({
            summary: makeSummary({ total: 5, green: 5, worst_score: 100 }),
        });
        const stat = screen.getByTitle("grade=green");
        expect(stat).toBeInTheDocument();
        expect(stat).toHaveTextContent("100");
    });

    it("hides the summary grid until a report is supplied (pre-audit state)", () => {
        renderCard({ summary: null });
        // No grade tooltip and no total label until summary lands.
        expect(screen.queryByTitle(/grade=/)).not.toBeInTheDocument();
        expect(
            screen.queryByText("page.reality.summary.total"),
        ).not.toBeInTheDocument();
        // Run button is rendered up front.
        expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("disables the run button while a mutation is pending", () => {
        renderCard({ isPending: true });
        expect(screen.getByRole("button")).toBeDisabled();
    });
});
