import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { AuditEventListResponse, AuditListParams } from "../types";

/*
 * Query hook for GET /api/audit/events (AL.3 endpoint).
 *
 * Page (limit=50 default) of audit rows newest-first. Filters mirror
 * the backend schema:
 *   - actor_username, action substring, target_type, target_id,
 *     result, since, until, limit, cursor
 *
 * Why useQuery (vs useMutation): list is a read; we want the cache
 * + automatic refetch-on-focus (operators leave the tab open and
 * want fresh data when returning). 30 s staleTime keeps it cheap.
 *
 * Cursor pagination: the page passes back `next_cursor` from the
 * previous response to fetch the next page. The query key includes
 * the cursor so each page has its own cache slot.
 */

const AuditListQueryKey = "audit-events-list";

const buildSearchParams = (params: AuditListParams): string => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== "") {
            search.set(key, String(value));
        }
    }
    return search.toString();
};

const fetchAuditEvents = async (
    params: AuditListParams,
): Promise<AuditEventListResponse> => {
    const qs = buildSearchParams(params);
    const path = qs ? `/api/audit/events?${qs}` : "/api/audit/events";
    return fetch(path);
};

export const useAuditEvents = (params: AuditListParams = {}) =>
    useQuery({
        queryKey: [AuditListQueryKey, params],
        queryFn: () => fetchAuditEvents(params),
        staleTime: 30_000,
        // Don't refetch on every mount — the operator may flick
        // between tabs many times per minute.
        refetchOnWindowFocus: true,
    });
