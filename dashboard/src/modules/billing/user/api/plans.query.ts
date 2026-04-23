import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import { FIXTURE_PLANS } from "../fixtures";
import { mockResolve, shouldUseMock } from "./mock-gate";
import type { Plan } from "../../types";

/*
 * User-facing plan list.
 *
 * Differs from the admin `useAdminPlans` at two points:
 * - Always filters to `enabled=true` via the backend's
 *   `include_disabled=false` query param (admin defaults to true).
 * - Sorted by `sort_order` ascending (backend already does this;
 *   this hook just consumes).
 *
 * The backend endpoint `GET /api/billing/plans` is scheduled in
 * `SPEC-billing-a2-a3.md` §A.2.2 follow-up. Until it exists, this
 * hook returns fixture data via the mock gate — no 404 in preview.
 */

export const UserBillingPlansQueryKey = "billing-plans-user";

async function fetchUserPlans(): Promise<Plan[]> {
    if (shouldUseMock()) {
        return mockResolve(FIXTURE_PLANS.filter((p) => p.enabled));
    }
    // Public user endpoint — no admin gate. Matches the spec's
    // "GET /api/billing/plans" scope (lines 419-420 of
    // SPEC-billing-mvp.md).
    return fetch<Plan[]>("/billing/plans");
}

export const useUserPlans = () =>
    useQuery({
        queryKey: [UserBillingPlansQueryKey],
        queryFn: fetchUserPlans,
    });
