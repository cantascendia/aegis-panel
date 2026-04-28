import { useMutation } from "@tanstack/react-query";

import { fetch } from "@marzneshin/common/utils";

import type { AuditRequestBody, Report } from "../types";

/*
 * Mutation hook for POST /api/reality/audit (R.3 backend).
 *
 * Why a mutation rather than a query: the audit is operator-initiated
 * (button click) and side-effect-free; we explicitly do NOT want
 * TanStack Query to retry, refetch on focus, or cache it. Each "Run
 * audit" press is one POST, the result is the latest report.
 *
 * Body discriminator follows the SPEC contract:
 *   - {source: "db"}                 — audit live panel config
 *   - {source: "config", config: {}} — dry-run an arbitrary xray dict
 *
 * `vps_asn` is forwarded when provided. The dashboard MVP does not yet
 * collect it from the operator (no input field for now); when omitted
 * the backend yields a graceful asn_match warning (-10), so the page
 * still renders something useful out of the box. Future R.5 may add
 * an ASN input — the hook already accepts the field.
 *
 * The endpoint can return 504 if WHOIS hangs. We surface the error to
 * the caller via TanStack's onError pathway; the page renders the
 * message verbatim from `error.message`.
 */

const AuditMutationKey = "reality-audit";

async function postAudit(body: AuditRequestBody): Promise<Report> {
    return fetch<Report>("/reality/audit", {
        method: "POST",
        body,
    });
}

export const useRealityAudit = () =>
    useMutation({
        mutationKey: [AuditMutationKey],
        mutationFn: postAudit,
        // Don't retry: the audit is an operator-driven action; if it
        // fails (504, 500, 401), the page surfaces the error and lets
        // the operator decide whether to click again.
        retry: false,
    });
