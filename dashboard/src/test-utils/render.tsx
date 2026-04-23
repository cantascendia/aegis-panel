/**
 * Shared test render helper — wraps the SUT in the providers every
 * billing / feature component needs.
 *
 * Usage:
 *   import { renderWithProviders } from "@marzneshin/test-utils/render";
 *   const { queryClient } = renderWithProviders(<PlanCard .../>);
 *
 * Providers wired in:
 *   - I18nextProvider (real instance; `t("key")` falls back to the
 *     key itself when a locale is not loaded, which is fine for unit
 *     tests — assertions use regex on i18n keys)
 *   - QueryClientProvider (fresh client per render unless passed in)
 *
 * No MemoryRouter yet — leaf components under test don't read routes.
 * Add it here (not per-test) when X.3 starts covering route-level
 * scenarios.
 *
 * Spec: docs/ai-cto/SPEC-dashboard-tests.md §Render helper.
 */

import type { ReactElement } from "react";
import {
    render,
    type RenderOptions,
    type RenderResult,
} from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import i18n from "@marzneshin/features/i18n";

interface ExtraOptions {
    queryClient?: QueryClient;
}

export function makeTestQueryClient(): QueryClient {
    // `retry: false` → failed queries don't swallow assertion time
    // with auto-retries. `gcTime: 0` → no leftover cache between
    // tests that share a module-level client (shouldn't happen with
    // the default fresh-per-test, but belt + braces).
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false, gcTime: 0 },
            mutations: { retry: false },
        },
    });
}

export function renderWithProviders(
    ui: ReactElement,
    opts: Omit<RenderOptions, "wrapper"> & ExtraOptions = {},
): RenderResult & { queryClient: QueryClient } {
    const { queryClient: passed, ...rtlOpts } = opts;
    const queryClient = passed ?? makeTestQueryClient();
    const result = render(ui, {
        ...rtlOpts,
        wrapper: ({ children }) => (
            <I18nextProvider i18n={i18n}>
                <QueryClientProvider client={queryClient}>
                    {children}
                </QueryClientProvider>
            </I18nextProvider>
        ),
    });
    return Object.assign(result, { queryClient });
}
