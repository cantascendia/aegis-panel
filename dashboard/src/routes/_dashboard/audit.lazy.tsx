/**
 * /audit — Audit log page. Wave-B1 Nilou rewrite.
 *
 * Design: PanelHead + 3-KPI row (total / failures-24h / today) +
 * filter NilouCard (existing filter UI) + existing AuditEventsTable.
 *
 * Data: useAuditEvents hook — GET /api/audit/events.
 * Existing AuditEventsTable inner table / filter / pagination is preserved.
 *
 * Gate: sudo-only route — wrapped in <SudoRoute> matching original.
 */
import { type FC, Suspense } from 'react';
import { createLazyFileRoute, Outlet } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Loading } from '@marzneshin/common/components';
import {
    KPI,
    NilouCard,
    PanelHead,
} from '@marzneshin/common/components/nilou';
import { SudoRoute } from '@marzneshin/libs/sudo-routes';
import { useAuditEvents, AuditEventsTable } from '@marzneshin/modules/audit';
import type { AuditEventSummary } from '@marzneshin/modules/audit';
import { Button } from '@marzneshin/common/components';
import { RefreshCw } from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** ISO-8601 UTC ts → true if it falls within the last 24 hours */
const isLast24h = (iso: string): boolean => {
    try {
        const ts = new Date(iso).getTime();
        return Date.now() - ts < 24 * 60 * 60 * 1000;
    } catch {
        return false;
    }
};

/** ISO-8601 UTC ts → true if it is today (local time) */
const isToday = (iso: string): boolean => {
    try {
        const d = new Date(iso);
        const now = new Date();
        return (
            d.getFullYear() === now.getFullYear() &&
            d.getMonth() === now.getMonth() &&
            d.getDate() === now.getDate()
        );
    } catch {
        return false;
    }
};

// ---------------------------------------------------------------------------
// KPI row
// ---------------------------------------------------------------------------

interface AuditKPIRowProps {
    items: AuditEventSummary[];
    total: number;
    isLoading: boolean;
}

const AuditKPIRow: FC<AuditKPIRowProps> = ({ items, total, isLoading }) => {
    const { t } = useTranslation();

    const failures24h = items.filter(
        (e) => e.result === 'failure' && isLast24h(e.ts),
    ).length;
    const todayCount = items.filter((e) => isToday(e.ts)).length;

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 16,
                marginBottom: 24,
            }}
        >
            <KPI
                label={t('page.audit.kpi.total', 'Total events')}
                value={isLoading ? '…' : total}
                accent="teal"
            />
            <KPI
                label={t('page.audit.kpi.failures', 'Failures (24 h)')}
                value={isLoading ? '…' : failures24h}
                accent={failures24h > 0 ? 'coral' : 'emerald'}
                trend={failures24h > 0 ? 'down' : 'up'}
            />
            <KPI
                label={t('page.audit.kpi.today', 'Today')}
                value={isLoading ? '…' : todayCount}
                accent="gold"
            />
        </div>
    );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const AuditPage: FC = () => {
    const { t } = useTranslation();
    // Load first page to derive KPI counts (limit=50 default)
    const { data, isLoading, refetch } = useAuditEvents({ limit: 50 });
    const items = data?.items ?? [];
    const total = data?.total_returned ?? items.length;

    return (
        <>
            <PanelHead
                title={t('page.audit.title')}
                sub={t('page.audit.sub', 'All admin operations')}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetch()}
                    >
                        <RefreshCw size={14} style={{ marginRight: 6 }} />
                        {t('page.audit.action.refresh')}
                    </Button>
                }
            />

            <AuditKPIRow items={items} total={total} isLoading={isLoading} />

            {/* Full table — retains existing filter + pagination logic */}
            <NilouCard pad={0}>
                <AuditEventsTable />
            </NilouCard>

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    );
};

export const Route = createLazyFileRoute('/_dashboard/audit')({
    component: () => (
        <SudoRoute>
            <AuditPage />
        </SudoRoute>
    ),
});
