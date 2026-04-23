import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import { FIXTURE_AWAITING_TRC20_INVOICE } from "../fixtures";
import { mockResolve, shouldUseMock } from "./mock-gate";
import type { CheckoutRequest, CheckoutResponse } from "../../types";
import { UserMyInvoicesQueryKey } from "./my-invoices.query";

/*
 * POST /api/billing/cart/checkout — creates an invoice from the
 * current cart + picked channel, returns `{invoice_id, payment_url}`.
 *
 * The backend endpoint lands in A.2.2 (SPEC-billing-a2-a3.md).
 * Until then, mocked to return the TRC20 fixture invoice pointing
 * at `/dashboard/billing/invoice/{id}` — exercises the poll screen
 * without a real gateway.
 *
 * Co-located with `checkout.mutate.ts` in the A.3.3 admin-stubs
 * tree, deliberately at the user sub-path. Post-merge we may
 * consolidate; not blocking per WIP-billing-split.md.
 */

async function doCheckout(body: CheckoutRequest): Promise<CheckoutResponse> {
    if (shouldUseMock()) {
        return mockResolve({
            invoice_id: FIXTURE_AWAITING_TRC20_INVOICE.id,
            payment_url:
                FIXTURE_AWAITING_TRC20_INVOICE.payment_url ??
                `/dashboard/billing/invoice/${FIXTURE_AWAITING_TRC20_INVOICE.id}`,
        });
    }
    return fetch<CheckoutResponse>("/billing/cart/checkout", {
        method: "post",
        body,
    });
}

const handleCheckoutError = (error: Error) => {
    toast.error(
        i18n.t("page.billing.purchase.toast.checkout_error", {
            defaultValue: "Checkout failed",
        }),
        { description: error.message },
    );
};

const handleCheckoutSuccess = (res: CheckoutResponse) => {
    toast.success(
        i18n.t("page.billing.purchase.toast.checkout_success", {
            defaultValue: "Invoice #{{id}} created",
            id: res.invoice_id,
        }),
    );
    queryClient.invalidateQueries({
        queryKey: [UserMyInvoicesQueryKey],
    });
};

export const useCheckout = () =>
    useMutation({
        mutationKey: ["billing-user-checkout"],
        mutationFn: doCheckout,
        onError: handleCheckoutError,
        onSuccess: handleCheckoutSuccess,
    });
