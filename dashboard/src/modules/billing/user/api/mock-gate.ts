/*
 * Mock gate for the A.4 user purchase UI skeleton.
 *
 * A.4 ships behind the `VITE_BILLING_USER_UI` Vite env var. When
 * `off` (default) OR when a `?mock=1` URL param is present, API
 * hooks return fixture data from `../fixtures` instead of calling
 * the backend — the real endpoints (A.2.2 `/cart/checkout`, A.3.1
 * `/invoices/me`) don't exist on main yet.
 *
 * When `VITE_BILLING_USER_UI=on` AND no `?mock=1` override, hooks
 * go straight to `fetch(...)`.
 *
 * Delete this module (and every caller's fallback branch) in the
 * flip-on follow-up PR once the backend endpoints land. See
 * `docs/ai-cto/WIP-billing-split.md` "Flip-on checklist".
 */

/** Read-only snapshot of the active gate decision.
 *
 * Computed once per hook call (cheap), not memo'd, so a runtime
 * URL param change is picked up on the next re-render / refetch.
 */
export function shouldUseMock(): boolean {
    const flag = import.meta.env.VITE_BILLING_USER_UI;
    const envOn = flag === "on" || flag === "true" || flag === "1";
    const urlOverride =
        typeof window !== "undefined" &&
        new URLSearchParams(window.location.search).get("mock") === "1";
    // URL override ALWAYS wins so reviewers can preview mocked UI
    // even in a staging build that flipped the env flag on.
    if (urlOverride) return true;
    return !envOn;
}

/** Resolve a fixture value after a small artificial delay so the
 *  UI's loading state is visible during preview. The delay is
 *  intentionally short — reviewers shouldn't wait.
 */
export function mockResolve<T>(value: T, delayMs = 200): Promise<T> {
    return new Promise((resolve) => {
        setTimeout(() => resolve(value), delayMs);
    });
}
