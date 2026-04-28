import { type FC } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@marzneshin/common/components";

import type { InvoiceState } from "../../types";

/*
 * User-facing invoice status badge.
 *
 * Differs from the admin `StateLabel` in `invoice-detail-dialog.tsx`
 * in that it uses friendlier labels from the user i18n subtree
 * (`page.billing.purchase.state.*`) instead of showing raw state
 * strings. The admin dialog intentionally shows raw states; user UI
 * needs "Waiting for payment", "Activated", "Cancelled", etc.
 */

const variantFor = (
    state: InvoiceState,
): "default" | "secondary" | "outline" | "destructive" => {
    if (state === "applied") return "default";
    if (state === "paid" || state === "awaiting_payment") return "secondary";
    if (
        state === "expired" ||
        state === "cancelled" ||
        state === "failed"
    ) {
        return "destructive";
    }
    return "outline";
};

/* Exhaustive map of InvoiceState → i18n key. Inline literal t("…")
 * per-branch (see L-017: template-literal keys are invisible to the
 * drift-gate regex). */
const labelFor = (state: InvoiceState, t: (k: string) => string): string => {
    switch (state) {
        case "created":
            return t("page.billing.purchase.state.created");
        case "pending":
            return t("page.billing.purchase.state.pending");
        case "awaiting_payment":
            return t("page.billing.purchase.state.awaiting_payment");
        case "paid":
            return t("page.billing.purchase.state.paid");
        case "applied":
            return t("page.billing.purchase.state.applied");
        case "expired":
            return t("page.billing.purchase.state.expired");
        case "cancelled":
            return t("page.billing.purchase.state.cancelled");
        case "failed":
            return t("page.billing.purchase.state.failed");
    }
};

export const InvoiceStatusBadge: FC<{ state: InvoiceState }> = ({ state }) => {
    const { t } = useTranslation();
    return <Badge variant={variantFor(state)}>{labelFor(state, t)}</Badge>;
};
