import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { PaymentChannel, PaymentChannelPatch } from "../types";
import { BillingChannelsQueryKey } from "./channels.query";

interface UpdateArgs {
    id: number;
    patch: PaymentChannelPatch;
}

export async function fetchUpdateChannel({
    id,
    patch,
}: UpdateArgs): Promise<PaymentChannel> {
    return fetch<PaymentChannel>(`/billing/admin/channels/${id}`, {
        method: "patch",
        body: patch,
    });
}

const handleError = (error: Error) => {
    toast.error(
        i18n.t("page.billing.channels.toast.update_error", {
            defaultValue: "Update failed",
        }),
        { description: error.message },
    );
};

const handleSuccess = (channel: PaymentChannel) => {
    toast.success(
        i18n.t("page.billing.channels.toast.update_success", {
            defaultValue: "Channel {{code}} updated",
            code: channel.channel_code,
        }),
    );
    queryClient.invalidateQueries({ queryKey: [BillingChannelsQueryKey] });
};

export const useUpdateChannel = () =>
    useMutation({
        mutationKey: [BillingChannelsQueryKey, "update"],
        mutationFn: fetchUpdateChannel,
        onError: handleError,
        onSuccess: handleSuccess,
    });
