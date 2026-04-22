import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { Invoice, InvoiceAdminAction } from "../types";
import { BillingInvoicesQueryKey } from "./invoices.query";

interface ActionArgs {
    id: number;
    body: InvoiceAdminAction;
}

export async function fetchApplyManual({
    id,
    body,
}: ActionArgs): Promise<Invoice> {
    return fetch<Invoice>(`/billing/admin/invoices/${id}/apply_manual`, {
        method: "post",
        body,
    });
}

export async function fetchCancelInvoice({
    id,
    body,
}: ActionArgs): Promise<Invoice> {
    return fetch<Invoice>(`/billing/admin/invoices/${id}/cancel`, {
        method: "post",
        body,
    });
}

const handleApplyError = (error: Error) => {
    toast.error(
        i18n.t("page.billing.invoices.toast.apply_error", {
            defaultValue: "Apply failed",
        }),
        { description: error.message },
    );
};

const handleApplySuccess = (inv: Invoice) => {
    toast.success(
        i18n.t("page.billing.invoices.toast.apply_success", {
            defaultValue: "Invoice #{{id}} applied",
            id: inv.id,
        }),
    );
    queryClient.invalidateQueries({ queryKey: [BillingInvoicesQueryKey] });
};

const handleCancelError = (error: Error) => {
    toast.error(
        i18n.t("page.billing.invoices.toast.cancel_error", {
            defaultValue: "Cancel failed",
        }),
        { description: error.message },
    );
};

const handleCancelSuccess = (inv: Invoice) => {
    toast.success(
        i18n.t("page.billing.invoices.toast.cancel_success", {
            defaultValue: "Invoice #{{id}} cancelled",
            id: inv.id,
        }),
    );
    queryClient.invalidateQueries({ queryKey: [BillingInvoicesQueryKey] });
};

export const useApplyManual = () =>
    useMutation({
        mutationKey: [BillingInvoicesQueryKey, "apply_manual"],
        mutationFn: fetchApplyManual,
        onError: handleApplyError,
        onSuccess: handleApplySuccess,
    });

export const useCancelInvoice = () =>
    useMutation({
        mutationKey: [BillingInvoicesQueryKey, "cancel"],
        mutationFn: fetchCancelInvoice,
        onError: handleCancelError,
        onSuccess: handleCancelSuccess,
    });
