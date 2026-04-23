/**
 * Unit tests for PlanCard.
 *
 * Covers:
 *   - Display name resolution (i18n json → English fallback)
 *   - Price formatting (integer fen → ¥X.XX)
 *   - Shape line (GB / d) for fixed plans
 *   - "alreadyInCart" toggles button variant + disables + swaps label
 *   - onAdd callback fires with the full plan object
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";

import { I18nextProvider } from "react-i18next";
import i18n from "@marzneshin/features/i18n";

import type { Plan } from "../../types";
import { PlanCard } from "./plan-card";

const STARTER_PLAN: Plan = {
    id: 101,
    operator_code: "starter-30",
    display_name_en: "Starter · 30 GB / 30 d",
    display_name_i18n: { "zh-cn": "入门 · 30 GB / 30 天" },
    kind: "fixed",
    data_limit_gb: 30,
    duration_days: 30,
    price_cny_fen: 3500,
    enabled: true,
    sort_order: 10,
    created_at: "2026-04-01T00:00:00Z",
};

function renderCard(overrides?: {
    plan?: Plan;
    alreadyInCart?: boolean;
    onAdd?: (plan: Plan) => void;
}) {
    const onAdd = overrides?.onAdd ?? vi.fn();
    const utils = render(
        <I18nextProvider i18n={i18n}>
            <PlanCard
                plan={overrides?.plan ?? STARTER_PLAN}
                alreadyInCart={overrides?.alreadyInCart ?? false}
                onAdd={onAdd}
            />
        </I18nextProvider>,
    );
    return { ...utils, onAdd };
}

describe("PlanCard", () => {
    it("renders English display name when locale has no override", () => {
        renderCard();
        expect(
            screen.getByText("Starter · 30 GB / 30 d"),
        ).toBeInTheDocument();
    });

    it("formats price from integer fen to ¥X.XX", () => {
        renderCard();
        // 3500 fen → ¥35.00, not ¥3500 / ¥35 / ¥35.0
        expect(screen.getByText("¥35.00")).toBeInTheDocument();
    });

    it("renders shape string from GB + days", () => {
        renderCard();
        expect(screen.getByText("30 GB / 30 d")).toBeInTheDocument();
    });

    it("renders without crashing for a plan with no GB and no days", () => {
        // Defensive render — backend shouldn't return this for a
        // fixed plan, but the component must not crash if it does.
        // The shape line renders empty; we assert the name + price
        // still render correctly (no spurious content pushed into
        // the shape div).
        renderCard({
            plan: {
                ...STARTER_PLAN,
                data_limit_gb: null,
                duration_days: null,
            },
        });
        expect(
            screen.getByText("Starter · 30 GB / 30 d"),
        ).toBeInTheDocument();
        expect(screen.getByText("¥35.00")).toBeInTheDocument();
    });

    it("calls onAdd with the full plan when CTA clicked (not-in-cart)", async () => {
        const user = userEvent.setup();
        const onAdd = vi.fn();
        renderCard({ onAdd });
        const button = screen.getByRole("button");
        expect(button).not.toBeDisabled();
        await user.click(button);
        expect(onAdd).toHaveBeenCalledOnce();
        expect(onAdd).toHaveBeenCalledWith(STARTER_PLAN);
    });

    it("disables CTA and swaps label when alreadyInCart=true", async () => {
        const user = userEvent.setup();
        const onAdd = vi.fn();
        renderCard({ alreadyInCart: true, onAdd });
        const button = screen.getByRole("button");
        expect(button).toBeDisabled();
        // Click does nothing because disabled — user-event respects
        // the disabled state and doesn't fire.
        await user.click(button);
        expect(onAdd).not.toHaveBeenCalled();
    });

    it("gives distinct label text for 'add' vs 'already in cart' states", () => {
        const { unmount } = renderCard({ alreadyInCart: false });
        const addLabel = screen.getByRole("button").textContent;
        unmount();
        renderCard({ alreadyInCart: true });
        const alreadyLabel = screen.getByRole("button").textContent;
        expect(addLabel).not.toBe(alreadyLabel);
    });
});
