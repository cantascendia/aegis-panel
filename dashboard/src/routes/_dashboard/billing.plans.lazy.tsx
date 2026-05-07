/**
 * /billing/plans — Plan tier definitions. Wave-B2 Nilou rewrite.
 *
 * Restyled to PanelHead + NilouCard wrapper. All CRUD dialogs
 * (PlanFormDialog) live inside PlansTable — preserved untouched.
 * Mutations (useCreatePlan / useUpdatePlan) are owned by PlansTable.
 * This file only changes the layout shell; billing logic is untouched.
 *
 * Forbidden-path note: billing UI per .claude/rules/forbidden-paths.md.
 * This PR must carry the `requires-double-review` label.
 */

import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading } from "@marzneshin/common/components";
import { NilouCard, PanelHead } from "@marzneshin/common/components/nilou";
import { PlansTable } from "@marzneshin/modules/billing";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

export const BillingPlansPage: FC = () => {
    const { t } = useTranslation();

    return (
        <>
            <PanelHead
                title={t("page.billing.plans.title")}
                sub={t("page.billing.plans.subtitle")}
            />

            <NilouCard pad={0}>
                <PlansTable />
            </NilouCard>

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/plans")({
    component: () => (
        <SudoRoute>
            <BillingPlansPage />
        </SudoRoute>
    ),
});
