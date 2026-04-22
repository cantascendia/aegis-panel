import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { ChannelsTable } from "@marzneshin/modules/billing";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const BillingChannelsPage: FC = () => {
    const { t } = useTranslation();
    return (
        <Page
            title={t("page.billing.channels.title")}
            className="sm:w-screen md:w-full"
        >
            <ChannelsTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/channels")({
    component: () => (
        <SudoRoute>
            <BillingChannelsPage />
        </SudoRoute>
    ),
});
