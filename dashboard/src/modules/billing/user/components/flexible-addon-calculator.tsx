import { type FC, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Input, Label } from "@marzneshin/common/components";

import type { CartLine, Plan } from "../../types";

/*
 * Flexible-addon calculator.
 *
 * Two addon shapes: `flexible_traffic` (per-GB) and
 * `flexible_duration` (per-day). User picks a quantity via numeric
 * input + +/- buttons; total updates live. "Add to cart" emits a
 * CartLine with the chosen quantity.
 *
 * Numeric inputs instead of shadcn Slider because `<Slider>` isn't
 * vendored in `common/components/ui/` and the skeleton doesn't
 * justify pulling in a new dependency. The UX is functional and
 * matches iplimit's minimalist admin panels.
 */

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;

interface AddonRowProps {
    plan: Plan;
    onAdd: (line: CartLine) => void;
}

const AddonRow: FC<AddonRowProps> = ({ plan, onAdd }) => {
    const { t } = useTranslation();
    const [qty, setQty] = useState(1);

    // Unit label — per-GB / per-day distinguishable at a glance.
    const unitLabel = useMemo(() => {
        if (plan.kind === "flexible_traffic") {
            return t("page.billing.purchase.addon.unit_gb");
        }
        if (plan.kind === "flexible_duration") {
            return t("page.billing.purchase.addon.unit_day");
        }
        return "";
    }, [plan.kind, t]);

    const lineTotal = plan.price_cny_fen * qty;

    const handleQtyChange = (raw: string) => {
        const parsed = Number.parseInt(raw, 10);
        // Clamp at 1 — flexible addons with qty=0 are meaningless
        // and the backend rejects them.
        if (!Number.isFinite(parsed) || parsed < 1) {
            setQty(1);
            return;
        }
        setQty(parsed);
    };

    const inputId = `addon-qty-${plan.id}`;

    return (
        <div className="flex flex-row gap-3 items-end p-3 border rounded-lg">
            <div className="flex-1">
                <div className="text-sm font-medium">
                    {plan.display_name_en}
                </div>
                <div className="text-xs text-muted-foreground">
                    {formatPriceCny(plan.price_cny_fen)} / {unitLabel}
                </div>
            </div>
            <div className="flex flex-col gap-1 w-32">
                <Label htmlFor={inputId} className="text-xs">
                    {t("page.billing.purchase.addon.quantity")}
                </Label>
                <div className="flex flex-row gap-1">
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setQty((q) => Math.max(1, q - 1))}
                    >
                        −
                    </Button>
                    <Input
                        id={inputId}
                        type="number"
                        min={1}
                        value={qty}
                        onChange={(e) => handleQtyChange(e.target.value)}
                        className="text-center tabular-nums"
                    />
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setQty((q) => q + 1)}
                    >
                        +
                    </Button>
                </div>
            </div>
            <div className="w-24 text-right tabular-nums font-semibold">
                {formatPriceCny(lineTotal)}
            </div>
            <Button
                type="button"
                onClick={() => onAdd({ plan_id: plan.id, quantity: qty })}
            >
                {t("page.billing.purchase.addon.add")}
            </Button>
        </div>
    );
};

interface FlexibleAddonCalculatorProps {
    plans: Plan[];
    onAdd: (line: CartLine) => void;
}

export const FlexibleAddonCalculator: FC<FlexibleAddonCalculatorProps> = ({
    plans,
    onAdd,
}) => {
    const { t } = useTranslation();
    const flex = plans.filter(
        (p) =>
            p.kind === "flexible_traffic" || p.kind === "flexible_duration",
    );

    if (flex.length === 0) return null;

    return (
        <section className="flex flex-col gap-2">
            <h3 className="text-base font-semibold">
                {t("page.billing.purchase.addon.title")}
            </h3>
            <p className="text-sm text-muted-foreground">
                {t("page.billing.purchase.addon.subtitle")}
            </p>
            <div className="flex flex-col gap-2">
                {flex.map((plan) => (
                    <AddonRow key={plan.id} plan={plan} onAdd={onAdd} />
                ))}
            </div>
        </section>
    );
};
