/**
 * StatusDot — small tinted dot for status indication.
 * Ported from design Atoms.jsx. `tone` selects color + glow.
 */
import type { FC } from 'react';

export type StatusTone = 'emerald' | 'amber' | 'coral' | 'muted' | 'teal' | 'navy' | 'gold';

export interface StatusDotProps {
    tone?: StatusTone;
    size?: number;
}

const COLORS: Record<StatusTone, string> = {
    emerald: '#5bc0be',
    amber: '#e8b04b',
    coral: '#e07856',
    muted: '#8a96b0',
    teal: 'var(--brand-teal, #3a9188)',
    navy: 'var(--brand-navy, #1e3a5f)',
    gold: '#c9a253',
};

export const StatusDot: FC<StatusDotProps> = ({ tone = 'emerald', size = 8 }) => {
    const c = COLORS[tone];
    return (
        <span
            style={{
                width: size,
                height: size,
                borderRadius: '50%',
                background: c,
                boxShadow: tone === 'emerald' ? `0 0 0 3px ${c}26` : 'none',
                display: 'inline-block',
                flexShrink: 0,
            }}
        />
    );
};
