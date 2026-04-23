import { type FC } from "react";
import { useTranslation } from "react-i18next";
import i18n from "@marzneshin/features/i18n";

import { Button } from "@marzneshin/common/components";

import type { Plan } from "../../types";

/*
 * Single fixed-plan card.
 *
 * Reads `display_name_i18n[currentLocale] ?? display_name_en` so
 * operators can localize names per plan without code changes
 * (`Plan.display_name_i18n` JSON column).
 *
 * Flexible plans (`kind !== "fixed"`) render via a different
 * component (`flexible-addon-calculator.tsx`) because the UX is
 * fundamentally different — sliders instead of a single CTA.
 */

const formatPriceCny = (fen: number) => `¥${(fen / 100).toFixed(2)}`;

const resolveLocalizedName = (plan: Plan): string => {
    const locale = i18n.language;
    return plan.display_name_i18n?.[locale] ?? plan.display_name_en;
};

interface PlanCardProps {
    plan: Plan;
    onAdd: (plan: Plan) => void;
    /** True if this plan is already in the cart — swap the "Add"
     *  CTA for a disabled "Added" state so the user doesn't
     *  accidentally add the same fixed plan twice. */
    alreadyInCart: boolean;
}

export const PlanCard: FC<PlanCardProps> = ({
    plan,
    onAdd,
    alreadyInCart,
}) => {
    const { t } = useTranslation();
    const name = resolveLocalizedName(plan);

    // Fixed plans always carry both GB and days; render defensively
    // in case the backend yields a half-filled row.
    const shape: string[] = [];
    if (plan.data_limit_gb !== null) shape.push(`${plan.data_limit_gb} GB`);
    if (plan.duration_days !== null) shape.push(`${plan.duration_days} d`);

    return (
        <div className="flex flex-col gap-3 p-4 border rounded-lg bg-card">
            <div className="flex flex-col gap-1">
                <h3 className="text-lg font-semibold">{name}</h3>
                <div className="text-sm text-muted-foreground">
                    {shape.join(" / ")}
                </div>
            </div>
            <div className="text-2xl font-bold tabular-nums">
                {formatPriceCny(plan.price_cny_fen)}
            </div>
            <Button
                variant={alreadyInCart ? "secondary" : "default"}
                disabled={alreadyInCart}
                onClick={() => onAdd(plan)}
                className="w-full"
            >
                {alreadyInCart
                    ? t("page.billing.purchase.plan_card.already_added")
                    : t("page.billing.purchase.plan_card.add_to_cart")}
            </Button>
        </div>
    );
};
