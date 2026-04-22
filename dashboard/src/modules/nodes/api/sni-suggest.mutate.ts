import { useMutation } from "@tanstack/react-query";
import { fetch } from "@marzneshin/common/utils";

/*
 * SNI intelligent selector — dashboard client.
 *
 * Backend endpoint: POST /api/nodes/sni-suggest (see
 * hardening/sni/endpoint.py). Sudo-admin only, 60s wall-clock timeout,
 * selector-internal Semaphore(5) caps outbound probe fan-out.
 *
 * Shapes mirror backend `SelectorResult.to_dict()` exactly. The golden
 * test (tests/test_sni_selector.py::test_output_json_schema_golden)
 * guards the backend side; if that test ever updates, these types
 * need to follow.
 */

export type SniRegion = "auto" | "global" | "jp" | "kr" | "us" | "eu";

export interface SniSuggestRequest {
    vps_ip: string;
    count: number;
    region: SniRegion;
}

export interface SniCheckResults {
    blacklist_ok: boolean;
    no_redirect: boolean;
    same_asn: boolean;
    tls13_ok: boolean;
    alpn_h2_ok: boolean;
    x25519_ok: boolean;
    ocsp_stapling: boolean;
    rtt_ms: number | null;
}

export interface SniCandidate {
    host: string;
    score: number;
    checks: SniCheckResults;
    notes: string;
}

export interface SniRejection {
    host: string;
    reason: string;
}

export interface SniSelectorResult {
    vps_ip: string;
    vps_asn: number | null;
    vps_country: string | null;
    probed_at: string;
    elapsed_seconds: number;
    candidates: SniCandidate[];
    rejected: SniRejection[];
}

export async function fetchSniSuggest(
    req: SniSuggestRequest,
): Promise<SniSelectorResult> {
    // The endpoint blocks up to 60 s on real probes. ofetch's default
    // timeout is infinite; we rely on the server-side wall clock
    // rather than racing the client timeout against it. If the
    // browser window closes, the request is cancelled client-side,
    // and that's fine — the server's selector has its own bounded
    // asyncio budget.
    return fetch("/nodes/sni-suggest", { method: "post", body: req });
}

const SniSuggestFetchKey = "nodes-sni-suggest";

export const useSniSuggestMutation = () => {
    return useMutation({
        mutationKey: [SniSuggestFetchKey],
        mutationFn: fetchSniSuggest,
        // No onSuccess toast — results are surfaced in the dialog.
        // No queryClient.invalidateQueries — this probe is read-only
        // and doesn't mutate server state we cache elsewhere.
    });
};
