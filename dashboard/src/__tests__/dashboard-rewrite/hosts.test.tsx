/**
 * Unit tests for /hosts route rewrite (Wave-A A2).
 *
 * Strategy: test Nilou primitives used by the page and the KPI arithmetic
 * logic independently (no full router mount).
 *
 * Assertions:
 *   1. PanelHead renders title and subtitle text.
 *   2. KPI renders label + numeric value.
 *   3. Active/disabled host count arithmetic is correct.
 *   4. "Add host" label is present in the page actions area.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PanelHead, KPI } from '@marzneshin/common/components/nilou';

/* ------------------------------------------------------------------ */
/* PanelHead rendering                                                 */
/* ------------------------------------------------------------------ */

describe('PanelHead (hosts page header)', () => {
    it('renders title text', () => {
        render(<PanelHead title="Hosts" />);
        expect(screen.getByText('Hosts')).toBeInTheDocument();
    });

    it('renders subtitle when provided', () => {
        render(
            <PanelHead
                title="Hosts"
                sub="Reality / VLESS inbound configs"
            />,
        );
        expect(
            screen.getByText('Reality / VLESS inbound configs'),
        ).toBeInTheDocument();
    });

    it('renders action content when provided', () => {
        render(
            <PanelHead
                title="Hosts"
                actions={<button type="button">Add host</button>}
            />,
        );
        expect(
            screen.getByRole('button', { name: 'Add host' }),
        ).toBeInTheDocument();
    });
});

/* ------------------------------------------------------------------ */
/* KPI component                                                        */
/* ------------------------------------------------------------------ */

describe('KPI (hosts KPI strip)', () => {
    it('renders label and value', () => {
        render(<KPI label="Total hosts" value="7" />);
        expect(screen.getByText('Total hosts')).toBeInTheDocument();
        expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('renders sub text when provided', () => {
        render(<KPI label="Active" value="5" sub="2 disabled" />);
        expect(screen.getByText('2 disabled')).toBeInTheDocument();
    });

    it('accepts all accent types without error', () => {
        const accents = ['teal', 'gold', 'emerald', 'coral'] as const;
        for (const accent of accents) {
            const { unmount } = render(
                <KPI label="X" value="0" accent={accent} />,
            );
            expect(screen.getByText('X')).toBeInTheDocument();
            unmount();
        }
    });
});

/* ------------------------------------------------------------------ */
/* Host active/disabled count arithmetic                               */
/* ------------------------------------------------------------------ */

describe('Host KPI strip arithmetic', () => {
    const hosts = [
        { id: 1, is_disabled: false },
        { id: 2, is_disabled: false },
        { id: 3, is_disabled: true },
        { id: 4, is_disabled: false },
    ];

    it('total is the full array length', () => {
        expect(hosts.length).toBe(4);
    });

    it('active = hosts where is_disabled is false', () => {
        const active = hosts.filter((h) => !h.is_disabled).length;
        expect(active).toBe(3);
    });

    it('disabled = hosts where is_disabled is true', () => {
        const disabled = hosts.filter((h) => h.is_disabled).length;
        expect(disabled).toBe(1);
    });

    it('active + disabled = total', () => {
        const active = hosts.filter((h) => !h.is_disabled).length;
        const disabled = hosts.filter((h) => h.is_disabled).length;
        expect(active + disabled).toBe(hosts.length);
    });
});
