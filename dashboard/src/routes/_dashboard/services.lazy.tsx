/**
 * /services route — Nilou design system rewrite (Wave-A A2).
 *
 * Visual source: docs/design-system-source/project/site/lib/PanelPages1.jsx.
 * Nodes-style table chrome. Existing ServicesTable preserved inside the card;
 * KPI strip added above.
 *
 * Existing sub-routes preserved via <Outlet />.
 */
import { type FC, Suspense } from 'react';
import { createLazyFileRoute, Outlet, useNavigate } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { SudoRoute } from '@marzneshin/libs/sudo-routes';
import { Loading } from '@marzneshin/common/components';
import {
    PanelHead,
    KPI,
} from '@marzneshin/common/components/nilou';
import { ServicesTable } from '@marzneshin/modules/services';
import { useServicesQuery } from '@marzneshin/modules/services';
import { Button } from '@marzneshin/common/components';
import { Plus } from 'lucide-react';

/* ------------------------------------------------------------------ */
/* KPI strip                                                            */
/* ------------------------------------------------------------------ */

function ServicesKPIStrip() {
    const { t } = useTranslation();
    const { data } = useServicesQuery({ page: 1, size: 1000 });
    const services = data?.entities ?? [];
    const total = services.length;
    /* "active" heuristic: services with at least one inbound assigned */
    const active = services.filter((s) => s.inbound_ids.length > 0).length;

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 14,
                marginBottom: 24,
            }}
        >
            <KPI
                label={t('page.services.kpi.total', 'Total services')}
                value={String(total)}
                accent="teal"
            />
            <KPI
                label={t('page.services.kpi.active', 'Active')}
                value={String(active)}
                accent="emerald"
            />
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

export const ServicesPage: FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate({ from: '/services' });

    return (
        <div style={{ padding: '28px 32px' }}>
            <PanelHead
                title={t('services', 'Services')}
                sub={t(
                    'page.services.sub',
                    'Service templates linking inbounds to plans',
                )}
                actions={
                    <Button
                        variant="default"
                        size="sm"
                        onClick={() => navigate({ to: '/services/create' })}
                    >
                        <Plus size={14} style={{ marginRight: 6 }} />
                        {t('page.services.add', 'Add service')}
                    </Button>
                }
            />

            <ServicesKPIStrip />

            {/* Existing entity table — preserves dialogs and navigation */}
            <ServicesTable />

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </div>
    );
};

export const Route = createLazyFileRoute('/_dashboard/services')({
    component: () => (
        <SudoRoute>
            <ServicesPage />
        </SudoRoute>
    ),
});
