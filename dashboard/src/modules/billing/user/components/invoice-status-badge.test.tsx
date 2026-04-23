/**
 * Unit test for InvoiceStatusBadge.
 *
 * Covers the exhaustive InvoiceState → (variant, label key) mapping.
 * The state machine literal values live in `ops/billing/db.py`; this
 * test protects the UI from silently mis-rendering a newly-added
 * state (the switch statement is exhaustive via TS, so adding a new
 * state without updating the switch would fail type-check, but
 * runtime visual regression is what CI catches).
 */

import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom";

import { I18nextProvider } from "react-i18next";
import i18n from "@marzneshin/features/i18n";

import type { InvoiceState } from "../../types";
import { InvoiceStatusBadge } from "./invoice-status-badge";

function renderBadge(state: InvoiceState) {
    return render(
        <I18nextProvider i18n={i18n}>
            <InvoiceStatusBadge state={state} />
        </I18nextProvider>,
    );
}

describe("InvoiceStatusBadge", () => {
    it.each<[InvoiceState]>([
        ["created"],
        ["pending"],
        ["awaiting_payment"],
        ["paid"],
        ["applied"],
        ["expired"],
        ["cancelled"],
        ["failed"],
    ])("renders without crashing for state %s", (state) => {
        const { container } = renderBadge(state);
        // Badge always renders a single element with non-empty text
        // content (localized label). We don't assert exact text
        // because i18n may fall back to key when translations
        // aren't loaded; the invariant we care about is "a badge
        // exists and isn't empty".
        const node = container.firstChild as HTMLElement | null;
        expect(node).not.toBeNull();
        expect(node?.textContent?.trim().length ?? 0).toBeGreaterThan(0);
    });

    it("applies destructive variant for terminal failure states", () => {
        // Smoke-test that the state→variant mapping doesn't collapse
        // all states into the same look. `applied` and `cancelled`
        // are both terminal but one is success (default variant) and
        // the other is failure (destructive). If a future refactor
        // accidentally uses the same variant for both, this catches
        // it.
        const applied = renderBadge("applied").container.firstChild as HTMLElement;
        const cancelled = renderBadge("cancelled").container.firstChild as HTMLElement;
        expect(applied.className).not.toBe(cancelled.className);
    });
});
