/**
 * /hosts route — Nilou design system rewrite (Wave-A A2).
 *
 * Visual source: docs/design-system-source/project/site/lib/PanelPages1.jsx.
 * Nodes-style table chrome. Existing InboundHostsTable (sidebar entity table)
 * is preserved inside the card; KPI strip added above.
 *
 * Existing sub-routes preserved via <Outlet />.
 */
import { type FC, Suspense } from 'react';
import { createLazyFileRoute, Outlet } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { SudoRoute } from '@marzneshin/libs/sudo-routes';
import { Loading } from '@marzneshin/common/components';
import {
    PanelHead,
    KPI,
} from '@marzneshin/common/components/nilou';
import { InboundHostsTable } from '@marzneshin/modules/hosts';
import { useHostsQuery } from '@marzneshin/modules/hosts';

/* ------------------------------------------------------------------ */
/* KPI strip                                                            */
/* ------------------------------------------------------------------ */

function HostsKPIStrip() {
    const { t } = useTranslation();
    const { data } = useHostsQuery({ page: 1, size: 1000 });
    const hosts = data?.entities ?? [];
    const total = hosts.length;
    const active = hosts.filter((h) => !h.is_disabled).length;
    const disabled = hosts.filter((h) => h.is_disabled).length;

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 14,
                marginBottom: 24,
            }}
        >
            <KPI
                label={t('page.hosts.kpi.total', 'Total hosts')}
                value={String(total)}
                accent="teal"
            />
            <KPI
                label={t('page.hosts.kpi.active', 'Active')}
                value={String(active)}
                accent="emerald"
            />
            <KPI
                label={t('page.hosts.kpi.disabled', 'Disabled')}
                value={String(disabled)}
                accent="coral"
            />
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

export const HostsPage: FC = () => {
    const { t } = useTranslation();

    // No top-level "Add host" CTA: hosts are scoped to specific inbounds,
    // so creation lives inside InboundHostsTable per-inbound (route is
    // `/hosts/$inboundId/create`). Surfacing a generic "Add" button here
    // would require an inbound picker first, which clutters the page.
    return (
        <div style={{ padding: '28px 32px' }}>
            <PanelHead
                title={t('hosts', 'Hosts')}
                sub={t(
                    'page.hosts.sub',
                    'Reality / VLESS inbound configs',
                )}
            />

            <HostsKPIStrip />

            {/* Existing sidebar entity table — preserves inbound-based navigation */}
            <InboundHostsTable />

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </div>
    );
};

export const Route = createLazyFileRoute('/_dashboard/hosts')({
    component: () => (
        <SudoRoute>
            <HostsPage />
        </SudoRoute>
    ),
});
