/**
 * Customer portal API client.
 *
 * Thin fetch wrapper for POST /api/customers/sub-login and
 * GET /api/customers/me. Uses relative URLs so it works regardless of
 * the origin (local dev via Vite proxy, or prod mounted under /portal/).
 *
 * Error contract: every failed request throws a CustomerApiError with
 * { status, detail } so callers can branch on HTTP status without parsing
 * raw Response objects.
 *
 * Forbidden-path note: this module is imported by AuthPages.jsx (§32.1).
 * Changes to the request/response shape must match app/routes/customer.py
 * exactly (SubLoginResponse / CustomerMeResponse pydantic models).
 */

import { getToken } from './customer-auth.js';

/** Structured error thrown by all API helpers on non-2xx responses. */
export class CustomerApiError extends Error {
  /**
   * @param {number} status - HTTP status code
   * @param {string} detail - Human-readable message (from backend detail field)
   */
  constructor(status, detail) {
    super(detail);
    this.name = 'CustomerApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Parse an error response body into a readable detail string.
 * Backend uses FastAPI's default `{"detail": "..."}` shape.
 *
 * @param {Response} res
 * @returns {Promise<string>}
 */
async function _extractDetail(res) {
  try {
    const body = await res.json();
    if (body && typeof body.detail === 'string') return body.detail;
    if (body && typeof body.detail === 'object') return JSON.stringify(body.detail);
    return res.statusText || `HTTP ${res.status}`;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

/**
 * Exchange a subscription URL for a 15-min customer JWT.
 *
 * Matches: POST /api/customers/sub-login
 * Request:  { sub_url: string }
 * Response: SubLoginResponse { access_token, token_type, user_id, username, expires_in_seconds }
 *
 * @param {string} subUrl - Full subscription URL (e.g. https://nilou.cc/sub/alice/abc123...)
 * @returns {Promise<{access_token: string, token_type: string, user_id: number, username: string, expires_in_seconds: number}>}
 * @throws {CustomerApiError} on 400 (malformed URL) or 401 (invalid credential)
 */
export async function subLogin(subUrl) {
  const res = await fetch('/api/customers/sub-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sub_url: subUrl }),
  });

  if (!res.ok) {
    const detail = await _extractDetail(res);
    throw new CustomerApiError(res.status, detail);
  }

  return res.json();
}

/**
 * Return the authenticated customer's own state.
 *
 * Matches: GET /api/customers/me
 * Auth:    Bearer token from localStorage via getToken()
 * Response: CustomerMeResponse { user_id, username, used_traffic, data_limit,
 *            data_limit_reset_strategy, expire_date, expire_strategy,
 *            is_active, online_at, note }
 *
 * @returns {Promise<import('./types').CustomerMeResponse>}
 * @throws {CustomerApiError} on 401 (missing/expired token) or other errors
 */
export async function getMe() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch('/api/customers/me', { headers });

  if (!res.ok) {
    const detail = await _extractDetail(res);
    throw new CustomerApiError(res.status, detail);
  }

  return res.json();
}
