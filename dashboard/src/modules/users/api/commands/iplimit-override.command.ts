import { useMutation } from "@tanstack/react-query";
import { fetch, queryClient } from "@marzneshin/common/utils";
import {
    type IpLimitAction,
    type IpLimitOverride,
    IpLimitAuditQueryFetchKey,
    IpLimitQueryFetchKey,
} from "@marzneshin/modules/users";

export interface IpLimitOverridePatch {
    username: string;
    max_concurrent_ips: number | null;
    window_seconds: number | null;
    violation_action: IpLimitAction | null;
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

