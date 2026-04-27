/*
 * Cart / checkout types for the admin-on-behalf-of-user flow
 * (BRIEF-billing-user-auth-blocker.md option A — the chosen path
 * after PR #41's user-self-serve skeleton hit the user-auth gap).
 *
 * These mirror the backend Pydantic schemas in `ops/billing/
 * schemas.py` (`CheckoutLineIn`, `CheckoutIn`, `CheckoutOut`).
 * Kept in a separate module from `./index.ts` so admin-CRUD shapes
 * and checkout shapes evolve independently.
 *
 * No fixture-time / mock shapes here — those moved to test fixtures
 * after the flip-on. See `user/fixtures.ts` for what remains
 * (component-test seed data only).
 */

import type { Plan } from "./index";

/**
 * One cart line. Local UI state until checkout. Wire shape sent
 * inside `CheckoutRequest.lines` matches `CheckoutLineIn` on the
 * backend.
 */
export interface CartLine {
    plan_id: number;
    quantity: number;
}

/**
 * Snapshot augmented with the resolved plan for display.
 * UI-only convenience; not on the wire.
 */
export interface ResolvedCartLine {
    plan: Plan;
    quantity: number;
    /** quantity × plan.price_cny_fen — precomputed so the total bar
     *  doesn't recompute on every render. */
    line_total_fen: number;
}

/**
 * Tagged channel identifier emitted by `CheckoutPaymentPicker.onPay`.
 * The picker collapses (channel_kind, sub_id) into a single string
 * to keep the callback narrow:
 *   - `"trc20"` for the singleton TRC20 channel
 *   - `"epay:<channel_code>"` for one of the configured 码商 rows
 *
 * The route handler splits this back into `channel_code` for
 * `CheckoutRequest.channel_code` (which is just the bare code; the
 * `epay:` prefix is a UI grouping device, not on the wire).
 */
export type CheckoutChannelId = "trc20" | `epay:${string}`;

/**
 * `POST /api/billing/cart/checkout` request body. Admin-initiated
 * (per BRIEF option A): admin picks `user_id` via the UserSelector
 * component, the backend uses it to attach the new Invoice to the
 * VPN user. Backend dep is `SudoAdminDep`.
 *
 * `success_url` and `cancel_url` are passed verbatim to the EPay
 * 码商 as the user redirect targets. For TRC20 the backend ignores
 * cancel_url; success_url is unused too (TRC20 stays in-panel).
 *
 * `subject` is the human-readable label that EPay 码商 shows on
 * the payment page; defaults to a sensible string server-side if
 * omitted.
 */
export interface CheckoutRequest {
    user_id: number;
    channel_code: string;
    lines: CartLine[];
    success_url: string;
    cancel_url: string;
    subject?: string;
}

/**
 * `POST /api/billing/cart/checkout` response. Mirrors `CheckoutOut`.
 *
 * For EPay: `payment_url` is the 码商-hosted redirect; admin copies
 * it and pings the user via Telegram / email.
 * For TRC20: `payment_url` is an in-panel route that renders the
 * QR + memo + countdown screen.
 */
export interface CheckoutResponse {
    invoice_id: number;
    total_cny_fen: number;
    payment_url: string;
    provider_invoice_id: string;
    state: string;
    expires_at: string;
}
