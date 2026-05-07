/**
 * Card + CardHeader — Nilou cream surface, hairline border, modest radius.
 *
 * Ported from design PanelShell.jsx. Naming intentionally collides
 * with shadcn Card so consumers import from this barrel get the Nilou
 * version. shadcn's original Card stays in `dashboard/src/common/components/ui/card.tsx`
 * for places that want it (legacy).
 */
import type { CSSProperties, FC, ReactNode } from 'react';

export interface CardProps {
    children: ReactNode;
    pad?: number;
    style?: CSSProperties;
}

export const Card: FC<CardProps> = ({ children, pad = 22, style = {} }) => (
    <div
        style={{
            background: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border) / 0.6)',
            borderRadius: 10,
            padding: pad,
            ...style,
        }}
    >
        {children}
    </div>
);

export interface CardHeaderProps {
    title: ReactNode;
    sub?: ReactNode;
    action?: ReactNode;
}

export const CardHeader: FC<CardHeaderProps> = ({ title, sub, action }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
            <h3 style={{ margin: 0, color: 'hsl(var(--foreground))', fontWeight: 600, fontSize: '1rem' }}>{title}</h3>
            {sub && <div style={{ marginTop: 2, color: 'hsl(var(--muted-foreground))', fontSize: '0.84rem' }}>{sub}</div>}
        </div>
        {action}
    </div>
);
