import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { HealthExtendedTable } from "@marzneshin/modules/health";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const HealthPage: FC = () => {
    const { t } = useTranslation();
    const titleText = t("page.health.title");
    return (
        <Page title={titleText} className="sm:w-screen md:w-full">
            <HealthExtendedTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/health")({
    component: () => (
        <SudoRoute>
            <HealthPage />
        </SudoRoute>
    ),
});
