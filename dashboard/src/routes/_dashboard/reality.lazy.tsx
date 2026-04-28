import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { AuditReportTable } from "@marzneshin/modules/reality";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const RealityPage: FC = () => {
    const { t } = useTranslation();
    const titleText = t("page.reality.title");
    return (
        <Page title={titleText} className="sm:w-screen md:w-full">
            <AuditReportTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/reality")({
    component: () => (
        <SudoRoute>
            <RealityPage />
        </SudoRoute>
    ),
});
