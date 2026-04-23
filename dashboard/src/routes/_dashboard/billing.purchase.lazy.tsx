import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, useNavigate } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import {
    CartSummary,
    CheckoutPaymentPicker,
    FlexibleAddonCalculator,
    PlansGrid,
    useCheckout,
    useUserChannels,
    useUserPlans,
} from "@marzneshin/modules/billing/user";
import type {
    CartLine,
    CheckoutChannelId,
    Plan,
} from "@marzneshin/modules/billing/types";

/*
 * User purchase page.
 *
 * Flow:
 * 1. Load plans + channels in parallel (useUserPlans + useUserChannels).
 * 2. User picks a fixed plan from the grid or configures a
 *    flexible-addon line, either adds to cart.
 * 3. CheckoutPaymentPicker renders below the grid; on "Pay", we
 *    call useCheckout().
 * 4. On success:
 *    - TRC20: navigate to /dashboard/billing/invoice/{id} (rendered
 *      by A.3.3's billing.invoice.lazy.tsx stub)
 *    - EPay: window.location.assign(payment_url) for the external
 *      码商 page (full redirect, leaves the SPA).
 *
 * No SudoRoute wrap — this is deliberately the user-facing route.
 * Non-sudo users can reach it; the sidebar entry is also gated in
 * `sidebarItemsNonSudoAdmin`.
 */

const BillingPurchasePage: FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const { data: plans, isLoading: loadingPlans, isError: plansErr } =
        useUserPlans();
    const {
        data: channels,
        isLoading: loadingChannels,
        isError: channelsErr,
    } = useUserChannels();

    const [cart, setCart] = useState<CartLine[]>([]);

    const addFixedPlan = (plan: Plan) => {
        // Fixed plans are unique in-cart — one Starter 30d shouldn't
        // be add-twice. Flexible addons CAN appear multiple times
        // but we consolidate by summing quantity via addFlexibleLine.
        setCart((prev) => {
            if (prev.some((l) => l.plan_id === plan.id)) return prev;
            return [...prev, { plan_id: plan.id, quantity: 1 }];
        });
    };

    const addFlexibleLine = (line: CartLine) => {
        setCart((prev) => {
            const existing = prev.find((l) => l.plan_id === line.plan_id);
            if (existing) {
                return prev.map((l) =>
                    l.plan_id === line.plan_id
                        ? { ...l, quantity: l.quantity + line.quantity }
                        : l,
                );
            }
            return [...prev, line];
        });
    };

    const removeLine = (planId: number) => {
        setCart((prev) => prev.filter((l) => l.plan_id !== planId));
    };

    const checkout = useCheckout();

    const onPay = async (channelId: CheckoutChannelId) => {
        const res = await checkout.mutateAsync({
            lines: cart,
            channel: channelId,
        });
        if (channelId === "trc20") {
            // Internal SPA route for the live polling screen.
            navigate({
                to: "/billing/invoice/$id" as unknown as "/",
                params: { id: String(res.invoice_id) },
            });
        } else if (res.payment_url) {
            // External 码商 redirect.
            window.location.assign(res.payment_url);
        }
        setCart([]);
    };

    if (loadingPlans || loadingChannels) return <Loading />;
    if (plansErr || channelsErr || !plans || !channels) {
        return (
            <Page title={t("page.billing.purchase.title")}>
                <div className="text-sm text-destructive p-3 rounded-md bg-destructive/10">
                    {t("page.billing.purchase.load_error")}
                </div>
            </Page>
        );
    }

    return (
        <Page
            title={t("page.billing.purchase.title")}
            className="sm:w-screen md:w-full"
        >
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
                <div className="flex flex-col gap-6">
                    <section>
                        <h2 className="text-xl font-semibold mb-3">
                            {t("page.billing.purchase.plans_title")}
                        </h2>
                        <PlansGrid
                            plans={plans}
                            cart={cart}
                            onAdd={addFixedPlan}
                        />
                    </section>
                    <FlexibleAddonCalculator
                        plans={plans}
                        onAdd={addFlexibleLine}
                    />
                    {cart.length > 0 && (
                        <section className="flex flex-col gap-3">
                            <h2 className="text-xl font-semibold">
                                {t("page.billing.purchase.pay_title")}
                            </h2>
                            <CheckoutPaymentPicker
                                channels={channels}
                                onPay={onPay}
                                pending={checkout.isPending}
                            />
                        </section>
                    )}
                </div>
                <CartSummary
                    lines={cart}
                    plans={plans}
                    onRemove={removeLine}
                    onCheckout={() => {
                        /* Checkout picker handles actual mutation;
                         * this button is a scroll-into-view hint
                         * for mobile viewports. A small UX nicety
                         * we can wire up later. */
                    }}
                    checkoutPending={checkout.isPending}
                />
            </div>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/purchase")({
    component: BillingPurchasePage,
});
