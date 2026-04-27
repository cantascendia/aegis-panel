import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { PaymentChannel } from "../../types";

/*
 * Channels for the admin checkout flow — only enabled rows.
 *
 * Backend admin endpoint returns ALL channels (incl. disabled);
 * we filter client-side here because the admin list is small
 * (typically 1-5 rows) and the backend has no `enabled` query
 * filter (would be a 1-line backend addition for a follow-up).
 *
 * TRC20 is appended client-side as a synthetic pseudo-channel
 * (channel_code = "trc20") if at least one EPay channel exists,
 * since the backend doesn't return TRC20 in this list — TRC20
 * config lives in env vars (BILLING_TRC20_*), not the
 * PaymentChannel table.
 *
 * The pseudo-channel is rendered by CheckoutPaymentPicker as the
 * second tab. CheckoutPaymentPicker filters it back out of the
 * EPay-only sub-list using `channel_code === "trc20"`.
 */

export const UserBillingChannelsQueryKey = "billing-channels-checkout";

const TRC20_PSEUDO: PaymentChannel = {
    id: -1,
    channel_code: "trc20",
    display_name: "USDT (TRC20)",
    kind: "epay", // pseudo — picker special-cases by channel_code
    gateway_url: "",
    merchant_id: "",
    enabled: true,
    priority: 30,
    created_at: "1970-01-01T00:00:00Z",
};

async function fetchEnabledChannels(): Promise<PaymentChannel[]> {
    const all = await fetch<PaymentChannel[]>("/billing/admin/channels");
    const enabled = all.filter((c) => c.enabled);
    // Always offer TRC20 as a tab — the operator decides per-invoice
    // whether the user wants USDT. Backend rejects with 4xx if TRC20
    // env not configured, surfacing the misconfig at checkout time.
    return [...enabled, TRC20_PSEUDO];
}

export const useUserChannels = () =>
    useQuery({
        queryKey: [UserBillingChannelsQueryKey],
        queryFn: fetchEnabledChannels,
    });
