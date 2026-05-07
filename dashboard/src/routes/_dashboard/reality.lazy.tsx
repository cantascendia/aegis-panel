/**
 * /reality — Reality audit page. Wave-B1 Nilou rewrite.
 *
 * Design: PanelHead + 4-KPI row (total/green/yellow/red) + card grid
 * (one NilouCard per audit target, repeat(auto-fit, minmax(360px, 1fr))).
 *
 * Data: useRealityAudit mutation (operator-initiated POST /api/reality/audit).
 * Existing AuditReportTable / FindingList components are preserved and
 * composed inside each target card.
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
    StatusDot,
} from '@marzneshin/common/components/nilou';
import { SudoRoute } from '@marzneshin/libs/sudo-routes';
import {
    useRealityAudit,
    FindingList,
} from '@marzneshin/modules/reality';
import type { Grade, ReportSummary, TargetResult } from '@marzneshin/modules/reality';
import { Button } from '@marzneshin/common/components';
import { Play, RefreshCw } from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const gradeTone = (grade: Grade): 'emerald' | 'amber' | 'coral' => {
    if (grade === 'green') return 'emerald';
    if (grade === 'yellow') return 'amber';
    return 'coral';
};

const gradeColor = (grade: Grade): string => {
    if (grade === 'green') return '#5bc0be';
    if (grade === 'yellow') return '#e8b04b';
    return '#e07856';
};

// ---------------------------------------------------------------------------
// KPI row
// ---------------------------------------------------------------------------

interface RealityKPIRowProps {
    summary: ReportSummary | null;
    isLoading: boolean;
}

const RealityKPIRow: FC<RealityKPIRowProps> = ({ summary, isLoading }) => {
    const { t } = useTranslation();

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
                label={t('page.reality.summary.total')}
                value={isLoading ? '…' : summary?.total ?? '—'}
                accent="teal"
            />
            <KPI
                label={t('page.reality.summary.green')}
                value={isLoading ? '…' : summary?.green ?? '—'}
                accent="emerald"
            />
            <KPI
                label={t('page.reality.summary.yellow')}
                value={isLoading ? '…' : summary?.yellow ?? '—'}
                accent="gold"
            />
            <KPI
                label={t('page.reality.summary.red')}
                value={isLoading ? '…' : summary?.red ?? '—'}
                accent="coral"
            />
        </div>
    );
};

// ---------------------------------------------------------------------------
// Target card
// ---------------------------------------------------------------------------

interface TargetCardProps {
    target: TargetResult;
}

const TargetCard: FC<TargetCardProps> = ({ target }) => {
    const { t } = useTranslation();
    const tone = gradeTone(target.grade);
    const color = gradeColor(target.grade);

    return (
        <NilouCard
            style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
        >
            {/* Card header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StatusDot tone={tone} size={10} />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                        style={{
                            fontWeight: 600,
                            fontSize: '0.95rem',
                            color: 'hsl(var(--foreground))',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {target.host}
                    </div>
                    <div
                        style={{
                            fontSize: '0.78rem',
                            color: 'hsl(var(--muted-foreground))',
                            fontFamily: 'var(--font-mono, ui-monospace)',
                            marginTop: 2,
                        }}
                    >
                        {target.sni}:{target.port}
                    </div>
                </div>
                {/* Score badge */}
                <div
                    style={{
                        fontFamily: 'var(--font-mono, ui-monospace)',
                        fontWeight: 700,
                        fontSize: '1.1rem',
                        color,
                    }}
                    title={t('page.reality.column.score')}
                >
                    {target.score}
                </div>
            </div>

            {/* Grade label */}
            <div
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '2px 10px',
                    borderRadius: 12,
                    background: `${color}20`,
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color,
                    alignSelf: 'flex-start',
                }}
            >
                {t(`page.reality.score.${target.grade}`)}
            </div>

            {/* Findings */}
            <div
                style={{
                    borderTop: '1px solid hsl(var(--border) / 0.4)',
                    marginTop: 4,
                    paddingTop: 8,
                }}
            >
                <FindingList findings={target.findings} />
            </div>
        </NilouCard>
    );
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const RealityPage: FC = () => {
    const { t } = useTranslation();
    const mutation = useRealityAudit();
    const report = mutation.data ?? null;
    const summary = report?.summary ?? null;

    const handleRun = () => {
        mutation.mutate({ source: 'db' });
    };

    const ButtonIcon = mutation.isPending ? RefreshCw : Play;
    const buttonLabel = mutation.isPending
        ? t('page.reality.running')
        : summary
          ? t('page.reality.rerun')
          : t('page.reality.run');

    return (
        <>
            <PanelHead
                title={t('page.reality.title')}
                sub={t('page.reality.kpi.sub', 'Per-target finding scores')}
                actions={
                    <Button onClick={handleRun} disabled={mutation.isPending}>
                        <ButtonIcon
                            size={14}
                            style={{
                                marginRight: 6,
                                animation: mutation.isPending
                                    ? 'spin 1s linear infinite'
                                    : 'none',
                            }}
                        />
                        {buttonLabel}
                    </Button>
                }
            />

            <RealityKPIRow summary={summary} isLoading={mutation.isPending} />

            {/* Error state */}
            {mutation.isError && (
                <NilouCard style={{ marginBottom: 16, borderColor: 'rgba(224,120,86,0.4)' }}>
                    <p
                        style={{
                            margin: 0,
                            color: '#e07856',
                            fontSize: '0.9rem',
                        }}
                    >
                        {t('page.reality.error.failed')}
                    </p>
                </NilouCard>
            )}

            {/* Pre-audit empty state */}
            {!report && !mutation.isPending && !mutation.isError && (
                <NilouCard>
                    <p
                        style={{
                            margin: 0,
                            textAlign: 'center',
                            color: 'hsl(var(--muted-foreground))',
                            fontSize: '0.9rem',
                        }}
                    >
                        {t('page.reality.empty')}
                    </p>
                </NilouCard>
            )}

            {/* No targets state */}
            {report && report.targets.length === 0 && (
                <NilouCard>
                    <p
                        style={{
                            margin: 0,
                            textAlign: 'center',
                            color: 'hsl(var(--muted-foreground))',
                            fontSize: '0.9rem',
                        }}
                    >
                        {t('page.reality.no_targets')}
                    </p>
                </NilouCard>
            )}

            {/* Target card grid */}
            {report && report.targets.length > 0 && (
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
                        gap: 16,
                    }}
                >
                    {report.targets.map((target) => (
                        <TargetCard
                            key={`${target.host}-${target.sni}-${target.port}`}
                            target={target}
                        />
                    ))}
                </div>
            )}

            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </>
    );
};

export const Route = createLazyFileRoute('/_dashboard/reality')({
    component: () => (
        <SudoRoute>
            <RealityPage />
        </SudoRoute>
    ),
});
