import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { PaymentEvent } from "../types";
import { BillingInvoicesQueryKey } from "./invoices.query";

export async function fetchInvoiceEvents(
    invoiceId: number,
): Promise<PaymentEvent[]> {
    return fetch<PaymentEvent[]>(
        `/billing/admin/invoices/${invoiceId}/events`,
    );
}

export const useInvoiceEvents = (
    invoiceId: number | null,
    options: { enabled?: boolean } = {},
) =>
    useQuery({
        queryKey: [BillingInvoicesQueryKey, "events", invoiceId],
        queryFn: () => fetchInvoiceEvents(invoiceId as number),
        enabled: invoiceId !== null && options.enabled !== false,
    });
