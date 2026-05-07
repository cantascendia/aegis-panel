/**
 * Customer portal API client.
 *
 * Thin fetch wrapper for /api/customers/*. Uses relative URLs.
 *
 * Endpoints currently shipped (wave-S backend, commit bc135d8):
 *   POST /api/customers/sub-login → subLogin(subUrl)
 *   GET  /api/customers/me        → getMe()
 *
 * Endpoints not yet shipped — guarded by graceful-404. Caller receives
 * `{ _placeholder: true, ... }` and renders "Demo data" badge:
 *   GET /api/customers/me/traffic
 *   GET /api/customers/me/invoices
 *   GET /api/billing/plans
 *
 * Forbidden-path note: imported by AuthPages.jsx (§32.1). Request /
 * response shapes MUST match app/routes/customer.py pydantic models.
 */

import { getToken } from './customer-auth.js';

export class CustomerApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = 'CustomerApiError';
    this.status = status;
    this.detail = detail;
  }
}

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

export async function getMe() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch('/api/customers/me', { headers });
  if (!res.ok) {
    const detail = await _extractDetail(res);
    throw new CustomerApiError(res.status, detail);
  }
  return res.json();
}

async function _getWithGraceful404(path, placeholder) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(path, { headers });
  } catch {
    return { _placeholder: true, _reason: 'network', ...placeholder };
  }
  if (res.status === 404) {
    return { _placeholder: true, _reason: 'endpoint-missing', ...placeholder };
  }
  if (!res.ok) {
    const detail = await _extractDetail(res);
    throw new CustomerApiError(res.status, detail);
  }
  return res.json();
}

export async function getMyTraffic(days = 14) {
  return _getWithGraceful404(
    `/api/customers/me/traffic?days=${encodeURIComponent(days)}`,
    { daily: [], total_bytes: 0 }
  );
}

export async function getMyInvoices() {
  return _getWithGraceful404('/api/customers/me/invoices', { invoices: [] });
}

export async function getAvailablePlans() {
  return _getWithGraceful404('/api/billing/plans', { plans: [] });
}

// ---------------------------------------------------------------------------
// Display helpers (used by panel pages — shipped here so PanelPages1 can
// import alongside getMe / getMyTraffic).
// ---------------------------------------------------------------------------

/**
 * Format bytes as human-readable string (e.g. "38.6 GB", "452 MB").
 * Mirrors the design package's pretty-bytes-style output.
 *
 * @param {number} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
  if (bytes == null || isNaN(bytes)) return '—';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const exp = Math.min(Math.floor(Math.log(Math.abs(bytes)) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exp);
  // 1 decimal for ≥1 GB, integer for smaller units.
  const decimals = exp >= 3 && value < 100 ? 1 : 0;
  return `${value.toFixed(decimals)} ${units[exp]}`;
}

/**
 * Compute usage percentage as integer 0-100, clamped.
 *
 * @param {number} used
 * @param {number} limit
 * @returns {number} 0-100
 */
export function trafficPercent(used, limit) {
  if (!limit || limit <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((used / limit) * 100)));
}
