import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, useNavigate } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";
import {
    CartSummary,
    CheckoutPaymentPicker,
    FlexibleAddonCalculator,
    PlansGrid,
    UserSelector,
    useCheckout,
    useUserChannels,
    useUserPlans,
} from "@marzneshin/modules/billing/user";
import type {
    CartLine,
    Plan,
} from "@marzneshin/modules/billing/types";

/*
 * Admin checkout-on-behalf-of-user (per BRIEF-billing-user-auth-blocker
 * option A).
 *
 * Flow:
 * 1. Operator picks a VPN user via UserSelector
 *    (`GET /users?username=<typed>` debounced).
 * 2. Operator picks plans (PlansGrid) and/or addon quantities
 *    (FlexibleAddonCalculator) — same components as the original
 *    skeleton.
 * 3. CheckoutPaymentPicker tabs render once cart is non-empty.
 * 4. On Pay:
 *    - EPay → backend returns external 码商 URL → operator copies
 *      and forwards to user via Telegram/email
 *    - TRC20 → backend creates invoice → operator navigates to
 *      `/billing/invoices/{id}` (existing admin invoice detail
 *      page from PR #35) to copy memo / amount / countdown
 *
 * Wrapped in SudoRoute — only sudo admins can sell. Non-sudo
 * admins (per-customer support staff) are intentionally locked out
 * because checkout creates a real money record.
 */

const BillingCheckoutPage: FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const [pickedUser, setPickedUser] = useState<{ id: number; username: string } | null>(null);
    const [cart, setCart] = useState<CartLine[]>([]);

    const {
        data: plans,
        isLoading: loadingPlans,
        isError: plansErr,
    } = useUserPlans();
    const {
        data: channels,
        isLoading: loadingChannels,
        isError: channelsErr,
    } = useUserChannels();

    const addFixedPlan = (plan: Plan) => {
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

    const onPay = async (channelId: string) => {
        if (!pickedUser) return;
        const isTrc20 = channelId === "trc20";
        const channel_code = isTrc20 ? "trc20" : channelId.replace(/^epay:/, "");
        // Build absolute SPA URLs for success/cancel redirects.
        const origin =
            typeof window !== "undefined" ? window.location.origin : "";
        const res = await checkout.mutateAsync({
            user_id: pickedUser.id,
            channel_code,
            lines: cart,
            success_url: `${origin}/billing/invoices`,
            cancel_url: `${origin}/billing/checkout`,
            subject: `Aegis order for ${pickedUser.username}`,
        });
        // After invoice creation:
        //  - EPay: open the external 码商 URL in a new tab so the
        //    operator can copy it and ping the user via Telegram.
        //    Don't `assign` (would navigate the operator away).
        //  - TRC20: jump to admin invoice detail (PR #35) which
        //    shows memo + amount + countdown.
        if (isTrc20) {
            navigate({
                to: "/billing/invoices",
            });
        } else if (res.payment_url) {
            window.open(res.payment_url, "_blank", "noopener,noreferrer");
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
                    <section className="flex flex-col gap-2">
                        <h2 className="text-xl font-semibold">
                            {t("page.billing.purchase.user_section_title")}
                        </h2>
                        <UserSelector
                            selected={pickedUser}
                            onSelect={setPickedUser}
                        />
                    </section>

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
                    {cart.length > 0 && pickedUser && (
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
                    {cart.length > 0 && !pickedUser && (
                        <div className="text-sm text-muted-foreground p-3 rounded-md bg-muted">
                            {t("page.billing.purchase.user_selector.required_before_pay")}
                        </div>
                    )}
                </div>
                <CartSummary
                    lines={cart}
                    plans={plans}
                    onRemove={removeLine}
                    onCheckout={() => {
                        /* Picker handles actual mutation; this
                         * cart-summary button is a hint to scroll
                         * to the picker on mobile. Wire later. */
                    }}
                    checkoutPending={checkout.isPending}
                />
            </div>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/purchase")({
    component: () => (
        <SudoRoute>
            <BillingCheckoutPage />
        </SudoRoute>
    ),
});
