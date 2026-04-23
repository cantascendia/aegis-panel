import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import { FIXTURE_CHANNELS } from "../fixtures";
import { mockResolve, shouldUseMock } from "./mock-gate";
import type { PaymentChannel } from "../../types";

/*
 * Enabled payment channels for the user's checkout picker.
 *
 * Backend `GET /api/billing/channels` (user, not admin) returns
 * only `enabled=true` EPay channels. The TRC20 pseudo-channel is
 * synthesized client-side when the backend's env exposes
 * `BILLING_TRC20_ENABLED=true` — tracked via a separate flag on
 * the response (to be added in A.3.1). For the skeleton, we
 * always include the TRC20 pseudo-row in the fixture path.
 *
 * The backend endpoint isn't on main yet; the mock gate returns
 * fixtures so the checkout picker UI renders during preview.
 */

export const UserBillingChannelsQueryKey = "billing-channels-user";

async function fetchUserChannels(): Promise<PaymentChannel[]> {
    if (shouldUseMock()) {
        return mockResolve(FIXTURE_CHANNELS);
    }
    return fetch<PaymentChannel[]>("/billing/channels");
}

export const useUserChannels = () =>
    useQuery({
        queryKey: [UserBillingChannelsQueryKey],
        queryFn: fetchUserChannels,
    });
