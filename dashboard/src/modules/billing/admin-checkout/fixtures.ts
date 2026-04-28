/*
 * Component-test seed data for billing admin checkout components.
 *
 * History: created in PR #41 to back the user-self-serve UI mock
 * mode. After BRIEF-billing-user-auth-blocker.md option A flipped
 * the design to admin-on-behalf-of-user, the API hooks now hit real
 * backend endpoints — no runtime fixture path remains. These exports
 * survive solely to give component tests stable input data
 * (see `*.test.tsx` siblings).
 *
 * Pricing in integer fen (1/100 CNY). TRC20 amounts in USDT-millis
 * (1/1000 USDT). Matches `ops/billing/db.py` money invariants.
 */

import type {
    Invoice,
    PaymentChannel,
    Plan,
} from "../types";

export const FIXTURE_PLANS: Plan[] = [
    {
        id: 101,
        operator_code: "starter-30",
        display_name_en: "Starter · 30 GB / 30 d",
        display_name_i18n: { "zh-cn": "入门 · 30 GB / 30 天" },
        kind: "fixed",
        data_limit_gb: 30,
        duration_days: 30,
        price_cny_fen: 3500, // ¥35.00
        enabled: true,
        sort_order: 10,
        created_at: "2026-04-01T00:00:00Z",
    },
    {
        id: 102,
        operator_code: "pro-100",
        display_name_en: "Pro · 100 GB / 30 d",
        display_name_i18n: { "zh-cn": "专业 · 100 GB / 30 天" },
        kind: "fixed",
        data_limit_gb: 100,
        duration_days: 30,
        price_cny_fen: 8800, // ¥88.00
        enabled: true,
        sort_order: 20,
        created_at: "2026-04-01T00:00:00Z",
    },
    {
        id: 103,
        operator_code: "family-300",
        display_name_en: "Family · 300 GB / 30 d",
        display_name_i18n: { "zh-cn": "家庭 · 300 GB / 30 天" },
        kind: "fixed",
        data_limit_gb: 300,
        duration_days: 30,
        price_cny_fen: 19800, // ¥198.00
        enabled: true,
        sort_order: 30,
        created_at: "2026-04-01T00:00:00Z",
    },
    {
        id: 201,
        operator_code: "flex-gb",
        display_name_en: "Extra traffic (per GB)",
        display_name_i18n: { "zh-cn": "额外流量 (每 GB)" },
        kind: "flexible_traffic",
        data_limit_gb: 1,
        duration_days: null,
        price_cny_fen: 50, // ¥0.50/GB
        enabled: true,
        sort_order: 100,
        created_at: "2026-04-01T00:00:00Z",
    },
    {
        id: 202,
        operator_code: "flex-day",
        display_name_en: "Extra days (per day)",
        display_name_i18n: { "zh-cn": "额外天数 (每天)" },
        kind: "flexible_duration",
        data_limit_gb: null,
        duration_days: 1,
        price_cny_fen: 100, // ¥1.00/day
        enabled: true,
        sort_order: 110,
        created_at: "2026-04-01T00:00:00Z",
    },
];

export const FIXTURE_CHANNELS: PaymentChannel[] = [
    {
        id: 1,
        channel_code: "zpay1",
        display_name: "Zpay 主通道",
        kind: "epay",
        gateway_url: "https://zpay.example.com",
        merchant_id: "10000001",
        enabled: true,
        priority: 20,
        created_at: "2026-04-01T00:00:00Z",
    },
    {
        id: 2,
        channel_code: "epay-backup",
        display_name: "Epay 备用",
        kind: "epay",
        gateway_url: "https://epay-backup.example.com",
        merchant_id: "20000002",
        enabled: true,
        priority: 10,
        created_at: "2026-04-01T00:00:00Z",
    },
    // TRC20 is represented as a pseudo-channel by the user UI so the
    // picker tabs (EPay / TRC20) can iterate a uniform list. The
    // backend's `GET /api/billing/channels` will NOT return this
    // row — it's synthesized by the user API hook when TRC20 is
    // globally enabled. Kind stays "epay" in the type; the channel
    // picker component detects the synthetic row by `channel_code === "trc20"`.
    // NOTE: in the real hook, this synth-row insertion happens in
    // `user/api/channels.query.ts`; this fixture is just the merged
    // result for UI preview.
    {
        id: -1,
        channel_code: "trc20",
        display_name: "USDT (TRC20)",
        kind: "epay",
        gateway_url: "",
        merchant_id: "",
        enabled: true,
        priority: 30,
        created_at: "2026-04-01T00:00:00Z",
    },
];

/** A fresh awaiting-payment TRC20 invoice — useful for previewing
 *  the TRC20 payment screen without actually hitting the backend. */
export const FIXTURE_AWAITING_TRC20_INVOICE: Invoice = {
    id: 9001,
    user_id: 42,
    total_cny_fen: 3500,
    state: "awaiting_payment",
    provider: "trc20",
    provider_invoice_id: "AEG9001XZ",
    payment_url: "/dashboard/billing/invoice/9001",
    trc20_memo: "AEG9001XZ",
    trc20_expected_amount_millis: 4861, // ~4.861 USDT at 7.20 CNY/USDT
    created_at: "2026-04-23T10:00:00Z",
    paid_at: null,
    applied_at: null,
    expires_at: "2026-04-23T10:30:00Z",
    lines: [
        {
            id: 1,
            plan_id: 101,
            quantity: 1,
            unit_price_fen_at_purchase: 3500,
        },
    ],
};

// Note: the `FIXTURE_MY_INVOICES` array (PR #41) was deleted as part
// of the BRIEF-billing-user-auth-blocker option A flip — the
// `/billing/my-invoices` user page is gone (admin invoices table at
// `/billing/invoices` covers operator's view of any user's history).
