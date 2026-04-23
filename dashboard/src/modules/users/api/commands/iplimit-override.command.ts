import { useMutation } from "@tanstack/react-query";
import { fetch, queryClient } from "@marzneshin/common/utils";
import {
    type IpLimitAction,
    type IpLimitOverride,
    type IpLimitState,
    IpLimitAuditQueryFetchKey,
    IpLimitQueryFetchKey,
} from "@marzneshin/modules/users";

export interface IpLimitOverridePatch {
    username: string;
    max_concurrent_ips: number | null;
    window_seconds: number | null;
    violation_action: IpLimitAction | null;
    ip_allowlist_cidrs: string | null;
}

export async function patchIpLimitOverride(
    patch: IpLimitOverridePatch,
): Promise<IpLimitOverride> {
    const { username, ...body } = patch;
    return fetch(`/users/${username}/iplimit/override`, {
        method: "patch",
        body,
    });
}

export const useIpLimitOverrideMutation = () =>
    useMutation({
        mutationKey: ["users-iplimit-override"],
        mutationFn: patchIpLimitOverride,
        onSuccess: (_value, variables) => {
            queryClient.invalidateQueries({
                queryKey: [IpLimitQueryFetchKey, variables.username],
            });
            queryClient.invalidateQueries({
                queryKey: [IpLimitAuditQueryFetchKey, variables.username],
            });
        },
    });

export async function clearIpLimitDisable({
    username,
}: {
    username: string;
}): Promise<IpLimitState> {
    return fetch(`/users/${username}/iplimit/disable`, {
        method: "delete",
    });
}

export const useIpLimitDisableClearMutation = () =>
    useMutation({
        mutationKey: ["users-iplimit-disable-clear"],
        mutationFn: clearIpLimitDisable,
        onSuccess: (_value, variables) => {
            queryClient.invalidateQueries({
                queryKey: [IpLimitQueryFetchKey, variables.username],
            });
            queryClient.invalidateQueries({
                queryKey: [IpLimitAuditQueryFetchKey, variables.username],
            });
        },
    });
