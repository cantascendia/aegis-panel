/**
 * PanelHead — page title + sub + actions.
 * Ported from design PanelShell.jsx.
 */
import type { FC, ReactNode } from 'react';

export interface PanelHeadProps {
    title: ReactNode;
    sub?: ReactNode;
    actions?: ReactNode;
}

export const PanelHead: FC<PanelHeadProps> = ({ title, sub, actions }) => (
    <div
        style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            gap: 16,
            marginBottom: 24,
            flexWrap: 'wrap',
        }}
    >
        <div>
            <h1
                style={{
                    margin: 0,
                    fontFamily: "'Cormorant Garamond', Georgia, serif",
                    fontWeight: 500,
                    fontSize: '1.9rem',
                    color: 'hsl(var(--foreground))',
                    letterSpacing: '-0.02em',
                }}
            >
                {title}
            </h1>
            {sub && (
                <p style={{ margin: '6px 0 0', color: 'hsl(var(--muted-foreground))', fontSize: '0.96rem' }}>{sub}</p>
            )}
        </div>
        {actions && <div style={{ display: 'flex', gap: 10 }}>{actions}</div>}
    </div>
);
