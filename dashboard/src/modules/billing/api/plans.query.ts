import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { Plan } from "../types";

/*
 * Plain useQuery for admin plan list. Not on the entity-table infra
 * because billing plans are a small list (rarely > 20 rows) — the
 * pagination/filter/sort machinery of NodesTable is overkill.
 */

export const BillingPlansQueryKey = "billing-plans-admin";

export async function fetchAdminPlans(): Promise<Plan[]> {
    return fetch<Plan[]>("/billing/admin/plans");
}

export const useAdminPlans = () =>
    useQuery({
        queryKey: [BillingPlansQueryKey],
        queryFn: fetchAdminPlans,
    });
