import React, { useEffect } from 'react';
import { useRoute, Btn, Eyebrow } from './lib/Atoms.jsx';
import { ErrorBoundary } from './lib/ErrorBoundary.jsx';
import { MarketingTopbar, MarketingFooter, Section } from './lib/Marketing.jsx';
import {
  HomePage,
  FeaturesPage,
  PricingPage,
  FAQPage,
  AboutPage,
  ContactPage,
  StatusPage,
  LegalPage,
} from './lib/MarketingPages.jsx';
import { LoginPage, SignupPage } from './lib/AuthPages.jsx';
import { DashboardPage, NodesPage } from './lib/PanelPages1.jsx';
import {
  TrafficPage,
  PlansPage,
  BillingPage,
  TicketsPage,
  InvitePage,
  AccountPage,
  DocsPage,
} from './lib/PanelPages2.jsx';
import { isTokenValid } from './lib/customer-auth.js';

// Routes that require a valid customer JWT.
// Marketing routes, /login, and /signup are open.
const PROTECTED_PREFIXES = ['/panel', '/dashboard'];

/**
 * Returns true if the given path requires authentication.
 * Prefix-match so /panel/account, /panel/traffic, etc. are all covered.
 */
function isProtected(path) {
  return PROTECTED_PREFIXES.some((prefix) => path === prefix || path.startsWith(prefix + '/') || path.startsWith(prefix));
}

const NotFound = ({ path }) => (
  <Section pad="120px 0 160px">
    <div style={{ textAlign: 'center', maxWidth: 540, margin: '0 auto' }}>
      <Eyebrow>404 · path not found</Eyebrow>
      <h1
        style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 500,
          fontSize: '3rem',
          color: 'var(--brand-navy)',
          margin: '0 0 16px',
        }}
      >
        Off the lotus path.
      </h1>
      <p
        style={{
          color: 'var(--text-secondary)',
          fontSize: '1.04rem',
          marginBottom: 28,
        }}
      >
        The page{' '}
        <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--brand-teal)' }}>{path}</code>{' '}
        doesn&apos;t exist. Maybe try the home page or the dashboard.
      </p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <Btn variant="primary" to="/">
          Home
        </Btn>
        <Btn variant="secondary" to="/panel">
          Dashboard
        </Btn>
      </div>
    </div>
  </Section>
);

const App = () => {
  const { path, go } = useRoute();

  // Auth guard: redirect unauthenticated users away from protected routes.
  // Runs synchronously before route resolution so no protected content flashes.
  useEffect(() => {
    if (isProtected(path) && !isTokenValid()) {
      go('/login');
    }
  }, [path, go]);

  // If the current path is protected and the token is invalid, render nothing
  // while the redirect effect fires (avoids a flash of the protected page).
  if (isProtected(path) && !isTokenValid()) {
    return null;
  }

  const route = (() => {
    if (path === '/' || path === '') return { kind: 'marketing', label: '01 Home', el: <HomePage /> };
    if (path === '/features') return { kind: 'marketing', label: '02 Features', el: <FeaturesPage /> };
    if (path === '/pricing') return { kind: 'marketing', label: '03 Pricing', el: <PricingPage /> };
    if (path === '/faq') return { kind: 'marketing', label: '04 FAQ', el: <FAQPage /> };
    if (path === '/about') return { kind: 'marketing', label: '05 About', el: <AboutPage /> };
    if (path === '/contact') return { kind: 'marketing', label: '06 Contact', el: <ContactPage /> };
    if (path === '/status') return { kind: 'marketing', label: '07 Status', el: <StatusPage /> };
    if (path === '/legal') return { kind: 'marketing', label: '08 Legal', el: <LegalPage /> };

    if (path === '/login') return { kind: 'auth', label: '09 Sign in', el: <LoginPage /> };
    if (path === '/signup') return { kind: 'auth', label: '10 Sign up', el: <SignupPage /> };

    if (path === '/dashboard' || path === '/panel' || path === '/panel/')
      return { kind: 'panel', label: '11 Dashboard', el: <DashboardPage /> };
    if (path === '/panel/nodes') return { kind: 'panel', label: '12 Nodes', el: <NodesPage /> };
    if (path === '/panel/traffic') return { kind: 'panel', label: '13 Traffic', el: <TrafficPage /> };
    if (path === '/panel/plans') return { kind: 'panel', label: '14 Plans', el: <PlansPage /> };
    if (path === '/panel/billing') return { kind: 'panel', label: '15 Billing', el: <BillingPage /> };
    if (path === '/panel/tickets') return { kind: 'panel', label: '16 Tickets', el: <TicketsPage /> };
    if (path === '/panel/invite') return { kind: 'panel', label: '17 Invite', el: <InvitePage /> };
    if (path === '/panel/account') return { kind: 'panel', label: '18 Account', el: <AccountPage /> };
    if (path === '/panel/docs') return { kind: 'panel', label: '19 Docs', el: <DocsPage /> };

    return { kind: 'marketing', label: '404', el: <NotFound path={path} /> };
  })();

  useEffect(() => {
    document.title = `${route.label.replace(/^\d+\s+/, '')} — Nilou Network`;
  }, [route.label]);

  // Wrap the route subtree in an ErrorBoundary (PORTAL-RELIABILITY.md §4).
  // App-level boundary catches any thrown error in any of the 19 routes.
  // P2.3 will additionally wrap PanelShell with a panel-scope boundary so
  // panel page crashes don't unmount sidebar+topbar.
  return (
    <div data-screen-label={route.label}>
      <ErrorBoundary scope="app">
        {route.kind === 'marketing' && (
          <>
            <MarketingTopbar />
            {route.el}
            <MarketingFooter />
          </>
        )}
        {route.kind === 'auth' && route.el}
        {route.kind === 'panel' && route.el}
      </ErrorBoundary>
    </div>
  );
};

export default App;
