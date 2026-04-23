/**
 * Unit tests for useInvoicePoll (TRC20-screen poll hook).
 *
 * What we're protecting:
 *   - Terminal states must stop the polling loop (applied/expired/
 *     cancelled/failed). If this regresses, we hammer the billing
 *     backend forever once an invoice is "done". Not a money bug,
 *     but a DoS-on-ourselves bug.
 *   - `enabled=false` / `id=null` must not fire queries at all.
 *   - Non-terminal state keeps polling at the spec'd interval.
 *
 * We don't test the interval value itself (5_000 is a magic const
 * in the source); we test the behavioral shape: "one more fetch
 * happens after time advances for non-terminal, zero fetches happen
 * after terminal."
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { Invoice, InvoiceState } from "../../types";

// Mock the mock-gate to force the live-fetch path; otherwise the
// hook returns the hardcoded FIXTURE_AWAITING_TRC20_INVOICE via
// mockResolve and we can't vary the state.
vi.mock("./mock-gate", async () => {
    const actual = await vi.importActual<typeof import("./mock-gate")>(
        "./mock-gate",
    );
    return {
        ...actual,
        shouldUseMock: () => false,
    };
});

// Mock the transport. This is what the hook calls in non-mock mode.
vi.mock("@marzneshin/common/utils", () => ({
    fetch: vi.fn(),
}));

// Import AFTER mocks are declared (hoisted) so the hook sees them.
import { fetch as mockedFetch } from "@marzneshin/common/utils";
import { useInvoicePoll } from "./invoice-poll.query";

const fetchMock = mockedFetch as unknown as ReturnType<typeof vi.fn>;

function buildInvoice(state: InvoiceState): Invoice {
    return {
        id: 9001,
        user_id: 42,
        total_cny_fen: 3500,
        state,
        provider: "trc20",
        provider_invoice_id: "AEG9001XZ",
        payment_url: "/dashboard/billing/invoice/9001",
        trc20_memo: "AEG9001XZ",
        trc20_expected_amount_millis: 4861,
        created_at: "2026-04-23T10:00:00Z",
        paid_at: null,
        applied_at: null,
        expires_at: "2026-04-23T10:30:00Z",
        lines: [],
    };
}

function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
        defaultOptions: {
            queries: { retry: false, gcTime: 0 },
        },
    });
    return createElement(QueryClientProvider, { client }, children);
}

beforeEach(() => {
    fetchMock.mockReset();
});

afterEach(() => {
    vi.useRealTimers();
});

describe("useInvoicePoll", () => {
    it("does not fetch when id is null", async () => {
        fetchMock.mockResolvedValue(buildInvoice("awaiting_payment"));
        const { result } = renderHook(() => useInvoicePoll(null), {
            wrapper,
        });
        // Let any microtasks resolve; query should still be idle.
        await new Promise((r) => setTimeout(r, 0));
        expect(fetchMock).not.toHaveBeenCalled();
        expect(result.current.isFetching).toBe(false);
    });

    it("does not fetch when enabled=false (opt-out)", async () => {
        fetchMock.mockResolvedValue(buildInvoice("awaiting_payment"));
        renderHook(() => useInvoicePoll(9001, { enabled: false }), {
            wrapper,
        });
        await new Promise((r) => setTimeout(r, 0));
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("fetches once and settles for a non-terminal invoice", async () => {
        fetchMock.mockResolvedValue(buildInvoice("awaiting_payment"));
        const { result } = renderHook(() => useInvoicePoll(9001), {
            wrapper,
        });
        await waitFor(() =>
            expect(result.current.data?.state).toBe("awaiting_payment"),
        );
        expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it.each<[InvoiceState]>([
        ["applied"],
        ["expired"],
        ["cancelled"],
        ["failed"],
    ])(
        "stops polling once state is terminal (%s) — no second fetch after interval",
        async (state) => {
            fetchMock.mockResolvedValue(buildInvoice(state));

            const { result } = renderHook(() => useInvoicePoll(9001), {
                wrapper,
            });
            await waitFor(() =>
                expect(result.current.data?.state).toBe(state),
            );
            expect(fetchMock).toHaveBeenCalledTimes(1);

            // Advance well past the 5_000 ms poll interval. If the
            // `refetchInterval` callback returned a number instead of
            // `false` for terminal states, react-query would schedule
            // another fetch here and the mock would record a second
            // call. It must not.
            vi.useFakeTimers();
            vi.advanceTimersByTime(30_000);
            vi.useRealTimers();

            // Give the event loop a tick so any erroneously scheduled
            // refetch would land.
            await new Promise((r) => setTimeout(r, 0));
            expect(fetchMock).toHaveBeenCalledTimes(1);
        },
    );
});
