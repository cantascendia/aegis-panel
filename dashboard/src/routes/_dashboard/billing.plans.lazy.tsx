import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { PlansTable } from "@marzneshin/modules/billing";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const BillingPlansPage: FC = () => {
    const { t } = useTranslation();
    return (
        <Page
            title={t("page.billing.plans.title", "Plans")}
            className="sm:w-screen md:w-full"
        >
            <PlansTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/plans")({
    component: () => (
        <SudoRoute>
            <BillingPlansPage />
        </SudoRoute>
    ),
});
