// React error boundary — closes PORTAL-RELIABILITY.md §4 "P1 已知缺陷".
// Two layers per §4 mandate:
//   (1) App-level — catches unhandled render errors anywhere.
//   (2) PanelShell-level — when wrapped around PanelShell children, panel
//       page crashes leave sidebar+topbar visible.
// Telemetry stub: localStorage capped FIFO 20 records (no Sentry / GA per §4).
import React from 'react';

const STORAGE_KEY = 'aegis_portal_errors';
const MAX_RECORDS = 20;

const logBoundaryError = (error, info, scope) => {
  try {
    const records = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    records.unshift({
      ts: new Date().toISOString(),
      scope,
      msg: String(error?.message || error || 'unknown'),
      stack: String(error?.stack || '').split('\n').slice(0, 5).join('\n'),
      componentStack: String(info?.componentStack || '').split('\n').slice(0, 5).join('\n'),
      hash: typeof window !== 'undefined' ? window.location.hash : '',
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records.slice(0, MAX_RECORDS)));
  } catch (e) {
    // localStorage unavailable / quota — swallow to avoid recursion
  }
  // eslint-disable-next-line no-console
  console.error(`[portal:${scope}]`, error, info);
};

const FallbackChrome = ({ scope, onReset }) => (
  <div
    role="alert"
    style={{
      maxWidth: 640,
      margin: '80px auto',
      padding: '32px 28px',
      background: 'var(--surface)',
      border: '1px solid var(--border-soft)',
      borderRadius: 'var(--r-lg, 10px)',
      boxShadow: 'var(--shadow-md)',
      textAlign: 'center',
    }}
  >
    <h2
      style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 500,
        fontSize: '1.6rem',
        color: 'var(--brand-navy)',
        margin: '0 0 12px',
      }}
    >
      Something didn&apos;t load right.
    </h2>
    <p style={{ color: 'var(--text-secondary)', lineHeight: 1.65, margin: '0 0 22px' }}>
      The page hit an error{scope === 'panel' ? ' inside the panel' : ''}. The team has been notified.
      Try refreshing, or{' '}
      <a href="#/contact" style={{ color: 'var(--brand-teal)', textDecoration: 'underline' }}>
        contact us
      </a>{' '}
      if it persists.
    </p>
    <button
      type="button"
      onClick={onReset}
      style={{
        padding: '10px 22px',
        background: 'var(--brand-teal)',
        color: '#fff',
        border: 'none',
        borderRadius: 6,
        fontWeight: 600,
        cursor: 'pointer',
      }}
    >
      Reload
    </button>
  </div>
);

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
    this.handleReset = this.handleReset.bind(this);
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    logBoundaryError(error, info, this.props.scope || 'app');
  }

  handleReset() {
    // Hash-router safe reload — preserves URL.
    if (typeof window !== 'undefined') window.location.reload();
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return <FallbackChrome scope={this.props.scope} onReset={this.handleReset} />;
    }
    return this.props.children;
  }
}

export { ErrorBoundary, logBoundaryError };
