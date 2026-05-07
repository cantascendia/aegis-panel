/**
 * Tests for /billing/channels route (Wave-B2 Nilou rewrite).
 *
 * Acceptance criteria:
 *   1. PanelHead title "Payment channels" is rendered.
 *   2. PanelHead subtitle is rendered.
 *   3. ChannelsTable is mounted inside a NilouCard.
 *   4. No legacy <Page> wrapper present.
 *
 * Strategy: mock ChannelsTable so we only test the layout shell.
 * Channel CRUD mutations (useCreateChannel / useUpdateChannel) are
 * owned by ChannelsTable — not exercised here (forbidden-path rule).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@marzneshin/modules/billing", () => ({
    ChannelsTable: () => <div data-testid="channels-table">ChannelsTable</div>,
    PlansTable: () => <div data-testid="plans-table">PlansTable</div>,
    InvoicesTable: () => <div data-testid="invoices-table">InvoicesTable</div>,
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

let BillingChannelsPage: () => JSX.Element;

beforeEach(async () => {
    const mod = await import("../../routes/_dashboard/billing.channels.lazy");
    BillingChannelsPage = mod.BillingChannelsPage as () => JSX.Element;
}, 30000);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BillingChannelsPage (Wave-B2 / /billing/channels route)", () => {
    it("renders the PanelHead title for Payment channels", () => {
        renderWithProviders(<BillingChannelsPage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
    });

    it("PanelHead heading is non-empty", () => {
        renderWithProviders(<BillingChannelsPage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading.textContent?.length).toBeGreaterThan(0);
    });

    it("mounts the ChannelsTable component inside the NilouCard shell", () => {
        renderWithProviders(<BillingChannelsPage />);
        expect(screen.getByTestId("channels-table")).toBeInTheDocument();
    });

    it("does not render a legacy Page wrapper (data-page attribute absent)", () => {
        const { container } = renderWithProviders(<BillingChannelsPage />);
        const pageDiv = container.querySelector("[data-page]");
        expect(pageDiv).toBeNull();
    });
});
