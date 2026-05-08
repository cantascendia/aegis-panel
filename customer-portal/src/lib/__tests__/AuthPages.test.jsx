/**
 * Tests for the customer-portal LoginPage flow.
 *
 * §32.1 forbidden path — these tests guard the auth contract against
 * silent regression. Specifically:
 * - Short / empty subscription URL is blocked client-side (no fetch fired)
 * - Successful login stores the JWT then navigates to /panel
 * - Failed login (400 / 401 / network) shows inline error and clears
 *   the input so the next attempt requires fresh paste (security:
 *   reduces shoulder-surfing of bad URL)
 *
 * We don't test SignupPage — it's still P1 mock (§D-018 sequence puts
 * customer signup behind admin-creates-user invariant).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';

import { Router } from '../Atoms.jsx';
import { LoginPage } from '../AuthPages.jsx';
import { clearToken, getToken } from '../customer-auth.js';

function res({ ok = true, status = 200, body = {}, statusText = 'OK' } = {}) {
    return {
        ok,
        status,
        statusText,
        json: async () => body,
    };
}

function renderLogin() {
    return render(
        <Router>
            <LoginPage />
        </Router>,
    );
}

beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
    // Reset hash so Router starts at '/' regardless of test order.
    window.location.hash = '';
});

afterEach(() => {
    vi.restoreAllMocks();
    clearToken();
});

// ---------------------------------------------------------------------------
// Visual sanity
// ---------------------------------------------------------------------------

describe('LoginPage layout', () => {
    it('renders Cormorant title and subscription URL textarea', () => {
        renderLogin();
        // Cormorant title is split across two spans ("Welcome back," + "lotus.")
        expect(screen.getByText(/Welcome back/i)).toBeInTheDocument();
        expect(screen.getByText(/lotus\./i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/nilou\.network\/sub/i)).toBeInTheDocument();
    });

    it('renders the Sign in submit button', () => {
        renderLogin();
        expect(
            screen.getByRole('button', { name: /sign in/i }),
        ).toBeInTheDocument();
    });
});

// ---------------------------------------------------------------------------
// Submission flow
// ---------------------------------------------------------------------------

describe('LoginPage submit flow', () => {
    it('rejects short subscription URL client-side (no fetch fires)', async () => {
        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        const button = screen.getByRole('button', { name: /sign in/i });

        // Avoid the browser-native required-field popup by providing a non-empty
        // but too-short value. The component checks `length < 9`.
        fireEvent.change(textarea, { target: { value: 'short' } });
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent(
                /please enter your subscription url/i,
            );
        });
        expect(globalThis.fetch).not.toHaveBeenCalled();
    });

    it('on success: stores token + navigates to /panel', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({
                body: {
                    access_token: 'header.payload.signature',
                    token_type: 'bearer',
                    user_id: 42,
                    username: 'cust_alice',
                    expires_in_seconds: 900,
                },
            }),
        );

        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        const button = screen.getByRole('button', { name: /sign in/i });

        fireEvent.change(textarea, {
            target: { value: 'https://nilou.cc/sub/cust_alice/abc123' },
        });
        fireEvent.click(button);

        await waitFor(() => {
            expect(getToken()).toBe('header.payload.signature');
        });
        expect(window.location.hash).toBe('#/panel');
    });

    it('on 401: clears the input and shows backend detail', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({
                ok: false,
                status: 401,
                body: { detail: 'Invalid subscription URL' },
            }),
        );

        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        const button = screen.getByRole('button', { name: /sign in/i });

        fireEvent.change(textarea, {
            target: { value: 'https://nilou.cc/sub/wrong/key' },
        });
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent(
                /invalid subscription url/i,
            );
        });
        expect(textarea.value).toBe('');
        expect(getToken()).toBeNull();
    });

    it('on 400 (malformed): shows backend detail without storing token', async () => {
        globalThis.fetch.mockResolvedValueOnce(
            res({
                ok: false,
                status: 400,
                body: { detail: 'Subscription URL is malformed' },
            }),
        );

        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        const button = screen.getByRole('button', { name: /sign in/i });

        fireEvent.change(textarea, {
            target: { value: 'https://example.com/junk/path' },
        });
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toHaveTextContent(
                /subscription url is malformed/i,
            );
        });
        expect(getToken()).toBeNull();
    });

    it('shows generic message when fetch throws (offline)', async () => {
        globalThis.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        const button = screen.getByRole('button', { name: /sign in/i });

        fireEvent.change(textarea, {
            target: { value: 'https://nilou.cc/sub/cust_alice/abc123' },
        });
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByRole('alert')).toBeInTheDocument();
        });
        expect(getToken()).toBeNull();
    });

    it('button shows loading state during pending request', async () => {
        // Stall fetch so we can observe the loading state.
        let resolveFetch;
        globalThis.fetch.mockReturnValueOnce(
            new Promise((resolve) => {
                resolveFetch = () =>
                    resolve(
                        res({
                            body: {
                                access_token: 'a.b.c',
                                user_id: 1,
                                username: 'x',
                                expires_in_seconds: 900,
                            },
                        }),
                    );
            }),
        );

        renderLogin();
        const textarea = screen.getByPlaceholderText(/nilou\.network\/sub/i);
        fireEvent.change(textarea, {
            target: { value: 'https://nilou.cc/sub/cust_alice/abc123' },
        });
        fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

        // Btn is a custom inline-style button — it doesn't forward disabled
        // to the DOM. Loading state is signalled by the label text changing.
        await waitFor(() => {
            expect(
                screen.getByRole('button', { name: /signing in/i }),
            ).toBeInTheDocument();
        });
        // Textarea is also disabled while loading (verifies loading prop wired).
        expect(textarea).toBeDisabled();

        // Cleanup: let the promise resolve so the test doesn't leak.
        resolveFetch();
    });
});
