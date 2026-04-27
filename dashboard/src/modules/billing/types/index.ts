/*
 * Types for ops/billing/ backend.
 *
 * Mirrors the Pydantic response shapes from
 * ops/billing/schemas.py. Keep in sync when those change — there's
 * no auto-generation yet (a future A.5/v0.3 chore).
 */

export type PlanKind =
    | "fixed"
    | "flexible_traffic"
    | "flexible_duration";

export interface Plan {
    id: number;
    operator_code: string;
    display_name_en: string;
    display_name_i18n: Record<string, string>;
    kind: PlanKind;
    data_limit_gb: number | null;
    duration_days: number | null;
    price_cny_fen: number;
    enabled: boolean;
    sort_order: number;
    created_at: string;
}

export interface PlanIn {
    operator_code: string;
    display_name_en: string;
    display_name_i18n?: Record<string, string>;
    kind: PlanKind;
    data_limit_gb?: number | null;
    duration_days?: number | null;
    price_cny_fen: number;
    enabled?: boolean;
    sort_order?: number;
}

export interface PlanPatch {
    display_name_en?: string;
    display_name_i18n?: Record<string, string>;
    data_limit_gb?: number | null;
    duration_days?: number | null;
    price_cny_fen?: number;
    enabled?: boolean;
    sort_order?: number;
}

/*
 * PaymentChannel — EPay 码商 credentials. `secret_key` is write-only
 * (never echoed in ChannelOut); rotate by PATCH with the new value.
 */

export type PaymentChannelKind = "epay";

export interface PaymentChannel {
    id: number;
    channel_code: string;
    display_name: string;
    kind: PaymentChannelKind;
    gateway_url: string;
    merchant_id: string;
    enabled: boolean;
    priority: number;
    created_at: string;
}

export interface PaymentChannelIn {
    channel_code: string;
    display_name: string;
    kind?: PaymentChannelKind;
    gateway_url: string;
    merchant_id: string;
    secret_key: string;
    enabled?: boolean;
    priority?: number;
}

export interface PaymentChannelPatch {
    display_name?: string;
    gateway_url?: string;
    merchant_id?: string;
    secret_key?: string;
    enabled?: boolean;
    priority?: number;
}

/*
 * Invoice + audit views. State machine literal values mirror
 * ops/billing/db.py's INVOICE_STATE_* constants; keep in sync on
 * schema changes.
 */

export type InvoiceState =
    | "created"
    | "pending"
    | "awaiting_payment"
    | "paid"
    | "applied"
    | "expired"
    | "cancelled"
    | "failed";

export const INVOICE_TERMINAL_STATES: InvoiceState[] = [
    "applied",
    "expired",
    "cancelled",
    "failed",
];

export interface InvoiceLine {
    id: number;
    plan_id: number;
    quantity: number;
    unit_price_fen_at_purchase: number;
}

export interface Invoice {
    id: number;
    user_id: number;
    total_cny_fen: number;
    state: InvoiceState;
    provider: string;
    provider_invoice_id: string | null;
    payment_url: string | null;
    trc20_memo: string | null;
    trc20_expected_amount_millis: number | null;
    created_at: string;
    paid_at: string | null;
    applied_at: string | null;
    expires_at: string;
    lines: InvoiceLine[];
}

export interface PaymentEvent {
    id: number;
    invoice_id: number;
    event_type: string;
    payload_json: Record<string, unknown>;
    note: string | null;
    created_at: string;
}

export interface InvoiceAdminAction {
    note: string;
}

// ------------------------------------------------------------------
// User-facing types — cart / checkout / polling snapshot.
// Kept in a separate module so the user purchase flow evolves
// independently from admin-CRUD shapes. See `./user.ts` for the
// rationale and the full type list.
// ------------------------------------------------------------------

export type {
    CartLine,
    CheckoutChannelId,
    CheckoutRequest,
    CheckoutResponse,
    ResolvedCartLine,
} from "./user";
