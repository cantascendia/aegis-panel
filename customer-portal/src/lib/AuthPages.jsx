// Auth pages: Login, Signup
import React, { useState } from 'react';
import { useRoute, Link, LotusMark, Btn } from './Atoms.jsx';

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

const LoginPage = () => {
  const { go } = useRoute();
  return (
    <AuthShell title="Welcome back," accent="lotus." sub="Sign in to your dashboard."
      footer={<>Don&apos;t have an account? <Link to="/signup" style={{ color: 'var(--brand-teal)', fontWeight: 600 }}>Create one</Link></>}>
      <form onSubmit={(e) => { e.preventDefault(); go('/dashboard'); }}>
        <FieldGroup label="Email"><input type="email" defaultValue="liu.wei@nilou-demo.network" style={inputCss} /></FieldGroup>
        <FieldGroup label="Password"><input type="password" defaultValue="••••••••••" style={inputCss} /></FieldGroup>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.86rem', marginBottom: 20 }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input type="checkbox" defaultChecked style={{ accentColor: 'var(--brand-teal)' }} /> Remember me
          </label>
          <a style={{ color: 'var(--brand-teal)', fontWeight: 500 }}>Forgot password?</a>
        </div>
        <Btn variant="primary" type="submit" full>Sign in</Btn>
      </form>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
        <div style={{ height: 1, background: 'var(--border-soft)', flex: 1 }} /> or <div style={{ height: 1, background: 'var(--border-soft)', flex: 1 }} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Btn variant="secondary"><span style={{ fontSize: '1.1em' }}>G</span> Google</Btn>
        <Btn variant="secondary"><span style={{ fontSize: '1.1em' }}>⌘</span> GitHub</Btn>
      </div>
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
