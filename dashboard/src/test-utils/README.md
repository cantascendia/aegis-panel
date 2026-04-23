# dashboard/src/test-utils

Helpers for writing vitest + React Testing Library tests in this
dashboard. Part of the S-X test infra (see
`docs/ai-cto/SPEC-dashboard-tests.md`).

Keep this doc tight — it's a quickstart, not a textbook.

## Quickstart

```tsx
import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

import { renderWithProviders } from "@marzneshin/test-utils/render";

import { MyComponent } from "./my-component";

describe("MyComponent", () => {
    it("calls onSubmit when the button is clicked", async () => {
        const user = userEvent.setup();
        const onSubmit = vi.fn();
        renderWithProviders(<MyComponent onSubmit={onSubmit} />);
        await user.click(screen.getByRole("button", { name: /submit/i }));
        expect(onSubmit).toHaveBeenCalledOnce();
    });
});
```

Run tests:

```
pnpm test:ci           # one-shot, same as CI
pnpm test              # watch mode
pnpm test:coverage     # one-shot + coverage report (dashboard/coverage/)
```

## `renderWithProviders(ui, opts?)`

Wraps `ui` in the providers leaf components need:

- `I18nextProvider` with the real project i18n instance. When a
  locale isn't loaded, `t("key")` falls back to the key itself —
  assertions can match `/key-path/i`.
- `QueryClientProvider` with a fresh client per render (unless you
  pass `queryClient`). Defaults: `retry: false`, `gcTime: 0`.

Returns the standard RTL `RenderResult` plus `queryClient` in case
you need to seed cache.

### Seeding cache

```tsx
const { queryClient } = renderWithProviders(<MyWidget />);
queryClient.setQueryData(["my-key"], { hello: "world" });
// … rerender or wait for useQuery to read cache
```

### Sharing a client across renders

```tsx
import { makeTestQueryClient } from "@marzneshin/test-utils/render";

const queryClient = makeTestQueryClient();
const { rerender } = renderWithProviders(<A />, { queryClient });
rerender(<B />); // same provider, same client
```

## Patterns

### Testing a hook that polls

Mock the gate + transport, then use `renderHook` with a local
`QueryClientProvider` wrapper (`renderWithProviders` is for components;
hooks use bare `renderHook` from `@testing-library/react`). See
`src/modules/billing/user/api/invoice-poll.query.test.ts` for the
canonical example with fake timers.

Key bits:

```ts
vi.mock("./mock-gate", async () => ({
    ...(await vi.importActual("./mock-gate")),
    shouldUseMock: () => false,
}));
vi.mock("@marzneshin/common/utils", () => ({ fetch: vi.fn() }));

// In the test:
vi.useFakeTimers();
vi.advanceTimersByTime(30_000);
vi.useRealTimers();
```

### Testing a component with Radix Tabs / Select / Dialog

Radix unmounts inactive panels. Assert on one panel at a time; switch
via `userEvent.click(screen.getByRole("tab", { name: /x/i }))` then
assert inside the active panel. You may see `act()` warnings from
Radix's async focus updates — they're cosmetic; tests still pass.

### Money math / totals

Use integer fen everywhere (`price_cny_fen`, `total_cny_fen`). Format
once at the display boundary. Unit tests assert the rendered `¥X.XX`
string exactly — float-drift regressions show up as string mismatch.
See `cart-summary.test.tsx`.

## Don't

- Don't `toMatchSnapshot()` DOM — shadcn class names are noisy.
- Don't assert on `aria-hidden` / `.class` selectors — users don't
  see them; tests go stale.
- Don't hit the real API. Mock at `@marzneshin/common/utils.fetch` or
  at the feature hook level.
- Don't stub i18n globally — the real instance is fine and exercises
  the i18n wiring too. Add specific translation keys to the locale
  JSON if a test needs a non-key-fallback.

## When to update this doc

- Added a new provider to `renderWithProviders` (e.g. MemoryRouter)
  → update the Quickstart + API section.
- Hit a new recurring pain pattern → add to §Patterns.
- Decide against a pattern (e.g. swapped jsdom for happy-dom) →
  update §Don't with the reasoning.

Keep it under ~100 lines. If it grows, it stops being read.
