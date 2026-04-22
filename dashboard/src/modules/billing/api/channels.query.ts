import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { PaymentChannel } from "../types";

export const BillingChannelsQueryKey = "billing-channels-admin";

export async function fetchAdminChannels(): Promise<PaymentChannel[]> {
    return fetch<PaymentChannel[]>("/billing/admin/channels");
}

export const useAdminChannels = () =>
    useQuery({
        queryKey: [BillingChannelsQueryKey],
        queryFn: fetchAdminChannels,
    });
