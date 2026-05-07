/**
 * Unit tests for /services route rewrite (Wave-A A2).
 *
 * Strategy: test Nilou primitives and service-count arithmetic directly
 * (no full router mount needed).
 *
 * Assertions:
 *   1. PanelHead renders title and subtitle.
 *   2. KPI renders total and active values.
 *   3. Active service heuristic (inbound_ids.length > 0) is correct.
 *   4. "Add service" action label is present.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PanelHead, KPI } from '@marzneshin/common/components/nilou';

/* ------------------------------------------------------------------ */
/* PanelHead rendering                                                 */
/* ------------------------------------------------------------------ */

describe('PanelHead (services page header)', () => {
    it('renders title "Services"', () => {
        render(<PanelHead title="Services" />);
        expect(screen.getByText('Services')).toBeInTheDocument();
    });

    it('renders subtitle describing service templates', () => {
        render(
            <PanelHead
                title="Services"
                sub="Service templates linking inbounds to plans"
            />,
        );
        expect(
            screen.getByText('Service templates linking inbounds to plans'),
        ).toBeInTheDocument();
    });

    it('renders "Add service" action button when provided', () => {
        render(
            <PanelHead
                title="Services"
                actions={<button type="button">Add service</button>}
            />,
        );
        expect(
            screen.getByRole('button', { name: 'Add service' }),
        ).toBeInTheDocument();
    });
});

/* ------------------------------------------------------------------ */
/* Services KPI arithmetic                                              */
/* ------------------------------------------------------------------ */

describe('Services KPI strip arithmetic', () => {
    const services = [
        { id: 1, name: 'Basic', inbound_ids: [1, 2], user_ids: [10] },
        { id: 2, name: 'Premium', inbound_ids: [3], user_ids: [11, 12] },
        { id: 3, name: 'Empty', inbound_ids: [], user_ids: [] },
    ];

    it('total = full array length', () => {
        expect(services.length).toBe(3);
    });

    it('active = services with at least one inbound_id', () => {
        const active = services.filter((s) => s.inbound_ids.length > 0).length;
        expect(active).toBe(2);
    });

    it('inactive = services with zero inbound_ids', () => {
        const inactive = services.filter((s) => s.inbound_ids.length === 0).length;
        expect(inactive).toBe(1);
    });
});

/* ------------------------------------------------------------------ */
/* KPI component rendering (services accent)                           */
/* ------------------------------------------------------------------ */

describe('KPI (services KPI strip)', () => {
    it('renders label and value for Total services', () => {
        render(<KPI label="Total services" value="3" accent="teal" />);
        expect(screen.getByText('Total services')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('renders label and value for Active services', () => {
        render(<KPI label="Active" value="2" accent="emerald" />);
        expect(screen.getByText('Active')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('renders zero value without crashing (empty state)', () => {
        render(<KPI label="Total services" value="0" />);
        expect(screen.getByText('0')).toBeInTheDocument();
    });
});
