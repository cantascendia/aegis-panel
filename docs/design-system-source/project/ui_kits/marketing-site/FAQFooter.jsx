const FAQS = [
  { q: 'How is this different from a basic VPS?', a: "A VPS gives you a blank Linux box — you install, patch, monitor, and back up everything yourself. Nilou Network gives you a managed instance of an open-source application that's already configured, kept current, and backed by a real person you can email when something goes sideways." },
  { q: 'Can I migrate to self-hosting later?', a: 'Yes. The software we operate is open-source — you can stand up the same application on your own hardware whenever you like. We will export your data and configuration on request, in standard formats, free of charge.' },
  { q: "What's your refund policy?", a: 'Subscriptions can be cancelled any time from your dashboard. Refunds for unused service time are processed within 7 business days of an approved request.' },
  { q: "What's your uptime target?", a: "We target 99.9% monthly uptime for managed instances. We do not offer a contractual SLA at the current scale — we'd rather be honest about being a small operation than promise enterprise guarantees we can't keep." },
];

const FAQ = () => {
  const [open, setOpen] = React.useState(0);
  return (
    <section id="faq" style={{ padding: '96px 0', background: 'var(--surface)' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>
        <div style={{ textAlign: 'center', maxWidth: 720, margin: '0 auto 64px' }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(1.9rem, 3.4vw, 2.6rem)', letterSpacing: '-0.02em', color: 'var(--brand-navy)', margin: '0 0 16px', lineHeight: 1.2 }}>Frequently asked</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.06rem', margin: 0 }}>Honest answers to the questions we hear most.</p>
        </div>
        <div style={{ maxWidth: 780, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {FAQS.map((f, i) => {
            const isOpen = open === i;
            return (
              <div key={f.q} style={{
                background: 'var(--surface)',
                border: `1px solid ${isOpen ? 'var(--brand-teal)' : 'var(--border-soft)'}`,
                borderRadius: 10, overflow: 'hidden',
                boxShadow: isOpen ? 'var(--shadow-sm)' : 'none'
              }}>
                <button onClick={() => setOpen(isOpen ? -1 : i)} style={{
                  width: '100%', textAlign: 'left', background: 'transparent', border: 0,
                  padding: '20px 24px', fontWeight: 600, color: 'var(--brand-navy)',
                  fontSize: '1.02rem', display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', gap: 16, cursor: 'pointer', fontFamily: 'var(--font-body)'
                }}>
                  {f.q}
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3a9188" strokeWidth="2.2" strokeLinecap="round" style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.18s' }}>
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </button>
                {isOpen && (
                  <div style={{ padding: '0 24px 20px', color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.96rem' }}>
                    <p style={{ margin: 0 }}>{f.a}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

const Footer = () => (
  <footer style={{ background: 'var(--brand-navy)', color: 'var(--text-on-dark)', padding: '64px 0 48px', borderTop: '3px solid var(--brand-teal)' }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 32, marginBottom: 48 }}>
        {[
          { h: 'Product', items: ['Features', 'Pricing', 'Status (soon)', 'Changelog (soon)'] },
          { h: 'Company', items: ['About', 'Contact', 'Legal & 特商法表記'] },
          { h: 'Resources', items: ['FAQ', 'Open-source notice', 'Trademark notice'] },
          { h: 'Languages', items: ['English', '日本語', '中文'] },
        ].map(col => (
          <div key={col.h}>
            <h4 style={{ fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--brand-gold-soft)', margin: '0 0 16px', fontFamily: 'var(--font-body)' }}>{col.h}</h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {col.items.map(it => (
                <li key={it} style={{ color: 'var(--text-on-dark)', fontSize: '0.92rem', opacity: it.includes('(soon)') ? 0.45 : 0.82, fontStyle: it.includes('(soon)') ? 'italic' : 'normal' }}>{it}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div style={{ paddingTop: 24, borderTop: '1px solid rgba(245, 236, 220, 0.12)', textAlign: 'center', fontSize: '0.82rem', color: 'var(--brand-gold-soft)', opacity: 0.7 }}>
        © 2025 Nilou Network · 個人事業主 in Japan · AGPL-3.0 source-disclosure compliant
      </div>
    </div>
  </footer>
);

Object.assign(window, { FAQ, Footer });
