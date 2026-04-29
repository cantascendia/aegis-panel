/**
 * Unit tests for AuditReportTable.
 *
 * Locks the orchestration contract:
 *   - loading state during the mutation
 *   - 401/403 → friendly auth error message
 *   - 504 → timeout error message (WHOIS-hang relay)
 *   - other status → generic error message
 *   - empty pre-audit state (no report yet)
 *   - report with zero targets → no_targets state
 *   - report with targets → table renders one row per target
 *
 * We mock `../api` (the useRealityAudit hook) so we can shape the
 * mutation state directly. This keeps the test fast and deterministic
 * — fetch / FetchError plumbing belongs in api-layer tests, not here.
 *
 * The component branches on `instanceof FetchError`; we construct
 * FetchError instances directly and seed `response.status` to drive
 * the auth/timeout/generic branches.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { FetchError } from "ofetch";

import { renderWithProviders } from "@marzneshin/test-utils/render";

import type { Report, TargetResult } from "../types";

// Mock the api module so we control useRealityAudit's return value
// per-test. The component imports from "../api" which re-exports
// useRealityAudit from "../api/audit.mutate".
const mockMutate = vi.fn();
let mockState: {
    data: Report | null;
    isPending: boolean;
    isError: boolean;
    error: unknown;
} = {
    data: null,
    isPending: false,
    isError: false,
    error: null,
};

vi.mock("../api", () => ({
    useRealityAudit: () => ({
        mutate: mockMutate,
        data: mockState.data ?? undefined,
        isPending: mockState.isPending,
        isError: mockState.isError,
        error: mockState.error,
    }),
}));

// Imported AFTER vi.mock so the mock is in effect.
import { AuditReportTable } from "./audit-report-table";

function setMutationState(partial: Partial<typeof mockState>) {
    mockState = { ...mockState, ...partial };
}

function makeTarget(overrides: Partial<TargetResult> = {}): TargetResult {
    return {
        host: "example.com",
        sni: "example.com",
        port: 443,
        score: 95,
        grade: "green",
        findings: [],
        ...overrides,
    };
}

function makeReport(targets: TargetResult[] = []): Report {
    const greenN = targets.filter((t) => t.grade === "green").length;
    const yellowN = targets.filter((t) => t.grade === "yellow").length;
    const redN = targets.filter((t) => t.grade === "red").length;
    const worst = targets.length
        ? Math.min(...targets.map((t) => t.score))
        : 0;
    return {
        schema_version: "1.0",
        audited_at: "2026-04-29T00:00:00Z",
        source: "db",
        targets,
        summary: {
            total: targets.length,
            green: greenN,
            yellow: yellowN,
            red: redN,
            worst_score: worst,
        },
    };
}

/**
 * Build a real FetchError with a fake response that carries the
 * status. ofetch's FetchError reads `err.response?.status`.
 */
function makeFetchError(status: number): FetchError {
    const err = new FetchError(`HTTP ${status}`);
    // Cast around the readonly response so we can stub status.
    (err as unknown as { response: { status: number } }).response = {
        status,
    };
    return err;
}

describe("AuditReportTable", () => {
    beforeEach(() => {
        // Reset between cases so leakage doesn't muddy assertions.
        mockMutate.mockReset();
        mockState = {
            data: null,
            isPending: false,
            isError: false,
            error: null,
        };
    });

    it("shows the empty pre-audit state before any mutation", () => {
        renderWithProviders(<AuditReportTable />);
        expect(screen.getByText("page.reality.empty")).toBeInTheDocument();
        // No table yet.
        expect(
            screen.queryByText("page.reality.column.host"),
        ).not.toBeInTheDocument();
    });

    it("disables the run button while the mutation is pending", () => {
        setMutationState({ isPending: true });
        renderWithProviders(<AuditReportTable />);
        // The single button on the page belongs to the summary card.
        expect(screen.getByRole("button")).toBeDisabled();
        // The "empty" placeholder hides during pending.
        expect(
            screen.queryByText("page.reality.empty"),
        ).not.toBeInTheDocument();
    });

    it("surfaces the auth error message for a 401", () => {
        setMutationState({
            isError: true,
            error: makeFetchError(401),
        });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.error.unauthorized"),
        ).toBeInTheDocument();
    });

    it("surfaces the auth error message for a 403", () => {
        setMutationState({
            isError: true,
            error: makeFetchError(403),
        });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.error.unauthorized"),
        ).toBeInTheDocument();
    });

    it("surfaces the timeout error message for a 504", () => {
        setMutationState({
            isError: true,
            error: makeFetchError(504),
        });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.error.timeout"),
        ).toBeInTheDocument();
    });

    it("surfaces the generic error message for a 500", () => {
        setMutationState({
            isError: true,
            error: makeFetchError(500),
        });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.error.failed"),
        ).toBeInTheDocument();
    });

    it("surfaces the generic error message for a non-FetchError throwable", () => {
        setMutationState({
            isError: true,
            error: new Error("network down"),
        });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.error.failed"),
        ).toBeInTheDocument();
    });

    it("shows the no_targets state when the report has zero targets", () => {
        setMutationState({ data: makeReport([]) });
        renderWithProviders(<AuditReportTable />);
        expect(
            screen.getByText("page.reality.no_targets"),
        ).toBeInTheDocument();
        // Still no table.
        expect(
            screen.queryByText("page.reality.column.host"),
        ).not.toBeInTheDocument();
    });

    it("renders an all-green report (perfect fixture-shape) as a populated table", () => {
        // Inline fixture mirroring hardening/reality/fixtures/perfect.json
        // shape (all targets graded green / score 100). We don't read the
        // backend file because that lives outside dashboard/src and would
        // couple the dashboard test to backend pathing.
        const report = makeReport([
            makeTarget({
                host: "fastly.com",
                sni: "fastly.com",
                grade: "green",
                score: 100,
            }),
            makeTarget({
                host: "cloudflare.com",
                sni: "cloudflare.com",
                grade: "green",
                score: 100,
            }),
        ]);
        setMutationState({ data: report });
        renderWithProviders(<AuditReportTable />);
        // Table headers visible.
        expect(
            screen.getByText("page.reality.column.host"),
        ).toBeInTheDocument();
        // Two rows of green badges.
        const greenBadges = screen.getAllByText(
            "page.reality.score.green",
        );
        expect(greenBadges).toHaveLength(2);
        // No empty / no-targets / error placeholders bleed through.
        expect(
            screen.queryByText("page.reality.no_targets"),
        ).not.toBeInTheDocument();
        expect(
            screen.queryByText("page.reality.empty"),
        ).not.toBeInTheDocument();
    });

    it("renders a broken-fixture report with red findings rows", () => {
        // Inline broken fixture: one target red (score 40), one yellow (65).
        const report = makeReport([
            makeTarget({
                host: "bad-host.example",
                sni: "bad-host.example",
                grade: "red",
                score: 40,
                findings: [
                    {
                        check: "port_canonical",
                        ok: false,
                        severity: "critical",
                        score_delta: -25,
                        evidence: "Non-canonical port",
                        remediation: "Use 443",
                        data: {},
                    },
                ],
            }),
            makeTarget({
                host: "warn-host.example",
                sni: "warn-host.example",
                grade: "yellow",
                score: 65,
                findings: [],
            }),
        ]);
        setMutationState({ data: report });
        renderWithProviders(<AuditReportTable />);
        // One red and one yellow badge visible.
        expect(
            screen.getByText("page.reality.score.red"),
        ).toBeInTheDocument();
        expect(
            screen.getByText("page.reality.score.yellow"),
        ).toBeInTheDocument();
    });
});
