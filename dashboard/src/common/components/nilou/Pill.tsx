/**
 * Pill — small uppercased rounded label for plan tier / multiplier / status tags.
 * Ported from design Atoms.jsx.
 */
import type { FC, ReactNode } from 'react';

export type PillTone = 'teal' | 'gold' | 'emerald' | 'amber' | 'coral' | 'navy';

export interface PillProps {
    tone?: PillTone;
    children: ReactNode;
}

const TONES: Record<PillTone, { bg: string; fg: string }> = {
    teal: { bg: 'rgba(58,145,136,0.12)', fg: '#1d5e58' },
    gold: { bg: 'rgba(201,162,83,0.16)', fg: '#8a6a2d' },
    emerald: { bg: 'rgba(91,192,190,0.16)', fg: '#1b6f6c' },
    amber: { bg: 'rgba(232,176,75,0.18)', fg: '#9a6f1f' },
    coral: { bg: 'rgba(224,120,86,0.16)', fg: '#a04a2c' },
    navy: { bg: 'rgba(30,58,95,0.10)', fg: '#1e3a5f' },
};

export const Pill: FC<PillProps> = ({ tone = 'teal', children }) => {
    const t = TONES[tone];
    return (
        <span
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                background: t.bg,
                color: t.fg,
                fontSize: '0.74rem',
                fontWeight: 600,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                padding: '4px 10px',
                borderRadius: 999,
                whiteSpace: 'nowrap',
            }}
        >
            {children}
        </span>
    );
};
