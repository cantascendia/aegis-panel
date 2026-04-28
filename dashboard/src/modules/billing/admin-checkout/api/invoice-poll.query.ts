import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import {
    INVOICE_TERMINAL_STATES,
    type Invoice,
} from "../../types";

/*
 * Polled view of an invoice for the TRC20 payment screen.
 *
 * Wraps the admin endpoint `GET /api/billing/admin/invoices/{id}`
 * with `refetchInterval` so the screen reflects state transitions
 * (awaiting_payment → paid → applied) without manual refresh.
 *
 * Polling stops when state hits a terminal value to avoid
 * hammering the backend on dead invoices.
 *
 * Distinct from the sibling `useAdminInvoice` hook (which doesn't
 * poll) so it can be deleted independently if the operator-side UX
 * changes — admin pages prefer manual refresh; this screen needs
 * live update because the operator stays on it while the user pays.
 */

export const InvoicePollQueryKey = "billing-invoice-poll";

const POLL_INTERVAL_MS = 5_000;

async function fetchInvoice(id: number): Promise<Invoice> {
    return fetch<Invoice>(`/billing/admin/invoices/${id}`);
}

export const useInvoicePoll = (
    id: number | null,
    options: { enabled?: boolean } = {},
) =>
    useQuery({
        queryKey: [InvoicePollQueryKey, id],
        queryFn: () => fetchInvoice(id as number),
        enabled: id !== null && options.enabled !== false,
        refetchInterval: (query) => {
            const inv = query.state.data as Invoice | undefined;
            if (inv && INVOICE_TERMINAL_STATES.includes(inv.state)) {
                return false;
            }
            return POLL_INTERVAL_MS;
        },
    });
