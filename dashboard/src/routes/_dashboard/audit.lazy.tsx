import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading, Page } from "@marzneshin/common/components";
import { AuditEventsTable } from "@marzneshin/modules/audit";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

const AuditPage: FC = () => {
    const { t } = useTranslation();
    const titleText = t("page.audit.title");
    return (
        <Page title={titleText} className="sm:w-screen md:w-full">
            <AuditEventsTable />
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </Page>
    );
};

export const Route = createLazyFileRoute("/_dashboard/audit")({
    component: () => (
        <SudoRoute>
            <AuditPage />
        </SudoRoute>
    ),
});
