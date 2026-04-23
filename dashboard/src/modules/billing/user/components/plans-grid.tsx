import { type FC } from "react";
import { useTranslation } from "react-i18next";

import type { CartLine, Plan } from "../../types";
import { PlanCard } from "./plan-card";

/*
 * Grid of fixed plans. Flexible plans (`flexible_traffic`,
 * `flexible_duration`) are NOT rendered here — they live in the
 * addon calculator panel below the grid.
 *
 * Sorted by `sort_order` ascending (backend already does so; this
 * component just renders in the order it received).
 */

interface PlansGridProps {
    plans: Plan[];
    cart: CartLine[];
    onAdd: (plan: Plan) => void;
}

export const PlansGrid: FC<PlansGridProps> = ({ plans, cart, onAdd }) => {
    const { t } = useTranslation();
    const fixedPlans = plans.filter((p) => p.kind === "fixed");

    if (fixedPlans.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-10 border rounded-lg">
                {t("page.billing.purchase.empty_plans")}
            </div>
        );
    }

    const inCart = (planId: number) =>
        cart.some((line) => line.plan_id === planId);

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {fixedPlans.map((plan) => (
                <PlanCard
                    key={plan.id}
                    plan={plan}
                    onAdd={onAdd}
                    alreadyInCart={inCart(plan.id)}
                />
            ))}
        </div>
    );
};
