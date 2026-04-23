# dashboard/src/test-utils

Quickstart for vitest + React Testing Library helpers in this dashboard.
See `docs/ai-cto/SPEC-dashboard-tests.md` for the S-X testing plan.

Keep this file short: it is a quickstart, not a test strategy doc.

## Quickstart

```tsx
import "@testing-library/jest-dom";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@marzneshin/test-utils/render";

const user = userEvent.setup();
const onSubmit = vi.fn();

renderWithProviders(<MyComponent onSubmit={onSubmit} />);

await user.click(screen.getByRole("button", { name: /submit/i }));
expect(onSubmit).toHaveBeenCalledOnce();
```

Run tests from `dashboard/`:

```bash
pnpm test:ci
pnpm test
pnpm test:coverage
```

## `renderWithProviders(ui, opts?)`

Use this for components that need project providers:

- real project `I18nextProvider`; missing keys fall back to the key
- fresh `QueryClientProvider` per render unless `opts.queryClient` is
  supplied; defaults are `retry: false` and `gcTime: 0`
- RTL `RenderResult` plus `queryClient`

```tsx
const { queryClient } = renderWithProviders(<MyWidget />);
queryClient.setQueryData(["my-key"], { hello: "world" });
```

```tsx
import { makeTestQueryClient } from "@marzneshin/test-utils/render";

const queryClient = makeTestQueryClient();
const { rerender } = renderWithProviders(<A />, { queryClient });
rerender(<B />);
```

## Patterns

### Polling hooks

Use `renderHook` with a local `QueryClientProvider` wrapper. Mock the
feature gate and transport, then drive time with fake timers. See
`src/modules/billing/user/api/invoice-poll.query.test.ts`.

```ts
vi.mock("./mock-gate", async () => ({
    ...(await vi.importActual("./mock-gate")),
    shouldUseMock: () => false,
}));
vi.mock("@marzneshin/common/utils", () => ({ fetch: vi.fn() }));

vi.useFakeTimers();
vi.advanceTimersByTime(30_000);
vi.useRealTimers();
```

### Radix controls

Radix unmounts inactive panels. Assert on the active panel, interact
with the tab/select/dialog through roles, then assert again after the UI
settles.

### Money math

Use integer fen in state and API fixtures. Format once at the display
boundary, and assert the exact rendered money string.

## Do not

- Do not use DOM snapshots.
- Do not assert on `aria-hidden` or implementation class names.
- Do not hit the real API. Mock `@marzneshin/common/utils.fetch` or the
  feature hook boundary.
- Do not stub i18n globally unless the behavior under test requires it.

## Updating this file

Update it when providers, canonical test patterns, or banned patterns
change. Keep it under 100 lines; split longer guidance into another doc.
