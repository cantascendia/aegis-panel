import { useQuery } from "@tanstack/react-query";
import { FetchError } from "ofetch";

import { fetch } from "@marzneshin/common/utils";

import type { HealthReport } from "../types";

/*
 * Polled view of the sudo-admin extended health report.
 *
 * Wraps `GET /api/aegis/health/extended` (added by PR #83 — see
 * `hardening/health/endpoint.py` for the contract). The endpoint is
 * sudo-gated, so only the admin "Health" page should mount this hook;
 * non-sudo callers will see a 401/403 and we shut polling down rather
 * than spam the backend.
 *
 * 30s default cadence is operator-friendly: long enough to avoid
 * trampling (each call probes 6 subsystems concurrently with up to
 * 5s timeouts), short enough that a degraded badge appears within a
 * minute of the underlying issue. Manual refresh via the page button
 * uses TanStack Query's refetch().
 */

export const HealthExtendedQueryKey = "aegis-health-extended";

const POLL_INTERVAL_MS = 30_000;

async function fetchHealthExtended(): Promise<HealthReport> {
    return fetch<HealthReport>("/aegis/health/extended");
}

const isAuthError = (err: unknown): boolean => {
    if (err instanceof FetchError) {
        const status = err.response?.status;
        return status === 401 || status === 403;
    }
    return false;
};

export const useHealthExtended = () =>
    useQuery({
        queryKey: [HealthExtendedQueryKey],
        queryFn: fetchHealthExtended,
        refetchInterval: (query) => {
            // Stop polling on auth errors — the user clearly isn't
            // sudo on this session, and retrying every 30s would
            // pollute logs without ever succeeding.
            if (isAuthError(query.state.error)) return false;
            return POLL_INTERVAL_MS;
        },
        // No retry on 401/403 either — same reasoning.
        retry: (failureCount, error) => {
            if (isAuthError(error)) return false;
            return failureCount < 3;
        },
    });
