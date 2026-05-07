/**
 * BigChart — 2-series area+line chart for daily totals (e.g. download
 * + upload over 14 days). Ported from design PanelPages1.jsx but
 * accepts data via props instead of hardcoded values.
 */
import type { FC } from 'react';

export interface BigChartProps {
    /** Primary series (filled area). e.g. download GB per day. */
    primary: number[];
    /** Optional secondary series (dashed line). e.g. upload. */
    secondary?: number[];
    /** Color for primary series. Default Nilou teal. */
    primaryColor?: string;
    /** Color for secondary series. Default Nilou gold. */
    secondaryColor?: string;
}

export const BigChart: FC<BigChartProps> = ({
    primary,
    secondary,
    primaryColor = '#3a9188',
    secondaryColor = '#c9a253',
}) => {
    if (!primary || primary.length === 0) return null;

    const max = Math.max(...primary, ...(secondary ?? [0])) * 1.15 || 1;
    const w = 100;
    const h = 100;
    const x = (i: number) => (i / (primary.length - 1 || 1)) * w;
    const y = (v: number) => h - (v / max) * h;

    const path = primary.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ');
    const fill = `M 0 ${h} ${primary.map((v, i) => `L ${x(i)} ${y(v)}`).join(' ')} L ${w} ${h} Z`;
    const upath = secondary
        ? secondary.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ')
        : null;

    return (
        <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="100%" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
            <defs>
                <linearGradient id="dlg" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor={primaryColor} stopOpacity="0.32" />
                    <stop offset="100%" stopColor={primaryColor} stopOpacity="0" />
                </linearGradient>
            </defs>
            {[0, 25, 50, 75, 100].map((p) => (
                <line key={p} x1="0" x2={w} y1={(h * p) / 100} y2={(h * p) / 100} stroke="hsl(var(--border) / 0.6)" strokeWidth="0.3" />
            ))}
            <path d={fill} fill="url(#dlg)" />
            <path d={path} fill="none" stroke={primaryColor} strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
            {upath && (
                <path d={upath} fill="none" stroke={secondaryColor} strokeWidth="1.2" strokeDasharray="3 2" vectorEffect="non-scaling-stroke" />
            )}
        </svg>
    );
};
