/**
 * RingMeter — circular progress indicator with center label.
 * Ported from design PanelPages1.jsx.
 */
import type { FC, ReactNode } from 'react';

export interface RingMeterProps {
    percent: number;
    label: ReactNode;
    sub?: ReactNode;
    size?: number;
}

export const RingMeter: FC<RingMeterProps> = ({ percent, label, sub, size = 160 }) => {
    const r = (size / 160) * 56;
    const c = 2 * Math.PI * r;
    const cx = size / 2;
    const cy = size / 2;
    return (
        <div style={{ position: 'relative', display: 'grid', placeItems: 'center', padding: '12px 0' }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
                <circle cx={cx} cy={cy} r={r} fill="none" stroke="hsl(var(--border) / 0.6)" strokeWidth="10" />
                <circle
                    cx={cx}
                    cy={cy}
                    r={r}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={c}
                    strokeDashoffset={c * (1 - Math.min(Math.max(percent, 0), 100) / 100)}
                />
            </svg>
            <div style={{ position: 'absolute', textAlign: 'center' }}>
                <div
                    style={{
                        fontFamily: "'Cormorant Garamond', Georgia, serif",
                        fontSize: '1.6rem',
                        fontWeight: 500,
                        color: 'hsl(var(--foreground))',
                        lineHeight: 1,
                    }}
                >
                    {label}
                </div>
                {sub && (
                    <div style={{ fontSize: '0.82rem', color: 'hsl(var(--muted-foreground))', marginTop: 4 }}>{sub}</div>
                )}
            </div>
        </div>
    );
};
