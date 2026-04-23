import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import { FIXTURE_MY_INVOICES } from "../fixtures";
import { mockResolve, shouldUseMock } from "./mock-gate";
import type { MyInvoiceRow } from "../../types";

/*
 * GET /api/billing/invoices/me — current user's invoice history.
 *
 * Backend lands in A.3.1 (SPEC-billing-a2-a3.md). Mock path
 * returns the `FIXTURE_MY_INVOICES` array with one row per state
 * (awaiting_payment / applied / expired / cancelled) so the history
 * page visibly exercises every badge during preview.
 */

export const UserMyInvoicesQueryKey = "billing-invoices-me";

async function fetchMyInvoices(): Promise<MyInvoiceRow[]> {
    if (shouldUseMock()) {
        return mockResolve(FIXTURE_MY_INVOICES);
    }
    return fetch<MyInvoiceRow[]>("/billing/invoices/me");
}

export const useMyInvoices = () =>
    useQuery({
        queryKey: [UserMyInvoicesQueryKey],
        queryFn: fetchMyInvoices,
    });
