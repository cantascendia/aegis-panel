import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import { FIXTURE_AWAITING_TRC20_INVOICE } from "../fixtures";
import { mockResolve, shouldUseMock } from "./mock-gate";
import type { Invoice } from "../../types";

/*
 * GET /api/billing/invoices/{id} — poll a specific invoice the
 * current user owns.
 *
 * Used by the TRC20 payment screen: every 5 s (server-side
 * Tronscan poll runs at 30 s, so 5 s is overkill but keeps the
 * UI snappy during testing) until state is terminal.
 *
 * Refetch stops automatically when `data.state` is terminal. See
 * INVOICE_TERMINAL_STATES in ../../types.
 */

import { INVOICE_TERMINAL_STATES } from "../../types";

export const UserInvoicePollQueryKey = "billing-invoice-poll-user";

const POLL_INTERVAL_MS = 5_000;

async function fetchInvoicePoll(id: number): Promise<Invoice> {
    if (shouldUseMock()) {
        return mockResolve(FIXTURE_AWAITING_TRC20_INVOICE);
    }
    return fetch<Invoice>(`/billing/invoices/${id}`);
}

export const useInvoicePoll = (
    id: number | null,
    options: { enabled?: boolean } = {},
) =>
    useQuery({
        queryKey: [UserInvoicePollQueryKey, id],
        queryFn: () => fetchInvoicePoll(id as number),
        enabled: id !== null && options.enabled !== false,
        // Stop polling once the invoice reaches a terminal state —
        // no point hammering the backend for an applied / cancelled
        // invoice.
        refetchInterval: (query) => {
            const inv = query.state.data as Invoice | undefined;
            if (inv && INVOICE_TERMINAL_STATES.includes(inv.state)) {
                return false;
            }
            return POLL_INTERVAL_MS;
        },
    });
