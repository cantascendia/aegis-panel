/**
 * Customer Portal API client — Track B P2.
 *
 * All endpoints sit under /api/customers/* and require a Bearer token
 * issued by POST /api/customers/sub-login (15-min JWT, customer scope).
 *
 * Token storage is intentionally minimal: sessionStorage so the token
 * is cleared when the tab is closed. P3 may upgrade to a refresh-token
 * flow once the backend ships one.
 *
 * Graceful-404 pattern:
 *   Endpoints not yet shipped by the backend return 404. Rather than
 *   crashing the UI, each helper detects 404 and returns a sentinel
 *   value with `_placeholder: true` so the caller can render a "Demo
 *   data" badge instead of an error screen.
 */

// ---------------------------------------------------------------------------
// Token helpers (shared with Wave-P1 — if customer-auth.js is created by P1
// it will use the same sessionStorage key so both modules interoperate).
// ---------------------------------------------------------------------------

const TOKEN_KEY = 'nilou_customer_token';

export function storeToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Base fetch wrapper
// ---------------------------------------------------------------------------

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers ?? {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  return res;
}

// ---------------------------------------------------------------------------
// Auth — sub-login
// ---------------------------------------------------------------------------

/**
 * Exchange a subscription URL for a customer JWT.
 * Stores the token in sessionStorage on success.
 *
 * @param {string} subUrl - Full subscription URL (https://…/sub/<username>/<key>)
 * @returns {{ ok: true, username: string } | { ok: false, error: string }}
 */
export async function subLogin(subUrl) {
  try {
    const res = await fetch(`${API_BASE}/api/customers/sub-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sub_url: subUrl }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail ?? `HTTP ${res.status}` };
    }
    const data = await res.json();
    storeToken(data.access_token);
    return { ok: true, username: data.username, user_id: data.user_id };
  } catch (err) {
    return { ok: false, error: err.message ?? 'Network error' };
  }
}

// ---------------------------------------------------------------------------
// GET /api/customers/me
// ---------------------------------------------------------------------------

/**
 * Fetch the authenticated customer's own state.
 *
 * @returns {Promise<{
 *   ok: boolean,
 *   status?: number,
 *   data?: import('./customer-api.js').CustomerMe,
 *   error?: string
 * }>}
 */
export async function getMe() {
  try {
    const res = await apiFetch('/api/customers/me');
    if (res.status === 401) return { ok: false, status: 401, error: 'Unauthorized' };
    if (!res.ok) return { ok: false, status: res.status, error: `HTTP ${res.status}` };
    const data = await res.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err.message ?? 'Network error' };
  }
}

// ---------------------------------------------------------------------------
// GET /api/customers/me/traffic?days=N  (endpoint may not exist yet → 404)
// ---------------------------------------------------------------------------

/**
 * Fetch daily traffic breakdown for the last N days.
 *
 * 404 fallback: returns `{ _placeholder: true, daily: [...mock], total_bytes: 0 }`
 * so the UI can render a "Demo data" badge rather than an error.
 *
 * @param {number} days - Number of days (7 | 14 | 30)
 * @returns {Promise<{ _placeholder?: true, daily: Array<{date: string, used_bytes: number}>, total_bytes: number }>}
 */
export async function getMyTraffic(days = 14) {
  try {
    const res = await apiFetch(`/api/customers/me/traffic?days=${days}`);
    if (res.status === 404 || res.status === 501) {
      // Endpoint not yet shipped — return plausible placeholder data.
      return _trafficPlaceholder(days);
    }
    if (!res.ok) return _trafficPlaceholder(days);
    const data = await res.json();
    return { ...data, _placeholder: false };
  } catch (_err) {
    return _trafficPlaceholder(days);
  }
}

function _trafficPlaceholder(days) {
  const seeds = [2.1, 2.8, 1.6, 3.2, 2.4, 1.9, 4.1, 3.8, 2.9, 3.4, 4.6, 3.1, 5.2, 4.8, 3.6, 2.7, 3.9, 4.2, 2.3, 1.8, 3.5, 4.0, 2.6, 3.3, 4.7, 3.0, 2.2, 5.0, 4.4, 3.7];
  const daily = Array.from({ length: days }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return {
      date: d.toISOString().slice(0, 10),
      used_bytes: Math.round(seeds[i % seeds.length] * 1e9),
    };
  });
  const total_bytes = daily.reduce((s, r) => s + r.used_bytes, 0);
  return { _placeholder: true, daily, total_bytes };
}

// ---------------------------------------------------------------------------
// GET /api/customers/me/invoices  (endpoint may not exist yet → 404)
// ---------------------------------------------------------------------------

/**
 * Fetch the customer's invoice list.
 *
 * 404 fallback: returns `{ _placeholder: true, invoices: [...mock] }`.
 *
 * @returns {Promise<{ _placeholder?: true, invoices: Array<{id, amount, currency, status, paid_at, plan_name}> }>}
 */
export async function getMyInvoices() {
  try {
    const res = await apiFetch('/api/customers/me/invoices');
    if (res.status === 404 || res.status === 501) {
      return _invoicePlaceholder();
    }
    if (!res.ok) return _invoicePlaceholder();
    const data = await res.json();
    // Normalise — backend may return array directly or wrapped object.
    const invoices = Array.isArray(data) ? data : (data.invoices ?? []);
    return { _placeholder: false, invoices };
  } catch (_err) {
    return _invoicePlaceholder();
  }
}

function _invoicePlaceholder() {
  return {
    _placeholder: true,
    invoices: [
      { id: 'INV-2025-0428', amount: 0, currency: 'JPY', status: 'paid', paid_at: '2025-04-28T09:00:00Z', plan_name: 'Trial activation' },
    ],
  };
}

// ---------------------------------------------------------------------------
// GET /billing/plans  (may be owned by ops/billing layer → 404)
// ---------------------------------------------------------------------------

/**
 * Fetch publicly available subscription plans.
 *
 * 404 fallback: returns `{ _placeholder: true, plans: [] }` — the UI falls
 * back to its static PLANS constant from MarketingSections.jsx.
 *
 * @returns {Promise<{ _placeholder?: true, plans: Array }>}
 */
export async function getAvailablePlans() {
  try {
    const res = await apiFetch('/api/billing/plans');
    if (res.status === 404 || res.status === 501) {
      return { _placeholder: true, plans: [] };
    }
    if (!res.ok) return { _placeholder: true, plans: [] };
    const data = await res.json();
    const plans = Array.isArray(data) ? data : (data.plans ?? []);
    return { _placeholder: false, plans };
  } catch (_err) {
    return { _placeholder: true, plans: [] };
  }
}

// ---------------------------------------------------------------------------
// Utility: pretty-print bytes → human readable string
// ---------------------------------------------------------------------------

/**
 * Convert bytes to a human-readable string (GB with 1 decimal, or MB if < 1 GB).
 * @param {number} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 GB';
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(0)} MB`;
  return `${(bytes / 1e3).toFixed(0)} KB`;
}

/**
 * Compute used-traffic percentage (0–100), clamped.
 * Returns 0 if data_limit is null/0.
 * @param {number} used_traffic
 * @param {number|null} data_limit
 * @returns {number}
 */
export function trafficPercent(used_traffic, data_limit) {
  if (!data_limit) return 0;
  return Math.min(100, Math.round((used_traffic / data_limit) * 100));
}
