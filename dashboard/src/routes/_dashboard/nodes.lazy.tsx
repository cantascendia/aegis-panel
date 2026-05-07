/**
 * /nodes route — Nilou design system rewrite (Wave-A A2).
 *
 * Visual source: docs/design-system-source/project/site/lib/PanelPages1.jsx
 * lines 150-235. 1:1 copy of NodesPage chrome, operator marznode data.
 *
 * Existing sub-routes (nodeId dialogs, log viewer) preserved via <Outlet />.
 * Existing navigation callbacks (onEdit, onDelete, onOpen) preserved.
 */
import { useState, type FC, Suspense } from 'react';
import { createLazyFileRoute, Outlet, useNavigate } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { SudoRoute } from '@marzneshin/libs/sudo-routes';
import { Loading } from '@marzneshin/common/components';
import {
    PanelHead,
    NilouCard,
    StatusDot,
    Pill,
    NilouIcon,
} from '@marzneshin/common/components/nilou';
import { useNodesQuery } from '@marzneshin/modules/nodes';
import type { NodeType } from '@marzneshin/modules/nodes';
import { Button } from '@marzneshin/common/components';
import { RefreshCw, Plus } from 'lucide-react';

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/* ------------------------------------------------------------------ */

/** Map marznode status to StatusDot tone */
function statusTone(status: NodeType['status']): 'emerald' | 'amber' | 'coral' | 'muted' {
    switch (status) {
        case 'healthy': return 'emerald';
        case 'unhealthy': return 'coral';
        case 'disabled': return 'muted';
        default: return 'amber';
    }
}

/** Derive a region string from node address (best-effort) */
function deriveRegion(node: NodeType): string {
    return node.address;
}

/** Determine whether node is "premium" (usage_coefficient > 1) */
function isPremium(node: NodeType): boolean {
    return (node.usage_coefficient ?? 1) > 1;
}

/* ------------------------------------------------------------------ */
/* Filter tab pill                                                      */
/* ------------------------------------------------------------------ */

const FILTER_TAB_ACTIVE: React.CSSProperties = {
    padding: '7px 12px',
    border: 0,
    borderRadius: 6,
    background: 'rgba(58,145,136,0.10)',
    color: 'var(--brand-teal, #3a9188)',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: '0.86rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
};

const FILTER_TAB_IDLE: React.CSSProperties = {
    ...FILTER_TAB_ACTIVE,
    background: 'transparent',
    color: 'hsl(var(--muted-foreground))',
    fontWeight: 500,
};

/* ------------------------------------------------------------------ */
/* Load bar                                                             */
/* ------------------------------------------------------------------ */

