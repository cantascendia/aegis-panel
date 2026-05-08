/**
 * Tests for customer-portal API client.
 *
 * Module under test: src/lib/customer-api.js
 *
 * Strategy: stub global `fetch` per test (vitest.fn) so the whole
 * Response shape is under our control. We don't hit the network.
 *
 * Coverage axes:
 * - subLogin success → returns parsed body
 * - subLogin 400 / 401 → throws CustomerApiError with status + detail
 * - getMe attaches Authorization: Bearer header iff token exists
 * - getMe 401 → throws CustomerApiError
 * - graceful-404 helpers (getMyTraffic / getMyInvoices / getAvailablePlans)
 *   return { _placeholder: true, _reason: 'endpoint-missing', ... }
 * - graceful-404 on network failure → { _placeholder: true, _reason: 'network', ... }
 *
 * Forbidden-path gate: AuthPages.jsx depends on subLogin's error contract.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    CustomerApiError,
    getAvailablePlans,
    getMe,
    getMyInvoices,
    getMyTraffic,
    subLogin,
} from '../customer-api.js';
import { setToken } from '../customer-auth.js';

/** Build a minimal Response-like object for fetch stubs. */
function res({ ok = true, status = 200, body = {}, statusText = 'OK' } = {}) {
    return {
        ok,
        status,
        statusText,
        json: async () => body,
    };
}

beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
});

afterEach(() => {
    vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// subLogin
// ---------------------------------------------------------------------------

describe('subLogin', () => {
    it('POSTs to /api/customers/sub-login with sub_url body', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({
                body: {
                    access_token: 'a.b.c',
                    token_type: 'bearer',
                    user_id: 42,
                    username: 'cust_alice',
                    expires_in_seconds: 900,
                },
            }),
        );

        const result = await subLogin('https://nilou.cc/sub/cust_alice/abc123');

        expect(globalThis.fetch).toHaveBeenCalledWith(
            '/api/customers/sub-login',
            expect.objectContaining({
                method: 'POST',
                headers: expect.objectContaining({
                    'Content-Type': 'application/json',
                }),
                body: JSON.stringify({
                    sub_url: 'https://nilou.cc/sub/cust_alice/abc123',
                }),
            }),
        );
        expect(result.access_token).toBe('a.b.c');
        expect(result.user_id).toBe(42);
    });

    it('throws CustomerApiError with status 400 on malformed URL', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 400, body: { detail: 'Subscription URL is malformed' } }),
        );

        // Single call — assert the error matches both the type and the shape.
        let caught;
        try {
            await subLogin('garbage');
        } catch (e) {
            caught = e;
        }
        expect(caught).toBeInstanceOf(CustomerApiError);
        expect(caught).toMatchObject({
            status: 400,
            detail: 'Subscription URL is malformed',
        });
    });

    it('throws CustomerApiError with status 401 on invalid credential', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 401, body: { detail: 'Invalid subscription URL' } }),
        );

        await expect(
            subLogin('https://nilou.cc/sub/wrong/key'),
        ).rejects.toMatchObject({
            status: 401,
            detail: 'Invalid subscription URL',
        });
    });

    it('falls back to statusText if body has no detail', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 500, statusText: 'Server Error', body: {} }),
        );

        await expect(subLogin('x')).rejects.toMatchObject({
            status: 500,
            detail: 'Server Error',
        });
    });
});

// ---------------------------------------------------------------------------
// getMe
// ---------------------------------------------------------------------------

describe('getMe', () => {
    it('attaches Bearer header when token present', async () => {
        setToken('header.payload.sig');
        globalThis.fetch.mockResolvedValueOnce(
            res({ body: { user_id: 42, username: 'cust', used_traffic: 0, data_limit: null, is_active: true } }),
        );

        await getMe();

        const call = globalThis.fetch.mock.calls[0];
        expect(call[0]).toBe('/api/customers/me');
        expect(call[1].headers.Authorization).toBe('Bearer header.payload.sig');
    });

    it('omits Authorization header when no token', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ body: { user_id: 1 } }),
        );

        await getMe();

        const headers = globalThis.fetch.mock.calls[0][1].headers;
        expect(headers.Authorization).toBeUndefined();
    });

    it('throws CustomerApiError 401 when token is invalid/expired', async () => {
        setToken('expired.token.sig');
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 401, body: { detail: 'Invalid or expired customer token' } }),
        );

        await expect(getMe()).rejects.toMatchObject({
            status: 401,
            detail: 'Invalid or expired customer token',
        });
    });
});

// ---------------------------------------------------------------------------
// graceful-404 helpers
// ---------------------------------------------------------------------------

describe('graceful-404 helpers', () => {
    it('getMyTraffic returns placeholder on 404', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 404, statusText: 'Not Found' }),
        );

        const result = await getMyTraffic(14);

        expect(result._placeholder).toBe(true);
        expect(result._reason).toBe('endpoint-missing');
        expect(result.daily).toEqual([]);
        expect(result.total_bytes).toBe(0);
    });

    it('getMyTraffic encodes days param', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ body: { daily: [{ date: '2026-05-07', used_bytes: 1024 }], total_bytes: 1024 } }),
        );

        await getMyTraffic(30);

        expect(globalThis.fetch.mock.calls[0][0]).toBe('/api/customers/me/traffic?days=30');
    });

    it('getMyInvoices returns placeholder on 404', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 404 }),
        );

        const result = await getMyInvoices();

        expect(result._placeholder).toBe(true);
        expect(result._reason).toBe('endpoint-missing');
        expect(result.invoices).toEqual([]);
    });

    it('getAvailablePlans returns placeholder on 404', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 404 }),
        );

        const result = await getAvailablePlans();

        expect(result._placeholder).toBe(true);
        expect(result._reason).toBe('endpoint-missing');
        expect(result.plans).toEqual([]);
    });

    it('graceful-404 returns network placeholder on fetch throw', async () => {
        globalThis.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

        const result = await getMyTraffic();

        expect(result._placeholder).toBe(true);
        expect(result._reason).toBe('network');
    });

    it('graceful-404 still throws CustomerApiError on 500', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({ ok: false, status: 500, body: { detail: 'Internal Server Error' } }),
        );

        await expect(getMyTraffic()).rejects.toMatchObject({
            status: 500,
            detail: 'Internal Server Error',
        });
    });
});

// ---------------------------------------------------------------------------
// CustomerApiError shape
// ---------------------------------------------------------------------------

describe('CustomerApiError', () => {
    it('subclasses Error with status + detail fields', () => {
        const e = new CustomerApiError(401, 'Bad token');
        expect(e).toBeInstanceOf(Error);
        expect(e.name).toBe('CustomerApiError');
        expect(e.status).toBe(401);
        expect(e.detail).toBe('Bad token');
        expect(e.message).toBe('Bad token');
    });
});
