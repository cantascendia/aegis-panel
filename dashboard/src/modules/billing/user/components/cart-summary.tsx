import { type FC, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";

import { Button } from "@marzneshin/common/components";

import type { CartLine, Plan, ResolvedCartLine } from "../../types";

/*
 * Cart sidebar.
 *
 * Resolves CartLine[] (wire shape with plan_id + quantity) against
 * the plan catalog to produce ResolvedCartLine[] for display.
 * Mirrors backend's `compute_cart_total_fen` in `ops/billing/
 * pricing.py` — we recompute client-side for immediate feedback;
 * backend re-validates at /cart/checkout (authoritative).
 *
 * Empty cart renders an inline empty state; Checkout button is
 * disabled until total > 0.
 */

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;

function resolveLines(
    lines: CartLine[],
    plans: Plan[],
): ResolvedCartLine[] {
    const byId = new Map(plans.map((p) => [p.id, p]));
    const out: ResolvedCartLine[] = [];
    for (const line of lines) {
        const plan = byId.get(line.plan_id);
        if (!plan) continue; // plan deleted server-side mid-session; drop
        out.push({
            plan,
            quantity: line.quantity,
            line_total_fen: plan.price_cny_fen * line.quantity,
        });
    }
    return out;
}

interface CartSummaryProps {
    lines: CartLine[];
    plans: Plan[];
    onRemove: (planId: number) => void;
    onCheckout: () => void;
    /** Disable checkout during in-flight mutation so double-clicks
     *  can't create two invoices. */
    checkoutPending: boolean;
}

export const CartSummary: FC<CartSummaryProps> = ({
    lines,
    plans,
    onRemove,
    onCheckout,
    checkoutPending,
}) => {
    const { t } = useTranslation();
    const resolved = useMemo(() => resolveLines(lines, plans), [lines, plans]);
    const total = resolved.reduce((s, r) => s + r.line_total_fen, 0);

    return (
        <aside className="flex flex-col gap-3 p-4 border rounded-lg bg-card sticky top-4">
            <h2 className="text-lg font-semibold">
                {t("page.billing.purchase.cart.title")}
            </h2>
            {resolved.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-4">
                    {t("page.billing.purchase.cart.empty")}
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {resolved.map((line) => (
                        <div
                            key={line.plan.id}
                            className="flex flex-row gap-2 items-center text-sm border-b pb-2"
                        >
                            <div className="flex-1">
                                <div className="font-medium">
                                    {line.plan.display_name_en}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    ×{line.quantity} ·{" "}
                                    {formatPriceCny(line.plan.price_cny_fen)}
                                </div>
                            </div>
                            <div className="tabular-nums font-semibold">
                                {formatPriceCny(line.line_total_fen)}
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onRemove(line.plan.id)}
                                aria-label={t("page.billing.purchase.cart.remove")}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                </div>
            )}

            <div className="flex flex-row justify-between items-baseline pt-2 border-t">
                <span className="text-sm text-muted-foreground">
                    {t("page.billing.purchase.cart.total")}
                </span>
                <span className="text-xl font-bold tabular-nums">
                    {formatPriceCny(total)}
                </span>
            </div>

            <Button
                onClick={onCheckout}
                disabled={total === 0 || checkoutPending}
                className="w-full"
            >
                {checkoutPending
                    ? t("page.billing.purchase.cart.checkout_pending")
                    : t("page.billing.purchase.cart.checkout")}
            </Button>
        </aside>
    );
};