function LoadBar({ pct, tone }: { pct: number; tone: string }) {
    const barColor =
        tone === 'amber'
            ? 'var(--accent-amber, #e8b04b)'
            : tone === 'coral'
              ? 'var(--accent-coral, #e07856)'
              : 'var(--brand-teal, #3a9188)';

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
                style={{
                    flex: 1,
                    height: 5,
                    background: 'hsl(var(--muted) / 0.4)',
                    borderRadius: 999,
                    overflow: 'hidden',
                }}
            >
                <div
                    style={{
                        width: `${Math.min(100, Math.max(0, pct))}%`,
                        height: '100%',
                        background: barColor,
                    }}
                />
            </div>
            <span
                style={{
                    fontSize: '0.78rem',
                    color: 'hsl(var(--muted-foreground))',
                    fontFamily: 'var(--font-mono, ui-monospace)',
                    width: 30,
                    textAlign: 'right',
                }}
            >
                {pct}%
            </span>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Icon button                                                          */
/* ------------------------------------------------------------------ */

const iconBtnStyle: React.CSSProperties = {
    background: 'transparent',
    border: 0,
    color: 'hsl(var(--muted-foreground))',
    cursor: 'pointer',
    padding: 6,
    display: 'inline-grid',
    placeItems: 'center',
    borderRadius: 6,
};

/* ------------------------------------------------------------------ */
/* Table header cell                                                    */
/* ------------------------------------------------------------------ */

const TH_STYLE: React.CSSProperties = {
    padding: '11px 18px',
    fontSize: '0.74rem',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: 'hsl(var(--muted-foreground))',
    fontWeight: 600,
    borderBottom: '1px solid hsl(var(--border))',
    textAlign: 'left',
};

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

const FILTER_ALL = 'all';

export const NodesPage: FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate({ from: '/nodes' });
    const [filter, setFilter] = useState<string>(FILTER_ALL);
    const [search, setSearch] = useState('');

    const { data } = useNodesQuery({ page: 1, size: 100 });
    const nodes: NodeType[] = data?.entities ?? [];

    /* Unique status "tags" for filter tabs */
    const statusCounts = nodes.reduce<Record<string, number>>((acc, n) => {
        const s = n.status;
        acc[s] = (acc[s] ?? 0) + 1;
        return acc;
    }, {});

    const filtered = nodes.filter((n) => {
        const matchFilter = filter === FILTER_ALL || n.status === filter;
        const matchSearch =
            !search ||
            n.name.toLowerCase().includes(search.toLowerCase()) ||
            n.address.toLowerCase().includes(search.toLowerCase());
        return matchFilter && matchSearch;
    });

    const regions = new Set(nodes.map((n) => n.address.split('.')[1] ?? '')).size;

    const onOpen = (node: NodeType) =>
        navigate({ to: '/nodes/$nodeId', params: { nodeId: String(node.id) } });
    const onEdit = (node: NodeType) =>
        navigate({ to: '/nodes/$nodeId/edit', params: { nodeId: String(node.id) } });
    const onDelete = (node: NodeType) =>
        navigate({ to: '/nodes/$nodeId/delete', params: { nodeId: String(node.id) } });

    /* Filter tabs: All + per-status */
    const tabs: Array<[string, string, number]> = [
        [FILTER_ALL, t('page.nodes.filter.all', 'All'), nodes.length],
        ...Object.entries(statusCounts).map(
            ([s, n]) => [s, t(`page.nodes.status.${s}`, s), n] as [string, string, number],
        ),
    ];

    return (
        <div style={{ padding: '28px 32px' }}>
            <PanelHead
                title={t('nodes', 'Nodes')}
                sub={t('page.nodes.sub', {
                    count: nodes.length,
                    regions,
                    defaultValue: `${nodes.length} nodes across ${regions} regions`,
                })}
                actions={
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                /* query client invalidation is handled by react-query;
                                   navigate to self to trigger a refetch trigger */
                                window.location.reload();
                            }}
                        >
                            <RefreshCw size={14} style={{ marginRight: 6 }} />
                            {t('page.nodes.sync', 'Sync')}
                        </Button>
                        <Button
                            variant="default"
                            size="sm"
                            onClick={() => navigate({ to: '/nodes/create' })}
                        >
                            <Plus size={14} style={{ marginRight: 6 }} />
                            {t('page.nodes.add', 'Add node')}
                        </Button>
                    </>
                }
            />

            <NilouCard pad={0} style={{ marginBottom: 14 }}>
                {/* Filter / search bar */}
                <div
                    style={{
                        display: 'flex',
                        gap: 4,
                        padding: 14,
                        borderBottom: '1px solid hsl(var(--border) / 0.5)',
                        flexWrap: 'wrap',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                    }}
                >
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {tabs.map(([k, l, n]) => (
                            <button
                                key={k}
                                onClick={() => setFilter(k)}
                                style={filter === k ? FILTER_TAB_ACTIVE : FILTER_TAB_IDLE}
                                type="button"
                            >
                                {l}
                                <span
                                    style={{
                                        fontSize: '0.74rem',
                                        color:
                                            filter === k
                                                ? 'var(--brand-teal-deep, #1d5e58)'
                                                : 'hsl(var(--muted-foreground))',
                                    }}
                                >
                                    {n}
                                </span>
                            </button>
                        ))}
                    </div>
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            color: 'hsl(var(--muted-foreground))',
                            fontSize: '0.84rem',
                        }}
                    >
                        <NilouIcon name="search" size={14} />
                        <input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder={t('filter', 'Filter…')}
                            style={{
                                border: 0,
                                background: 'transparent',
                                outline: 'none',
                                fontFamily: 'inherit',
                                fontSize: '0.86rem',
                                width: 120,
                                color: 'hsl(var(--foreground))',
                            }}
                        />
                    </div>
                </div>

                {/* Nodes table */}
                <table
                    style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.9rem',
                    }}
                >
                    <thead>
                        <tr style={{ background: 'hsl(var(--muted) / 0.3)', textAlign: 'left' }}>
                            {[
                                t('page.nodes.col.region', 'Region'),
                                t('page.nodes.col.hostname', 'Hostname'),
                                t('page.nodes.col.protocol', 'Protocol'),
                                t('page.nodes.col.mult', 'Mult.'),
                                t('page.nodes.col.latency', 'Latency'),
                                t('page.nodes.col.load', 'Load'),
                                '',
                            ].map((h, i) => (
                                <th key={`${h}-${i}`} style={TH_STYLE}>
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.length === 0 && (
                            <tr>
                                <td
                                    colSpan={7}
                                    style={{
                                        padding: '32px 18px',
                                        textAlign: 'center',
                                        color: 'hsl(var(--muted-foreground))',
                                        fontSize: '0.9rem',
                                    }}
                                >
                                    {t('page.nodes.empty', 'No nodes found.')}
                                </td>
                            </tr>
                        )}
                        {filtered.map((node, i) => {
                            const tone = statusTone(node.status);
                            const premium = isPremium(node);
                            const mult =
                                node.usage_coefficient === 1
                                    ? '1x'
                                    : `${node.usage_coefficient}x`;
                            const region = deriveRegion(node);

                            return (
                                <tr
                                    key={node.id}
                                    onClick={() => onOpen(node)}
                                    style={{
                                        borderBottom:
                                            i < filtered.length - 1
                                                ? '1px solid hsl(var(--border) / 0.4)'
                                                : 'none',
                                        cursor: 'pointer',
                                    }}
                                >
                                    {/* Region */}
                                    <td style={{ padding: '14px 18px' }}>
                                        <div
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 10,
                                            }}
                                        >
                                            <StatusDot tone={tone} />
                                            <div>
                                                <div
                                                    style={{
                                                        color: 'hsl(var(--foreground))',
                                                        fontWeight: 500,
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: 8,
                                                    }}
                                                >
                                                    {node.name}
                                                    {premium && (
                                                        <Pill tone="gold">
                                                            {t('page.nodes.premium', 'Premium')}
                                                        </Pill>
                                                    )}
                                                </div>
                                                <div
                                                    style={{
                                                        fontSize: '0.78rem',
                                                        color: 'hsl(var(--muted-foreground))',
                                                        marginTop: 2,
                                                    }}
                                                >
                                                    {region}
                                                </div>
                                            </div>
                                        </div>
                                    </td>

                                    {/* Hostname */}
                                    <td
                                        className="font-mono"
                                        style={{
                                            padding: '14px 18px',
                                            fontFamily: 'var(--font-mono, ui-monospace)',
                                            fontSize: '0.82rem',
                                            color: 'hsl(var(--muted-foreground))',
                                        }}
                                    >
                                        {node.address}:{node.port}
                                    </td>

                                    {/* Protocol */}
                                    <td
                                        style={{
                                            padding: '14px 18px',
                                            color: 'hsl(var(--muted-foreground))',
                                        }}
                                    >
                                        {node.connection_backend ?? 'grpclib'}
                                    </td>

                                    {/* Mult */}
                                    <td
                                        style={{
                                            padding: '14px 18px',
                                            fontFamily: 'var(--font-mono, ui-monospace)',
                                            color:
                                                mult === '1x'
                                                    ? 'hsl(var(--muted-foreground))'
                                                    : 'var(--brand-gold, #c9a253)',
                                            fontWeight: 600,
                                        }}
                                    >
                                        {mult}
                                    </td>

                                    {/* Latency — not available from API; show dash */}
                                    <td
                                        style={{
                                            padding: '14px 18px',
                                            fontFamily: 'var(--font-mono, ui-monospace)',
                                            color: 'hsl(var(--foreground))',
                                        }}
                                    >
                                        —
                                    </td>

                                    {/* Load */}
                                    <td style={{ padding: '14px 18px', minWidth: 140 }}>
                                        <LoadBar pct={0} tone={tone} />
                                    </td>

                                    {/* Actions */}
                                    <td
                                        style={{
                                            padding: '14px 18px',
                                            textAlign: 'right',
                                        }}
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <button
                                            type="button"
                                            style={iconBtnStyle}
                                            title={t('edit', 'Edit')}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onEdit(node);
                                            }}
                                        >
                                            <NilouIcon name="settings" size={15} />
                                        </button>
                                        <button
                                            type="button"
                                            style={iconBtnStyle}
                                            title={t('delete', 'Delete')}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onDelete(node);
                                            }}
                                        >
                                            <NilouIcon name="copy" size={15} />
                                        </button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </NilouCard>

            {/* Existing outlet for nodeId sub-routes (dialogs + log viewer) */}
            <Suspense fallback={<Loading />}>
                <Outlet />
            </Suspense>
        </div>
    );
};

export const Route = createLazyFileRoute('/_dashboard/nodes')({
    component: () => (
        <SudoRoute>
            <NodesPage />
        </SudoRoute>
    ),
});
