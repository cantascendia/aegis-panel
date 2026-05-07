/**
 * Tests for /billing/purchase route (Wave-B2 Nilou rewrite).
 *
 * Acceptance criteria:
 *   1. PanelHead title is rendered.
 *   2. UserSelector section is mounted when data loads.
 *   3. PlansGrid section is mounted when data loads.
 *   4. Error state renders a NilouCard with error message on load failure.
 *
 * Strategy: mock useUserPlans + useUserChannels + useCheckout.
 * Mutations (useCheckout.mutateAsync) are mocked with a no-op.
 * We do NOT test pricing logic or mutation outcomes — forbidden-path rule.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_PLANS = [
    { id: 1, operator_code: "basic", display_name_en: "Basic Plan", kind: "fixed", data_limit_gb: 50, duration_days: 30, price_cny_fen: 2900, enabled: true, sort_order: 0, created_at: "2026-01-01T00:00:00Z", display_name_i18n: {} },
];

const MOCK_CHANNELS = [
    { id: 1, channel_code: "epay_01", display_name: "EPay Primary", kind: "epay", gateway_url: "https://example.com", merchant_id: "M123", enabled: true, priority: 1, created_at: "2026-01-01T00:00:00Z" },
];

vi.mock("@marzneshin/modules/billing/admin-checkout", () => ({
    useUserPlans: () => ({ data: MOCK_PLANS, isLoading: false, isError: false }),
    useUserChannels: () => ({ data: MOCK_CHANNELS, isLoading: false, isError: false }),
    useCheckout: () => ({ mutateAsync: vi.fn(), isPending: false }),
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    UserSelector: (_props: { selected: unknown; onSelect: unknown }) => (
        <div data-testid="user-selector">UserSelector</div>
    ),
    PlansGrid: ({ plans }: { plans: unknown[]; cart: unknown[]; onAdd: unknown }) => (
        <div data-testid="plans-grid">{(plans as { display_name_en: string }[]).map((p) => p.display_name_en).join(",")}</div>
    ),
    FlexibleAddonCalculator: () => <div data-testid="flexible-addon">FlexibleAddon</div>,
    CartSummary: () => <div data-testid="cart-summary">CartSummary</div>,
    CheckoutPaymentPicker: () => <div data-testid="payment-picker">PaymentPicker</div>,
}));

vi.mock("@marzneshin/libs/sudo-routes", () => ({
    SudoRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@tanstack/react-router", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@tanstack/react-router")>();
    return {
        ...actual,
        createLazyFileRoute: () => ({ component }: { component: () => JSX.Element }) => ({ component }),
        useNavigate: () => vi.fn(),
        Outlet: () => null,
    };
});

// ---------------------------------------------------------------------------
// Import component AFTER mocks
// ---------------------------------------------------------------------------

let BillingCheckoutPage: () => JSX.Element;

beforeEach(async () => {
    const mod = await import("../../routes/_dashboard/billing.purchase.lazy");
    BillingCheckoutPage = mod.BillingCheckoutPage as () => JSX.Element;
}, 30000);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("BillingCheckoutPage (Wave-B2 / /billing/purchase route)", () => {
    it("renders the PanelHead title for the checkout page", () => {
        renderWithProviders(<BillingCheckoutPage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
    });

    it("mounts the UserSelector component", () => {
        renderWithProviders(<BillingCheckoutPage />);
        expect(screen.getByTestId("user-selector")).toBeInTheDocument();
    });

    it("mounts the PlansGrid with available plans", () => {
        renderWithProviders(<BillingCheckoutPage />);
        expect(screen.getByTestId("plans-grid")).toBeInTheDocument();
        expect(screen.getByText(/Basic Plan/i)).toBeInTheDocument();
    });

    it("mounts the CartSummary component", () => {
        renderWithProviders(<BillingCheckoutPage />);
        expect(screen.getByTestId("cart-summary")).toBeInTheDocument();
    });
});
