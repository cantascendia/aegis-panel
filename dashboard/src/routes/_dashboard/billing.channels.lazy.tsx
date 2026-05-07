/**
 * /billing/channels — TRC20 + EPay payment channel configuration. Wave-B2 Nilou rewrite.
 *
 * Layout: PanelHead → NilouCard wrapping ChannelsTable.
 * All channel CRUD (ChannelFormDialog / useCreateChannel / useUpdateChannel)
 * lives inside ChannelsTable — preserved untouched.
 *
 * Forbidden-path note: billing UI per .claude/rules/forbidden-paths.md.
 * PR must carry the `requires-double-review` label.
 */

import { type FC, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { createLazyFileRoute, Outlet } from "@tanstack/react-router";

import { Loading } from "@marzneshin/common/components";
import { NilouCard, PanelHead } from "@marzneshin/common/components/nilou";
import { ChannelsTable } from "@marzneshin/modules/billing";
import { SudoRoute } from "@marzneshin/libs/sudo-routes";

export const BillingChannelsPage: FC = () => {
    const { t } = useTranslation();

    return (
        <>
            <PanelHead
                title={t("page.billing.channels.title")}
                sub={t("page.billing.channels.subtitle")}
            />

            <NilouCard pad={0}>
                <ChannelsTable />
            </NilouCard>

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    );
};

export const Route = createLazyFileRoute("/_dashboard/billing/channels")({
    component: () => (
        <SudoRoute>
            <BillingChannelsPage />
        </SudoRoute>
    ),
});
