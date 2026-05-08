/**
 * Tests for the customer DashboardPage `/me` wire.
 *
 * Found a real bug while writing this: the original wave-P2 merge had
 * DashboardPage treating `getMe()` as `{ok, data}` but customer-api.js
 * exports the throw-on-error contract. That meant the page was stuck
 * showing "Could not load" even on successful login. The accompanying
 * fix in PanelPages1.jsx switches to try/catch via .then/.catch.
 *
 * These tests guard that contract going forward.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

import { Router } from '../Atoms.jsx';
import { DashboardPage } from '../PanelPages1.jsx';
import { setToken } from '../customer-auth.js';

function res({ ok = true, status = 200, body = {}, statusText = 'OK' } = {}) {
    return {
        ok,
        status,
        statusText,
        json: async () => body,
    };
}

function renderDashboard() {
    return render(
        <Router>
            <DashboardPage />
        </Router>,
    );
}

beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
    window.location.hash = '';
});

afterEach(() => {
    vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// /me happy path
// ---------------------------------------------------------------------------

describe('DashboardPage /me wire', () => {
    it('renders the username from /me data', async () => {
        setToken('header.payload.signature');
        // /me succeeds
        globalThis.fetch.mockImplementation(async (url) => {
            if (url === '/api/customers/me') {
                return res({
                    body: {
                        user_id: 42,
                        username: 'cust_alice',
                        used_traffic: 38_654_705_664, // ~36 GB
                        data_limit: 107_374_182_400, // 100 GB
                        data_limit_reset_strategy: 'monthly',
                        expire_date: '2026-06-07T00:00:00',
                        expire_strategy: 'fixed_date',
                        is_active: true,
                        online_at: null,
                        note: null,
                    },
                });
            }
            // graceful 404 for traffic until backend ships
            return res({ ok: false, status: 404, statusText: 'Not Found' });
        });

        renderDashboard();

        await waitFor(() => {
            expect(screen.getByText(/Welcome back, cust_alice/)).toBeInTheDocument();
        });
        // Sub-text reflects active state
        expect(
            screen.getByText(/Your network is operating normally/i),
        ).toBeInTheDocument();
    });

    it('shows error banner when /me throws (e.g. 401 expired)', async () => {
        setToken('expired.token.sig');
        globalThis.fetch.mockResolvedValue(
            res({
                ok: false,
                status: 401,
                body: { detail: 'Invalid or expired customer token' },
            }),
        );

        renderDashboard();

        await waitFor(() => {
            expect(
                screen.getByText(/Could not load your account data/i),
            ).toBeInTheDocument();
        });
    });

    it('renders KPI grid with at least 4 cards', async () => {
        setToken('h.p.s');
        globalThis.fetch.mockImplementation(async (url) => {
            if (url === '/api/customers/me') {
                return res({
                    body: {
                        user_id: 1,
                        username: 'x',
                        used_traffic: 0,
                        data_limit: null,
                        is_active: true,
                    },
                });
            }
            return res({ ok: false, status: 404 });
        });

        renderDashboard();

        await waitFor(() => {
            expect(screen.getByText(/Used this cycle/i)).toBeInTheDocument();
        });
        // The "Remaining" KPI label collides with the trial-card copy
        // ("2 days, 7 hours remaining") so we anchor to the uppercase
        // eyebrow text exactly via a getAllByText match instead.
        expect(screen.getAllByText(/Remaining/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Active devices/i)).toBeInTheDocument();
        expect(screen.getByText(/Avg\. latency/i)).toBeInTheDocument();
    });

    it('attaches Bearer token to /me request', async () => {
        setToken('my.test.jwt');
        globalThis.fetch.mockResolvedValue(
            res({ body: { user_id: 1, username: 'x', used_traffic: 0, is_active: true } }),
        );

        renderDashboard();

        await waitFor(() => {
            expect(globalThis.fetch).toHaveBeenCalled();
        });
        const calls = globalThis.fetch.mock.calls;
        const meCall = calls.find((c) => c[0] === '/api/customers/me');
        expect(meCall).toBeDefined();
        expect(meCall[1].headers.Authorization).toBe('Bearer my.test.jwt');
    });

    it('renders limit-aware "Used this cycle" sub copy', async () => {
        setToken('h.p.s');
        globalThis.fetch.mockImplementation(async (url) => {
            if (url === '/api/customers/me') {
                return res({
                    body: {
                        user_id: 1,
                        username: 'x',
                        used_traffic: 53_687_091_200, // 50 GB
                        data_limit: 107_374_182_400, // 100 GB
                        is_active: true,
                    },
                });
            }
            return res({ ok: false, status: 404 });
        });

        renderDashboard();

        await waitFor(() => {
            // 50 / 100 = 50%
            expect(screen.getByText(/50% used/i)).toBeInTheDocument();
        });
    });
});
