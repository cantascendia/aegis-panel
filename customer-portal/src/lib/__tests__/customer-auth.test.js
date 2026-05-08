/**
 * Tests for customer-portal token store + JWT-payload reader.
 *
 * Module under test: src/lib/customer-auth.js
 *
 * Coverage axes:
 * - localStorage round-trip (set/get/clear)
 * - localStorage unavailable (e.g. quota / SSR) — silent fail
 * - JWT payload decoding via atob() — happy path + boundary
 * - isTokenValid decisions on missing / malformed / expired / fresh tokens
 *
 * Security note (§32.1 forbidden path): the token store is the only
 * client-side state guarding /panel routes. These assertions exist so
 * any future refactor can't silently weaken `isTokenValid`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    clearToken,
    getToken,
    getTokenExpiry,
    isTokenValid,
    setToken,
} from '../customer-auth.js';

/** Build a synthetic JWT (no signature — we never verify in JS). */
function makeJwt(payload) {
    const b64 = (obj) =>
        btoa(JSON.stringify(obj))
            .replace(/=+$/, '')
            .replace(/\+/g, '-')
            .replace(/\//g, '_');
    const header = b64({ alg: 'HS256', typ: 'JWT' });
    const body = b64(payload);
    // Signature is unused by the client — any string works.
    return `${header}.${body}.signature`;
}

beforeEach(() => {
    localStorage.clear();
});

afterEach(() => {
    vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// getToken / setToken / clearToken — localStorage round-trip
// ---------------------------------------------------------------------------

describe('token store', () => {
    it('getToken returns null when nothing stored', () => {
        expect(getToken()).toBeNull();
    });

    it('setToken + getToken round trip', () => {
        setToken('abc.def.ghi');
        expect(getToken()).toBe('abc.def.ghi');
    });

    it('clearToken removes the token', () => {
        setToken('abc.def.ghi');
        clearToken();
        expect(getToken()).toBeNull();
    });

    it('getToken does not throw if localStorage throws (private mode)', () => {
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
            throw new Error('SecurityError');
        });
        expect(() => getToken()).not.toThrow();
        expect(getToken()).toBeNull();
    });

    it('setToken does not throw if localStorage throws (quota)', () => {
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('QuotaExceededError');
        });
        expect(() => setToken('x.y.z')).not.toThrow();
    });

    it('clearToken does not throw if localStorage throws', () => {
        vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
            throw new Error('SecurityError');
        });
        expect(() => clearToken()).not.toThrow();
    });
});

// ---------------------------------------------------------------------------
// getTokenExpiry — decoding correctness
// ---------------------------------------------------------------------------

describe('getTokenExpiry', () => {
    it('returns null when no token stored', () => {
        expect(getTokenExpiry()).toBeNull();
    });

    it('returns null for token without 3 dot-separated parts', () => {
        setToken('not-a-jwt');
        expect(getTokenExpiry()).toBeNull();
    });

    it('returns null for token with non-base64 payload', () => {
        setToken('header.@@invalid@@.sig');
        expect(getTokenExpiry()).toBeNull();
    });

    it('returns null for token whose payload has no exp claim', () => {
        setToken(makeJwt({ sub: '42', access: 'customer' }));
        expect(getTokenExpiry()).toBeNull();
    });

    it('returns null for token whose exp is not a number', () => {
        setToken(makeJwt({ sub: '42', exp: 'tomorrow' }));
        expect(getTokenExpiry()).toBeNull();
    });

    it('decodes exp as ms timestamp (seconds → ms)', () => {
        const expSeconds = Math.floor(Date.now() / 1000) + 900; // +15 min
        setToken(makeJwt({ sub: '42', access: 'customer', exp: expSeconds }));
        const result = getTokenExpiry();
        expect(result).toBe(expSeconds * 1000);
    });

    it('handles base64url variants (- and _)', () => {
        // Force a payload that contains chars b64-encoded as `-` and `_`.
        // Using objects with surrogate pairs / special chars in keys / values:
        const payload = { sub: '255~', access: 'customer', exp: 9999999999 };
        const token = makeJwt(payload);
        // sanity: the encoded body should contain `-` or `_`
        const body = token.split('.')[1];
        expect(body).toMatch(/[-_]/);
        setToken(token);
        expect(getTokenExpiry()).toBe(9999999999 * 1000);
    });
});

// ---------------------------------------------------------------------------
// isTokenValid — gate decisions
// ---------------------------------------------------------------------------

describe('isTokenValid', () => {
    it('returns false when no token', () => {
        expect(isTokenValid()).toBe(false);
    });

    it('returns false when token has no exp', () => {
        setToken(makeJwt({ sub: '42' }));
        expect(isTokenValid()).toBe(false);
    });

    it('returns false when exp is in the past', () => {
        const past = Math.floor(Date.now() / 1000) - 60;
        setToken(makeJwt({ sub: '42', exp: past }));
        expect(isTokenValid()).toBe(false);
    });

    it('returns true when exp is in the future', () => {
        const future = Math.floor(Date.now() / 1000) + 900;
        setToken(makeJwt({ sub: '42', exp: future }));
        expect(isTokenValid()).toBe(true);
    });

    it('returns false when exp equals now (boundary)', () => {
        // Round down to seconds and freeze "now" in ms.
        const nowMs = Date.now();
        const exp = Math.floor(nowMs / 1000);
        setToken(makeJwt({ sub: '42', exp }));
        // exp * 1000 <= Date.now() → false (strict greater-than in module).
        expect(isTokenValid()).toBe(false);
    });
});
