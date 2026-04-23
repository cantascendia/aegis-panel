/*
 * User-facing billing types.
 *
 * Distinct from the admin types in `./index.ts` so the user purchase
 * flow evolves independently from admin-CRUD shapes. Admin types
 * (Plan, PaymentChannel, Invoice, etc.) are reused as-is for
 * user-side reads; only the cart / checkout request/response shapes
 * are genuinely user-specific.
 *
 * The backend endpoints that return these shapes are tracked in
 * `docs/ai-cto/SPEC-billing-a2-a3.md` (A.2.2 `/api/billing/cart/
 * checkout`, A.3.1 `/api/billing/invoices/me`, `/api/billing/plans`).
 * The types MAY need to rev when A.2.2 merges — keep an eye on the
 * diff.
 */

import type { InvoiceState, Plan } from "./index";

/**
 * One line in the user's cart. Local state only until checkout —
 * the backend receives the serialized form as {plan_id, quantity}
 * tuples on POST /api/billing/cart/checkout.
 */
export interface CartLine {
    plan_id: number;
    quantity: number;
}

/**
 * Snapshot of a cart line augmented with the resolved plan, used by
 * CartSummary / CheckoutPaymentPicker components. Kept out of the
 * wire protocol — it's a UI-only convenience type.
 */
export interface ResolvedCartLine {
    plan: Plan;
    quantity: number;
    /** quantity × plan.price_cny_fen — precomputed so the total bar
     *  doesn't recompute on every render. */
    line_total_fen: number;
}

/**
 * Payment channel choice at checkout time. Mirrors the backend
 * union:
 * - `"trc20"` — self-hosted USDT polling
 * - `"epay:<channel_code>"` — one configured 码商 (multiple can be
 *   active; the user picks one).
 */
export type CheckoutChannelId = "trc20" | `epay:${string}`;

/**
 * POST /api/billing/cart/checkout request body.
 */
export interface CheckoutRequest {
    lines: CartLine[];
    channel: CheckoutChannelId;
}

/**
 * POST /api/billing/cart/checkout response.
 *
 * For EPay the user is redirected to `payment_url` (外部 码商 页面).
 * For TRC20 `payment_url` is an in-app route like
 * `/dashboard/billing/invoice/{id}` that renders the QR / memo /
 * countdown screen locally.
 */
export interface CheckoutResponse {
    invoice_id: number;
    payment_url: string;
}

/**
 * Light derived type for the "my invoices" list row — trims fields
 * the history view doesn't need so we don't over-fetch. Backend may
 * return the full Invoice shape; UI picks these fields.
 */
export interface MyInvoiceRow {
    id: number;
    total_cny_fen: number;
    state: InvoiceState;
    provider: string;
    created_at: string;
    expires_at: string;
    paid_at: string | null;
}

/**
 * Polling-aware invoice view — superset of Invoice used by
 * InvoicePollQuery. Fields below are always present on the backend
 * response; the split exists so the polling component can render a
 * narrower interface without importing the full Invoice shape.
 */
export interface InvoicePollSnapshot {
    id: number;
    state: InvoiceState;
    provider: string;
    total_cny_fen: number;
    trc20_memo: string | null;
    trc20_expected_amount_millis: number | null;
    expires_at: string;
    paid_at: string | null;
    applied_at: string | null;
}
