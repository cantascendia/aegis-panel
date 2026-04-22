import { queryOptions, useQuery } from "@tanstack/react-query";
import { fetch } from "@marzneshin/common/utils";

export type IpLimitAction = "warn" | "disable";

export interface IpLimitConfig {
    max_concurrent_ips: number;
    window_seconds: number;
    violation_action: IpLimitAction;
    disable_duration_seconds: number;
}

export interface IpLimitOverride {
    max_concurrent_ips: number | null;
    window_seconds: number | null;
    violation_action: IpLimitAction | null;
}

export interface IpLimitState {
    username: string;
    redis_configured: boolean;
    observed_ips: string[];
    observed_count: number;
    disabled_until: number | null;
    config: IpLimitConfig;
    override: IpLimitOverride | null;
}

export interface IpLimitAuditEvent {
    user_id: number;
    username: string;
    ip_list: string[];
    count: number;
    action: IpLimitAction;
    ts: number;
}

export interface IpLimitAudit {
    username: string;
    redis_configured: boolean;
    events: IpLimitAuditEvent[];
}

export const IpLimitQueryFetchKey = "users-iplimit";
export const IpLimitAuditQueryFetchKey = "users-iplimit-audit";

export async function fetchIpLimitState({
    queryKey,
}: {
    queryKey: [string, string];
}): Promise<IpLimitState> {
    return fetch(`/users/${queryKey[1]}/iplimit`);
}

export async function fetchIpLimitAudit({
    queryKey,
}: {
    queryKey: [string, string];
}): Promise<IpLimitAudit> {
    return fetch(`/users/${queryKey[1]}/iplimit/audit`);
}

export const ipLimitQueryOptions = ({ username }: { username: string }) =>
    queryOptions({
        queryKey: [IpLimitQueryFetchKey, username],
        queryFn: fetchIpLimitState,
    });

export const ipLimitAuditQueryOptions = ({
    username,
}: {
    username: string;
}) =>
    queryOptions({
        queryKey: [IpLimitAuditQueryFetchKey, username],
        queryFn: fetchIpLimitAudit,
    });

export const useIpLimitQuery = ({ username }: { username: string }) =>
    useQuery(ipLimitQueryOptions({ username }));

export const useIpLimitAuditQuery = ({ username }: { username: string }) =>
    useQuery(ipLimitAuditQueryOptions({ username }));

