/**
 * LotusMark — Nilou Network primary brand glyph (8-petal lotus).
 *
 * Ported from `docs/design-system-source/project/site/lib/Atoms.jsx`
 * verbatim. `currentColor` so a single `color:` rule themes it.
 *
 * `breathe` adds 7s subtle scale + 3deg rotate animation (the
 * `lotus-breathe` keyframes ship in nilou-theme.css / globals.css).
 */
import type { FC } from 'react';

export interface LotusMarkProps {
    size?: number;
    color?: string;
    breathe?: boolean;
}

export const LotusMark: FC<LotusMarkProps> = ({ size = 48, color = 'hsl(var(--primary))', breathe = false }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 200 200"
        aria-hidden="true"
        style={{ color, animation: breathe ? 'lotus-breathe 7s ease-in-out infinite' : 'none' }}
    >
        <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <g strokeOpacity="0.92">
                {[0, 45, 90, 135, 180, 225, 270, 315].map((r) => (
                    <path
                        key={r}
                        d="M100 20 C 130 50, 130 90, 100 100 C 70 90, 70 50, 100 20 Z"
                        transform={`rotate(${r} 100 100)`}
                    />
                ))}
            </g>
            <circle cx="100" cy="100" r="6" />
            <circle cx="100" cy="100" r="2.5" fill="currentColor" />
        </g>
    </svg>
);
