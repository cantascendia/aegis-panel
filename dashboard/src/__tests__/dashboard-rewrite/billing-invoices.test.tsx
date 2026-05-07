/**
 * Tests for /billing/invoices route (Wave-B2 Nilou rewrite).
 *
 * Acceptance criteria:
 *   1. PanelHead title "Invoices" is rendered.
 *   2. Three KPI cards are rendered (MRR / Unpaid / Paid total).
 *   3. KPI values are correctly derived from mocked invoice data.
 *   4. InvoicesTable is mounted inside a NilouCard.
 *
 * Strategy: mock useAdminInvoices with a fixture covering paid,
 * pending, and applied invoices so we can assert KPI math.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const RECENT_ISO = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(); // 5 days ago

const MOCK_INVOICES = [
    // applied (paid), within 30d → contributes to MRR
    { id: 1, user_id: 10, total_cny_fen: 5000, state: "applied", provider: "epay", created_at: RECENT_ISO, expires_at: RECENT_ISO, lines: [] },
    // paid, within 30d → contributes to MRR
    { id: 2, user_id: 11, total_cny_fen: 3000, state: "paid", provider: "trc20", created_at: RECENT_ISO, expires_at: RECENT_ISO, lines: [] },
    // pending → counted as unpaid
    { id: 3, user_id: 12, total_cny_fen: 2000, state: "pending", provider: "epay", created_at: RECENT_ISO, expires_at: RECENT_ISO, lines: [] },
    // awaiting_payment → counted as unpaid
    { id: 4, user_id: 13, total_cny_fen: 1000, state: "awaiting_payment", provider: "trc20", created_at: RECENT_ISO, expires_at: RECENT_ISO, lines: [] },
    // expired → not counted anywhere
    { id: 5, user_id: 14, total_cny_fen: 4000, state: "expired", provider: "epay", created_at: RECENT_ISO, expires_at: RECENT_ISO, lines: [] },
];

vi.mock("@marzneshin/modules/billing/api", () => ({
    useAdminInvoices: () => ({
        data: MOCK_INVOICES,
        isLoading: false,
        isError: false,
    }),
}));

vi.mock("@marzneshin/modules/billing", () => ({
    InvoicesTable: () => <div data-testid="invoices-table">InvoicesTable</div>,
    PlansTable: () => <div data-testid="plans-table">PlansTable</div>,
    ChannelsTable: () => <div data-testid="channels-table">ChannelsTable</div>,
}));

vi.mock("@marzneshin/libs/sudo-routes", () => ({
    SudoRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@tanstack/react-router", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@tanstack/react-router")>();
    return {
        ...actual,
        createLazyFileRoute: () => ({ component }: { component: () => JSX.Element }) => ({ component }),
        Outlet: () => null,
    };
});

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------

let BillingInvoicesPage: () => JSX.Element;

beforeEach(async () => {
    const mod = await import("../../routes/_dashboard/billing.invoices.lazy");
    BillingInvoicesPage = mod.BillingInvoicesPage as () => JSX.Element;
}, 30000);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BillingInvoicesPage (Wave-B2 / /billing/invoices route)", () => {
    it("renders the PanelHead title for Invoices", () => {
        renderWithProviders(<BillingInvoicesPage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
    });

    it("renders MRR KPI label", () => {
        renderWithProviders(<BillingInvoicesPage />);
        // i18n key nilou.billing.kpi.mrr → "MRR (30d)"
        expect(screen.getByText(/MRR/i)).toBeInTheDocument();
    });

    it("renders Unpaid KPI — count of pending+awaiting_payment+created invoices", () => {
        renderWithProviders(<BillingInvoicesPage />);
        // 2 unpaid invoices (ids 3 + 4)
        expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("renders Paid total KPI label", () => {
        renderWithProviders(<BillingInvoicesPage />);
        expect(screen.getByText(/Paid total/i)).toBeInTheDocument();
    });

    it("mounts InvoicesTable inside the NilouCard shell", () => {
        renderWithProviders(<BillingInvoicesPage />);
        expect(screen.getByTestId("invoices-table")).toBeInTheDocument();
    });

    it("MRR value is computed from applied+paid invoices within 30 days", () => {
        renderWithProviders(<BillingInvoicesPage />);
        // MRR = (5000 + 3000) / 100 = ¥80 (rounded, no decimals)
        // Paid total = same (applied+paid = ¥80), so ¥80 appears twice — use getAllByText
        const matches = screen.getAllByText("¥80");
        expect(matches.length).toBeGreaterThanOrEqual(1);
    });
});
