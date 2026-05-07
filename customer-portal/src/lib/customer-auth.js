/**
 * Customer portal token store.
 *
 * Manages the short-lived 15-min JWT issued by POST /api/customers/sub-login.
 * No signature verification is done here — that is strictly a server-side
 * concern. We only parse the payload base64 to read the `exp` claim so we
 * can show the re-login prompt before the server rejects us.
 *
 * Security notes:
 * - Token lives in localStorage. Acceptable for the portal MVP (same-origin
 *   SPA, no cross-origin access, no sensitive PII beyond username).
 * - If the portal ever handles billing/payment keys, move to HttpOnly cookie.
 * - The 15-min expiry means a leaked token is self-expiring.
 *
 * Forbidden-path gate: this module is depended on by AuthPages.jsx which is
 * a §32.1 forbidden path. Any change to the token contract must go through
 * double-sign + codex cross-review.
 */

const STORAGE_KEY = 'customer_token';

/** @returns {string|null} Raw JWT string or null */
export function getToken() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/** @param {string} token - Raw JWT string */
export function setToken(token) {
  try {
    localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // localStorage unavailable (private browsing quota, SSR, etc.) — silent fail.
  }
}

/** Remove the stored token (logout). */
export function clearToken() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // silent fail
  }
}

/**
 * Decode JWT payload (no signature check) and return the `exp` claim as a
 * millisecond timestamp, or null if the token is missing / malformed.
 *
 * @returns {number|null} ms timestamp of expiry, or null
 */
export function getTokenExpiry() {
  const token = getToken();
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    // Base64url → Base64 → JSON
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    // Pad to multiple of 4
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
    const json = atob(padded);
    const payload = JSON.parse(json);
    if (typeof payload.exp !== 'number') return null;
    return payload.exp * 1000; // convert seconds → ms
  } catch {
    return null;
  }
}

/**
 * Returns true if we have a token that hasn't expired yet.
 * Conservative: treats missing expiry as invalid.
 *
 * @returns {boolean}
 */
export function isTokenValid() {
  const expiry = getTokenExpiry();
  if (expiry === null) return false;
  return expiry > Date.now();
}
