import { useQuery } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type {
    AuditEventDetail,
    AuditEventFilters,
    AuditEventRow,
    AuditStatsResponse,
} from "../types";

export const AuditEventsQueryKey = "audit-events";

// ── List events ───────────────────────────────────────────────────────────

async function fetchAuditEvents(
    filters: AuditEventFilters = {},
): Promise<AuditEventRow[]> {
    const query: Record<string, string | number> = {};
    if (filters.actor_username) query.actor_username = filters.actor_username;
    if (filters.actor_type) query.actor_type = filters.actor_type;
    if (filters.result) query.result = filters.result;
    if (filters.before_id !== undefined) query.before_id = filters.before_id;
    if (filters.limit !== undefined) query.limit = filters.limit;
    return fetch<AuditEventRow[]>("/audit/events", { query });
}

export const useAuditEvents = (filters: AuditEventFilters = {}) =>
    useQuery({
        queryKey: [AuditEventsQueryKey, "list", filters],
        queryFn: () => fetchAuditEvents(filters),
        staleTime: 30_000,
    });

// ── Single event (with decrypted state) ──────────────────────────────────

async function fetchAuditEvent(id: number): Promise<AuditEventDetail> {
    return fetch<AuditEventDetail>(`/audit/events/${id}`);
}

export const useAuditEvent = (
    id: number | null,
    options: { enabled?: boolean } = {},
) =>
    useQuery({
        queryKey: [AuditEventsQueryKey, "detail", id],
        queryFn: () => fetchAuditEvent(id as number),
        enabled: id !== null && options.enabled !== false,
        staleTime: 60_000,
    });

// ── Stats ─────────────────────────────────────────────────────────────────

async function fetchAuditStats(): Promise<AuditStatsResponse> {
    return fetch<AuditStatsResponse>("/audit/stats");
}

export const useAuditStats = () =>
    useQuery({
        queryKey: [AuditEventsQueryKey, "stats"],
        queryFn: fetchAuditStats,
        staleTime: 60_000,
    });
