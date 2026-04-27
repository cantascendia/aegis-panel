import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import i18n from "@marzneshin/features/i18n";
import { fetch, queryClient } from "@marzneshin/common/utils";

import type { CheckoutRequest, CheckoutResponse } from "../../types";
import { BillingInvoicesQueryKey } from "../../api/invoices.query";

/*
 * `POST /api/billing/cart/checkout` — admin checkout on behalf of
 * `body.user_id`. SudoAdminDep gated server-side.
 *
 * Per BRIEF-billing-user-auth-blocker.md option A. The previous
 * skeleton (PR #41) had a mock fallback gated on
 * `VITE_BILLING_USER_UI`; that knob is gone — flip-on done.
 *
 * On success:
 * - Invalidates the admin invoices cache so the operator's
 *   invoices table immediately reflects the new row.
 * - Caller decides redirect:
 *   - EPay → `window.location.assign(payment_url)` (external 码商)
 *   - TRC20 → SPA navigate to `/dashboard/billing/admin/invoices/{id}`
 *     so the operator can copy memo / amount and forward to user.
 */

async function doCheckout(body: CheckoutRequest): Promise<CheckoutResponse> {
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
    queryClient.invalidateQueries({ queryKey: [BillingInvoicesQueryKey] });
};

export const useCheckout = () =>
    useMutation({
        mutationKey: ["billing-checkout"],
        mutationFn: doCheckout,
        onError: handleCheckoutError,
        onSuccess: handleCheckoutSuccess,
    });
