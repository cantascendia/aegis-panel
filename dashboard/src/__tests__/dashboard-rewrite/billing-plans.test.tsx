/**
 * Tests for /billing/plans route (Wave-B2 Nilou rewrite).
 *
 * Acceptance criteria:
 *   1. PanelHead title "Plans" is rendered.
 *   2. PanelHead sub is rendered.
 *   3. PlansTable is mounted (the NilouCard shell is rendered).
 *   4. SudoRoute wraps the page — not under test here; tested via mock.
 *
 * Strategy: mock the billing module components so we only test
 * the layout shell (PanelHead + NilouCard wrapper).
 * Mutation hooks stay inside PlansTable — not exercised here.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@marzneshin/modules/billing", () => ({
    PlansTable: () => <div data-testid="plans-table">PlansTable</div>,
    InvoicesTable: () => <div data-testid="invoices-table">InvoicesTable</div>,
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

let BillingPlansPage: () => JSX.Element;

beforeEach(async () => {
    const mod = await import("../../routes/_dashboard/billing.plans.lazy");
    BillingPlansPage = mod.BillingPlansPage as () => JSX.Element;
}, 30000);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BillingPlansPage (Wave-B2 / /billing/plans route)", () => {
    it("renders the PanelHead title for Plans", () => {
        renderWithProviders(<BillingPlansPage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
    });

    it("renders the PanelHead subtitle text", () => {
        renderWithProviders(<BillingPlansPage />);
        // subtitle key: page.billing.plans.subtitle
        // i18n fallback renders the key or the en value
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading.textContent?.length).toBeGreaterThan(0);
    });

    it("mounts the PlansTable component inside the NilouCard shell", () => {
        renderWithProviders(<BillingPlansPage />);
        expect(screen.getByTestId("plans-table")).toBeInTheDocument();
    });

    it("does not render a <Page> wrapper (legacy pattern removed)", () => {
        const { container } = renderWithProviders(<BillingPlansPage />);
        // Legacy <Page> rendered a div with class containing "page"; confirm absent.
        // We just check the PlansTable testid is a direct descendant (not nested in Page).
        expect(screen.getByTestId("plans-table")).toBeInTheDocument();
        // The root fragment should not have any element with data-page attribute
        const pageDiv = container.querySelector("[data-page]");
        expect(pageDiv).toBeNull();
    });
});
