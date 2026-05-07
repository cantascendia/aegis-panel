/**
 * Row — flex row with muted label on left, mono value on right.
 * Ported from design PanelPages1.jsx for "stat list" layouts.
 */
import type { FC, ReactNode } from 'react';

export interface RowProps {
    a: ReactNode;
    b: ReactNode;
}

export const Row: FC<RowProps> = ({ a, b }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.86rem' }}>
        <span style={{ color: 'hsl(var(--muted-foreground))' }}>{a}</span>
        <span style={{ color: 'hsl(var(--foreground))', fontWeight: 600, fontFamily: "'JetBrains Mono', ui-monospace, monospace" }}>
            {b}
        </span>
    </div>
);
