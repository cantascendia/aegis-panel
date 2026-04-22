import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { PaymentChannel, PaymentChannelIn } from "../types";
import { BillingChannelsQueryKey } from "./channels.query";

export async function fetchCreateChannel(
    channel: PaymentChannelIn,
): Promise<PaymentChannel> {
    return fetch<PaymentChannel>("/billing/admin/channels", {
        method: "post",
        body: channel,
    });
}

const handleError = (error: Error, value: PaymentChannelIn) => {
    toast.error(
        i18n.t("page.billing.channels.toast.create_error", {
            defaultValue: "Create failed: {{code}}",
            code: value.channel_code,
        }),
        { description: error.message },
    );
};

const handleSuccess = (channel: PaymentChannel) => {
    toast.success(
        i18n.t("page.billing.channels.toast.create_success", {
            defaultValue: "Channel {{code}} created",
            code: channel.channel_code,
        }),
    );
    queryClient.invalidateQueries({ queryKey: [BillingChannelsQueryKey] });
};

export const useCreateChannel = () =>
    useMutation({
        mutationKey: [BillingChannelsQueryKey, "create"],
        mutationFn: fetchCreateChannel,
        onError: handleError,
        onSuccess: handleSuccess,
    });
