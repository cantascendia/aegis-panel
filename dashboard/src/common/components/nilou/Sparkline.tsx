/**
 * Sparkline — small SVG line+fill micro-chart for KPI cards.
 * Ported from design PanelPages1.jsx.
 */
import type { FC } from 'react';

export interface SparklineProps {
    data: number[];
    color?: string;
    h?: number;
    fill?: boolean;
}

export const Sparkline: FC<SparklineProps> = ({ data, color = 'hsl(var(--primary))', h = 36, fill = true }) => {
    if (!data || data.length === 0) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const w = 120;
    const pts = data
        .map((v, i) => `${(i / (data.length - 1 || 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`)
        .join(' ');
    return (
        <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" style={{ display: 'block' }}>
            {fill && <polygon points={`0,${h} ${pts} ${w},${h}`} fill={color} opacity="0.12" />}
            <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
};
