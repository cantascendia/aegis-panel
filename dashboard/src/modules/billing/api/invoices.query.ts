import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { Invoice, InvoiceState } from "../types";

export const BillingInvoicesQueryKey = "billing-invoices-admin";

export interface InvoiceFilters {
    state?: InvoiceState;
    user_id?: number;
    limit?: number;
    offset?: number;
}

export async function fetchAdminInvoices(
    filters: InvoiceFilters = {},
): Promise<Invoice[]> {
    const query: Record<string, string | number> = {};
    if (filters.state) query.state = filters.state;
    if (filters.user_id !== undefined) query.user_id = filters.user_id;
    if (filters.limit !== undefined) query.limit = filters.limit;
    if (filters.offset !== undefined) query.offset = filters.offset;
    return fetch<Invoice[]>("/billing/admin/invoices", { query });
}

export const useAdminInvoices = (filters: InvoiceFilters = {}) =>
    useQuery({
        queryKey: [BillingInvoicesQueryKey, "list", filters],
        queryFn: () => fetchAdminInvoices(filters),
    });

export async function fetchAdminInvoice(id: number): Promise<Invoice> {
    return fetch<Invoice>(`/billing/admin/invoices/${id}`);
}

export const useAdminInvoice = (
    id: number | null,
    options: { enabled?: boolean } = {},
) =>
    useQuery({
        queryKey: [BillingInvoicesQueryKey, "detail", id],
        queryFn: () => fetchAdminInvoice(id as number),
        enabled: id !== null && options.enabled !== false,
    });
