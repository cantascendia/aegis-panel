// Auth pages: Login, Signup
// Forbidden-path: §32.1 — every edit here requires double-sign + codex cross-review.
// P2 wires: LoginPage now calls POST /api/customers/sub-login (Wave-P1).
import React, { useState } from 'react';
import { useRoute, Link, LotusMark, Btn } from './Atoms.jsx';
import { subLogin } from './customer-api.js';
import { setToken } from './customer-auth.js';

const AuthShell = ({ title, accent, sub, children, footer }) => (
  <div style={{
    minHeight: '100vh',
    background: 'radial-gradient(ellipse 80% 60% at 50% 0%, var(--brand-cream-warm) 0%, transparent 60%), var(--surface)',
    display: 'grid', placeItems: 'center', padding: '40px 24px', position: 'relative', overflow: 'hidden',
  }}>
    <svg viewBox="0 0 200 200" aria-hidden="true" style={{ position: 'absolute', width: 520, height: 520, color: 'var(--brand-teal)', top: -160, right: -160, opacity: 0.4 }}>
      <circle cx="100" cy="100" r="40" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      <circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2" />
    </svg>
    <div style={{ width: '100%', maxWidth: 440, position: 'relative' }}>
      <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 32, color: 'var(--brand-navy)', fontWeight: 700 }}>
        <LotusMark size={28} /> <span>Nilou Network</span>
      </Link>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 14, padding: 36, boxShadow: 'var(--shadow-md)' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.8rem', color: 'var(--brand-navy)', margin: '0 0 8px', letterSpacing: '-0.02em' }}>
          {title} {accent && <span style={{ color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>{accent}</span>}
        </h1>
        {sub && <p style={{ margin: '0 0 24px', color: 'var(--text-secondary)', fontSize: '0.96rem' }}>{sub}</p>}
        {children}
      </div>
      {footer && <div style={{ textAlign: 'center', marginTop: 20, fontSize: '0.92rem', color: 'var(--text-muted)' }}>{footer}</div>}
    </div>
  </div>
);

const inputCss = {
  width: '100%', padding: '11px 14px', borderRadius: 6, border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--brand-navy)', fontSize: '0.94rem',
  fontFamily: 'var(--font-body)', boxSizing: 'border-box', outline: 'none',
};
const FieldGroup = ({ label, hint, children, style = {} }) => (
  <label style={{ display: 'block', marginBottom: 16, ...style }}>
    <div style={{ fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>{label}</div>
    {children}
    {hint && <div style={{ marginTop: 4, fontSize: '0.78rem', color: 'var(--text-muted)' }}>{hint}</div>}
  </label>
);

/**
 * LoginPage — P2 real wiring.
 *
 * Accepts a subscription URL (the customer's existing sub URL) and exchanges
 * it for a 15-min JWT via POST /api/customers/sub-login.
 *
 * Security checklist (per SPEC-customer-portal-p2.md §1.3-C and
 * PORTAL-RELIABILITY.md §2):
 * 1. Awaits fetch + checks .ok before storing token.
 * 2. Error branch keeps user on /login + shows inline error.
 * 3. Token stored via setToken() (customer-auth.js), not raw localStorage.
 * 4. No admin token path — this only accepts sub URLs, not email/password.
 *
 * Visual layout is PRESERVED from P1 — same Cormorant title, same Card,
 * same button styling. Only form content and onSubmit changed.
 */
const LoginPage = () => {
  const { go } = useRoute();
  const [subUrl, setSubUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Client-side guard: sub URL must be at least 9 chars (scheme + host minimum)
    if (subUrl.trim().length < 9) {
      setError('Please enter your subscription URL.');
      return;
    }

    setLoading(true);
    try {
      const data = await subLogin(subUrl.trim());
      setToken(data.access_token);
      go('/panel');
    } catch (err) {
      // Keep user on login page; clear sub URL for security; show detail.
      setSubUrl('');
      setError(
        err && err.detail
          ? err.detail
          : 'Login failed. Please check your subscription URL and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back,"
      accent="lotus."
      sub="Paste your subscription URL to sign in."
      footer={<>Don&apos;t have an account? <Link to="/signup" style={{ color: 'var(--brand-teal)', fontWeight: 600 }}>Create one</Link></>}
    >
      <form onSubmit={handleSubmit}>
        <FieldGroup
          label="Subscription URL"
          hint="Starts with https://nilou.network/sub/…"
        >
          <textarea
            value={subUrl}
            onChange={(e) => setSubUrl(e.target.value)}
            placeholder="https://nilou.network/sub/username/key"
            rows={3}
            style={{
              ...inputCss,
              resize: 'vertical',
              lineHeight: 1.5,
              fontFamily: 'var(--font-mono)',
              fontSize: '0.84rem',
            }}
            disabled={loading}
            required
          />
        </FieldGroup>

        {error && (
          <div
            role="alert"
            style={{
              marginBottom: 16,
              padding: '10px 14px',
              borderRadius: 6,
              background: 'rgba(224,120,86,0.10)',
              border: '1px solid rgba(224,120,86,0.35)',
              color: 'var(--accent-coral, #c0522e)',
              fontSize: '0.88rem',
              lineHeight: 1.45,
            }}
          >
            {error}
          </div>
        )}

        <Btn variant="primary" type="submit" full disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Btn>
      </form>
    </AuthShell>
  );
};

const SignupPage = () => {
  const { go } = useRoute();
  const [step, setStep] = useState(1);
  const [plan, setPlan] = useState('monthly');
  return (
    <AuthShell title={step === 1 ? 'Create your' : 'Pick your'} accent={step === 1 ? 'account.' : 'plan.'} sub={step === 1 ? 'Three days free, no card required.' : "You can change anytime from billing."}
      footer={step === 1 ? <>Already a member? <Link to="/login" style={{ color: 'var(--brand-teal)', fontWeight: 600 }}>Sign in</Link></> : null}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 22 }}>
        {[1, 2].map(s => (
          <div key={s} style={{ flex: 1, height: 4, borderRadius: 2, background: s <= step ? 'var(--brand-teal)' : 'var(--border-soft)' }} />
        ))}
      </div>
      {step === 1 ? (
        <form onSubmit={(e) => { e.preventDefault(); setStep(2); }}>
          <FieldGroup label="Email"><input type="email" placeholder="you@example.com" style={inputCss} required /></FieldGroup>
          <FieldGroup label="Password" hint="At least 12 characters · upper, number, symbol"><input type="password" placeholder="••••••••••••" style={inputCss} required /></FieldGroup>
          <FieldGroup label="Invite code (optional)" hint="Save ¥10 with a friend's code"><input type="text" placeholder="LOTUS-XXXX" style={inputCss} /></FieldGroup>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: '0.86rem', color: 'var(--text-secondary)', margin: '8px 0 18px' }}>
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--brand-teal)', marginTop: 3 }} required />
            <span>I agree to the <a style={{ color: 'var(--brand-teal)' }}>Terms</a> and <a style={{ color: 'var(--brand-teal)' }}>Privacy Policy</a>, and acknowledge the AGPL source-disclosure notice.</span>
          </label>
          <Btn variant="primary" type="submit" full>Continue</Btn>
        </form>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
            {[
              { id: 'trial', name: 'Trial · 3 days free', price: 'Free', sub: '100 GB · cancel any time' },
              { id: 'monthly', name: 'Monthly · ¥30/mo', price: '¥30', sub: '500 GB · standard nodes' },
              { id: 'quarterly', name: 'Quarterly · ¥80', price: '¥80', sub: '1.5 TB · premium · ~11% off' },
              { id: 'annual', name: 'Annual · ¥240', price: '¥240', sub: '6 TB · premium · ~33% off' },
            ].map(p => (
              <label key={p.id} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderRadius: 8,
                border: `2px solid ${plan === p.id ? 'var(--brand-teal)' : 'var(--border-soft)'}`,
                background: plan === p.id ? 'rgba(58,145,136,0.04)' : 'var(--surface)',
                cursor: 'pointer'
              }}>
                <input type="radio" name="plan" checked={plan === p.id} onChange={() => setPlan(p.id)} style={{ accentColor: 'var(--brand-teal)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: 'var(--brand-navy)', fontSize: '0.94rem' }}>{p.name}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 2 }}>{p.sub}</div>
                </div>
                <div style={{ fontFamily: 'var(--font-display)', color: 'var(--brand-teal)', fontSize: '1.3rem', fontWeight: 500 }}>{p.price}</div>
              </label>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn variant="ghost" onClick={() => setStep(1)} style={{ flex: '0 0 auto' }}>Back</Btn>
            <Btn variant="primary" onClick={() => go('/dashboard')} style={{ flex: 1 }}>{plan === 'trial' ? 'Start trial' : 'Continue to payment'}</Btn>
          </div>
        </>
      )}
    </AuthShell>
  );
};

export { LoginPage, SignupPage, FieldGroup, inputCss };
