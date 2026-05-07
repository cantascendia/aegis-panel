/**
 * Eyebrow — small uppercased section label above headings.
 * Ported from design Atoms.jsx.
 */
import type { FC, ReactNode } from 'react';

export interface EyebrowProps {
    children: ReactNode;
    color?: string;
}

export const Eyebrow: FC<EyebrowProps> = ({ children, color = '#c9a253' }) => (
    <p
        style={{
            display: 'inline-block',
            fontSize: '0.78rem',
            fontWeight: 600,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color,
            margin: '0 0 24px',
            padding: '6px 14px',
            background: 'rgba(201,162,83,0.1)',
            borderRadius: 999,
        }}
    >
        {children}
    </p>
);
