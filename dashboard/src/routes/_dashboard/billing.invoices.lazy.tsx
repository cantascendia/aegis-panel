import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { InvoicesTable } from "@marzneshin/modules/billing";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const BillingInvoicesPage: FC = () => {
    const { t } = useTranslation();
    return (
        <Page
            title={t("page.billing.invoices.title")}
            className="sm:w-screen md:w-full"
        >
            <InvoicesTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/invoices")({
    component: () => (
        <SudoRoute>
            <BillingInvoicesPage />
        </SudoRoute>
    ),
});
