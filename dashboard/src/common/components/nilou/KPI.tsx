/**
 * KPI — eyebrow label + display number + sub + optional sparkline.
 * Ported from design PanelPages1.jsx.
 *
 * Operator scope examples:
 *   <KPI label="Total users" value="142" sub="↑ 8 this week" sparkData={[120,124,128,132,136,140,142]} />
 *   <KPI label="Avg health" value="92" sub="↓ 2 this week" accent="emerald" />
 */
import type { FC, ReactNode } from 'react';
import { Card } from './Card';
import { Sparkline } from './Sparkline';

export type KPIAccent = 'teal' | 'gold' | 'emerald' | 'coral';

export interface KPIProps {
    label: ReactNode;
    value: ReactNode;
    sub?: ReactNode;
    trend?: 'up' | 'down';
    sparkData?: number[];
    accent?: KPIAccent;
}

const COLORS: Record<KPIAccent, string> = {
    teal: 'hsl(var(--primary))',
    gold: 'hsl(var(--accent))',
    emerald: '#5bc0be',
    coral: '#e07856',
};

export const KPI: FC<KPIProps> = ({ label, value, sub, trend, sparkData, accent = 'teal' }) => (
    <Card pad={20}>
        <div
            style={{
                fontSize: '0.74rem',
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
                color: 'hsl(var(--muted-foreground))',
                fontWeight: 600,
            }}
        >
            {label}
        </div>
        <div
            style={{
                fontFamily: "'Cormorant Garamond', Georgia, serif",
                fontSize: '2rem',
                fontWeight: 500,
                color: 'hsl(var(--foreground))',
                marginTop: 4,
                lineHeight: 1.05,
            }}
        >
            {value}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
            <span
                style={{
                    fontSize: '0.84rem',
                    color: trend === 'down' ? '#e07856' : 'hsl(var(--primary))',
                }}
            >
                {sub}
            </span>
        </div>
        {sparkData && (
            <div style={{ marginTop: 10 }}>
                <Sparkline data={sparkData} color={COLORS[accent]} />
            </div>
        )}
    </Card>
);
