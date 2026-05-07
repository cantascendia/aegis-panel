const FEATURES = [
  { n: 1, num: '01', title: 'Managed instance', body: 'A dedicated cloud-hosted instance maintained by us. Patches, upgrades, and dependency hygiene are handled in the background.' },
  { n: 2, num: '02', title: 'Operator support', body: 'Real-person support for configuration questions, integration help, and incident response — usually within a single business day.' },
  { n: 3, num: '03', title: 'Infrastructure care', body: 'SSL certificates, backups, upgrade windows, and monitoring kept current. Your service stays audit-friendly without your effort.' },
  { n: 4, num: '04', title: 'Open-source friendly', body: 'The software we operate is open-source. You can self-host the same application at any time — there is no proprietary lock-in.' },
  { n: 5, num: '05', title: 'Multi-region', body: 'Hosting available across Asia-Pacific regions, so you can pick a location that matches your latency budget.' },
  { n: 6, num: '06', title: 'Transparent pricing', body: 'Flat subscription tiers in CNY. No hidden fees, no usage surprises. Cancel any time from the dashboard.' },
];

const Features = () => (
  <section id="features" style={{ padding: '96px 0', background: 'var(--surface)' }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>
      <div style={{ textAlign: 'center', maxWidth: 720, margin: '0 auto 64px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(1.9rem, 3.4vw, 2.6rem)', letterSpacing: '-0.02em', color: 'var(--brand-navy)', margin: '0 0 16px', lineHeight: 1.2 }}>Operational details</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.06rem', margin: 0 }}>Six things, kept simple.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: 24 }}>
        {FEATURES.map(f => (
          <article key={f.n} style={{ position: 'relative', padding: '32px 24px', background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <FeatureIcon n={f.n} />
            <div style={{ fontFamily: 'var(--font-body)', fontSize: '0.78rem', letterSpacing: '0.16em', color: 'var(--brand-gold)', textTransform: 'uppercase', fontWeight: 600 }}>{f.num}</div>
            <h3 style={{ margin: 0, color: 'var(--brand-navy)', fontSize: '1.08rem', fontWeight: 600, letterSpacing: '-0.005em' }}>{f.title}</h3>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.94rem', lineHeight: 1.65 }}>{f.body}</p>
          </article>
        ))}
      </div>
    </div>
  </section>
);

const PLANS = [
  { tag: 'Trial', name: 'Trial', price: 'Free', sub: '3 days', items: ['Full instance access', 'Email support', 'No payment required'], cta: 'Start trial', variant: 'secondary' },
  { tag: 'Monthly', name: 'Monthly', price: '¥30', sub: 'per month', items: ['Managed instance', 'Standard support', 'Cancel any time'], cta: 'Subscribe', variant: 'primary' },
  { tag: 'Quarterly · ~11% off', name: 'Quarterly', price: '¥80', sub: 'per 3 months', items: ['Managed instance', 'Priority support', '~11% discount'], cta: 'Subscribe', variant: 'primary', highlight: true },
  { tag: 'Annual · ~33% off', name: 'Annual', price: '¥240', sub: 'per year', items: ['Managed instance', 'Priority support', '~33% discount'], cta: 'Subscribe', variant: 'primary', highlight: true },
];

const Pricing = () => (
  <section id="pricing" style={{ padding: '96px 0', background: 'linear-gradient(180deg, var(--brand-cream) 0%, var(--surface-warm) 100%)' }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>
      <div style={{ textAlign: 'center', maxWidth: 720, margin: '0 auto 64px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(1.9rem, 3.4vw, 2.6rem)', letterSpacing: '-0.02em', color: 'var(--brand-navy)', margin: '0 0 16px', lineHeight: 1.2 }}>Subscription plans</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.06rem', margin: 0 }}>Four tiers, all running the same managed software. Choose by billing cadence.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(245px, 1fr))', gap: 24 }}>
        {PLANS.map(p => (
          <div key={p.name} style={{
            position: 'relative', padding: '48px 24px 32px',
            background: p.highlight ? 'linear-gradient(180deg, #fff 0%, var(--brand-cream-warm) 100%)' : 'var(--surface)',
            border: `1px solid ${p.highlight ? 'var(--brand-teal)' : 'var(--border-soft)'}`,
            borderRadius: 10, textAlign: 'center', boxShadow: 'var(--shadow-sm)'
          }}>
            <span style={{
              position: 'absolute', top: -13, left: '50%', transform: 'translateX(-50%)',
              background: p.highlight ? 'var(--brand-gold)' : 'var(--brand-teal)',
              color: p.highlight ? 'var(--brand-navy)' : '#fff',
              fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
              padding: '5px 14px', borderRadius: 999, whiteSpace: 'nowrap',
            }}>{p.tag}</span>
            <h3 style={{ margin: '12px 0 16px', color: 'var(--brand-navy)', fontSize: '1.05rem', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{p.name}</h3>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '2.8rem', fontWeight: 500, color: 'var(--brand-teal)', margin: '0 0 24px', lineHeight: 1 }}>
              {p.price}
              <small style={{ display: 'block', fontFamily: 'var(--font-body)', fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 400, marginTop: 8, letterSpacing: '0.02em' }}>{p.sub}</small>
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 32px', textAlign: 'left' }}>
              {p.items.map(it => (
                <li key={it} style={{ padding: '12px 0', borderBottom: '1px solid var(--border-soft)', color: 'var(--text-secondary)', fontSize: '0.92rem', display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--brand-teal)', fontWeight: 700 }}>✓</span>{it}
                </li>
              ))}
            </ul>
            <Btn variant={p.variant} style={{ width: '100%' }}>{p.cta}</Btn>
          </div>
        ))}
      </div>
    </div>
  </section>
);

Object.assign(window, { Features, Pricing });
