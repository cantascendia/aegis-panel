import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { Plan } from "../../types";

/*
 * Plans for the admin checkout flow.
 *
 * Reuses the admin endpoint `GET /api/billing/admin/plans` with
 * `include_disabled=false` so the operator sees only currently
 * sellable plans. The same endpoint is used by `useAdminPlans`
 * (sibling) which defaults to including disabled — keeping
 * that contract stable; this hook just sends the explicit flag.
 *
 * Per BRIEF-billing-user-auth-blocker.md option A, admin checkout
 * is the chosen flow; no separate user-facing /plans endpoint
 * exists or is planned.
 */

export const UserBillingPlansQueryKey = "billing-plans-checkout";

async function fetchEnabledPlans(): Promise<Plan[]> {
    return fetch<Plan[]>("/billing/admin/plans", {
        query: { include_disabled: false },
    });
}

export const useUserPlans = () =>
    useQuery({
        queryKey: [UserBillingPlansQueryKey],
        queryFn: fetchEnabledPlans,
    });
