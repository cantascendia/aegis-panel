// Hero, Features, Pricing summary, FAQ accordion components
// shared between Home and dedicated pages.
import React, { useState } from 'react';
import { LotusMark, Eyebrow, Btn, Icon, ASSET } from './Atoms.jsx';
import { Section, SectionHead } from './Marketing.jsx';

const FEAT_GLYPHS = {
  1: <g><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" fill="currentColor" /></g>,
  2: <g><path d="M3 7.5C3 6.4 3.9 5.5 5 5.5h14c1.1 0 2 0.9 2 2v8.5c0 1.1-0.9 2-2 2H5c-1.1 0-2-0.9-2-2z" /><path d="M3.5 7l8.5 6 8.5-6" /><path d="M16 16l2.5 2.5 4-4" strokeWidth="1.6" /></g>,
  3: <g><path d="M12 2.5L4 6v6c0 4.5 3.4 8.6 8 9.5 4.6-0.9 8-5 8-9.5V6z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></g>,
  4: <g><circle cx="8" cy="12" r="4" /><path d="M12 12h9" /><path d="M16 12v3.5" /><path d="M19.5 12v2" /><circle cx="8" cy="12" r="1.2" fill="currentColor" /></g>,
  5: <g><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3c2.8 3 4.2 6 4.2 9s-1.4 6-4.2 9c-2.8-3-4.2-6-4.2-9s1.4-6 4.2-9z" /></g>,
  6: <g><path d="M3 8l3-3.5h12l3 3.5-9 12.5z" /><path d="M3 8h18" /><path d="M9 8l3 12.5L15 8" /><path d="M9 4.5l3 3.5 3-3.5" /></g>,
};

const FeatureIcon = ({ n }) => (
  <div style={{
    width: 44, height: 44, borderRadius: 6, display: 'grid', placeItems: 'center',
    background: 'linear-gradient(135deg, var(--brand-cream) 0%, var(--brand-cream-warm) 100%)',
    border: '1px solid var(--border-soft)', color: 'var(--brand-teal)', marginBottom: 8,
  }}>
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{FEAT_GLYPHS[n]}</svg>
  </div>
);

const Hero = () => (
  <section style={{
    position: 'relative', padding: '112px 0 88px',
    background: 'radial-gradient(ellipse 80% 60% at 50% 0%, var(--brand-cream-warm) 0%, transparent 60%), var(--surface)',
    overflow: 'hidden',
  }}>
    <svg viewBox="0 0 200 200" aria-hidden="true" style={{ position: 'absolute', width: 520, height: 520, color: 'var(--brand-teal)', top: -140, right: -140, opacity: 0.5, pointerEvents: 'none' }}>
      <circle cx="100" cy="100" r="40" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      <circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2" />
    </svg>
    <svg viewBox="0 0 200 200" aria-hidden="true" style={{ position: 'absolute', width: 620, height: 620, color: 'var(--brand-teal)', bottom: -180, left: -180, opacity: 0.5, pointerEvents: 'none' }}>
      <circle cx="100" cy="100" r="30" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      <circle cx="100" cy="100" r="50" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2" />
      <circle cx="100" cy="100" r="70" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.1" />
    </svg>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px', display: 'grid', gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)', gap: 88, alignItems: 'center', position: 'relative', zIndex: 1 }}>
      <div>
        <LotusMark size={84} breathe />
        <div style={{ height: 32 }} />
        <Eyebrow>Managed proxy network</Eyebrow>
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(2.4rem, 5vw, 3.8rem)', lineHeight: 1.12, letterSpacing: '-0.025em', margin: '0 0 28px', color: 'var(--brand-navy)' }}>
          <span style={{ display: 'block' }}>A network you can</span>
          <span style={{ display: 'block', color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>actually trust.</span>
        </h1>
        <p style={{ fontSize: '1.1rem', lineHeight: 1.72, color: 'var(--text-secondary)', maxWidth: 540, margin: '0 0 36px' }}>
          Multi-region nodes operated transparently from Japan. Open-source clients, audit-able pricing, real-person support — the parts you'd build yourself if you had the time.
        </p>
        <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
          <Btn variant="primary" to="/pricing">View plans</Btn>
          <Btn variant="secondary" to="/contact">Talk to us</Btn>
        </div>
        <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 22, listStyle: 'none', margin: 0, padding: 0, color: 'var(--text-muted)', fontSize: '0.86rem' }}>
          {['Operated from Japan', 'Open-source clients', 'Cancel any time', 'No tracking'].map(t => (
            <li key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--brand-gold)' }} />{t}
            </li>
          ))}
        </ul>
      </div>
      <div style={{ position: 'relative', background: '#e8f0ee', border: '1px solid var(--border)', borderRadius: 14, boxShadow: '0 1px 3px rgba(20,41,64,0.08), 0 12px 32px rgba(20,41,64,0.10), 0 32px 64px rgba(58,145,136,0.10)', overflow: 'hidden', aspectRatio: '16/11' }}>
        <img src={ASSET('hero-dashboard-v3.png')} alt="" style={{ width: '115%', height: '115%', objectFit: 'cover', objectPosition: 'center', margin: '-7.5% 0 0 -7.5%', display: 'block' }} />
      </div>
    </div>
  </section>
);

const FEATURES = [
  { n: 1, num: '01', title: 'Managed nodes', body: 'Multi-region cloud nodes maintained by us. Patches, kernel tuning, and dependency hygiene handled in the background.' },
  { n: 2, num: '02', title: 'Operator support', body: 'Real-person support for client setup, routing questions, and incident response — usually within a single business day.' },
  { n: 3, num: '03', title: 'Infrastructure care', body: 'TLS rotation, BBR tuning, automatic failover, monitoring kept current. Your service stays healthy without your effort.' },
  { n: 4, num: '04', title: 'Open-source clients', body: 'Works with v2rayN, Clash Meta, Stash, sing-box. Standard subscription URL — no custom client lock-in.' },
  { n: 5, num: '05', title: 'Multi-region', body: '14 PoPs across Asia-Pacific, North America, and Europe. Pick the location that matches your latency budget.' },
  { n: 6, num: '06', title: 'Transparent pricing', body: 'Flat subscription tiers in CNY. No hidden fees, no usage surprises. Cancel any time from the dashboard.' },
];

const FeatureGrid = () => (
  <Section id="features" bg="var(--surface)">
    <SectionHead eyebrow="Operational details" title="Six things," accent="kept simple." lead="The boring infrastructure work, handled. So you can think about anything else." />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: 22 }}>
      {FEATURES.map(f => (
        <article key={f.n} style={{ position: 'relative', padding: '28px 22px', background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <FeatureIcon n={f.n} />
          <div style={{ fontSize: '0.76rem', letterSpacing: '0.16em', color: 'var(--brand-gold)', textTransform: 'uppercase', fontWeight: 600 }}>{f.num}</div>
          <h3 style={{ margin: 0, color: 'var(--brand-navy)', fontSize: '1.06rem', fontWeight: 600 }}>{f.title}</h3>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.93rem', lineHeight: 1.65 }}>{f.body}</p>
        </article>
      ))}
    </div>
  </Section>
);

const PLANS = [
  { tag: 'Trial', name: 'Trial', price: 'Free', sub: '3 days', items: ['100 GB transfer', '3 nodes', 'Email support', 'No payment required'], cta: 'Start trial', variant: 'secondary', to: '/signup' },
  { tag: 'Monthly', name: 'Monthly', price: '¥30', sub: 'per month', items: ['500 GB transfer', 'All standard nodes', 'Standard support', 'Cancel any time'], cta: 'Subscribe', variant: 'primary', to: '/signup?plan=monthly' },
  { tag: 'Quarterly · ~11% off', name: 'Quarterly', price: '¥80', sub: 'per 3 months', items: ['1.5 TB transfer', 'All nodes incl. premium', 'Priority support', '~11% discount'], cta: 'Subscribe', variant: 'primary', to: '/signup?plan=quarterly', highlight: true },
  { tag: 'Annual · ~33% off', name: 'Annual', price: '¥240', sub: 'per year', items: ['6 TB transfer', 'All nodes incl. premium', 'Priority support', '~33% discount'], cta: 'Subscribe', variant: 'primary', to: '/signup?plan=annual', highlight: true },
];

const PricingGrid = () => (
  <Section id="pricing" bg="linear-gradient(180deg, var(--brand-cream) 0%, var(--surface-warm) 100%)">
    <SectionHead eyebrow="Pricing" title="Four tiers," accent="all the same network." lead="Choose by billing cadence. Same managed nodes, same support — longer commitments save more." />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(245px, 1fr))', gap: 22 }}>
      {PLANS.map(p => (
        <div key={p.name} style={{
          position: 'relative', padding: '44px 22px 28px',
          background: p.highlight ? 'linear-gradient(180deg, #fff 0%, var(--brand-cream-warm) 100%)' : 'var(--surface)',
          border: `1px solid ${p.highlight ? 'var(--brand-teal)' : 'var(--border-soft)'}`,
          borderRadius: 10, textAlign: 'center', boxShadow: 'var(--shadow-sm)',
        }}>
          <span style={{
            position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
            background: p.highlight ? 'var(--brand-gold)' : 'var(--brand-teal)',
            color: p.highlight ? 'var(--brand-navy)' : '#fff',
            fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
            padding: '5px 14px', borderRadius: 999, whiteSpace: 'nowrap',
          }}>{p.tag}</span>
          <h3 style={{ margin: '8px 0 14px', color: 'var(--brand-navy)', fontSize: '1.02rem', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{p.name}</h3>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '2.6rem', fontWeight: 500, color: 'var(--brand-teal)', margin: '0 0 20px', lineHeight: 1 }}>
            {p.price}
            <small style={{ display: 'block', fontFamily: 'var(--font-body)', fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 400, marginTop: 6 }}>{p.sub}</small>
          </p>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', textAlign: 'left' }}>
            {p.items.map(it => (
              <li key={it} style={{ padding: '10px 0', borderBottom: '1px solid var(--border-soft)', color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', gap: 8 }}>
                <span style={{ color: 'var(--brand-teal)', fontWeight: 700 }}>✓</span>{it}
              </li>
            ))}
          </ul>
          <Btn variant={p.variant} to={p.to} full>{p.cta}</Btn>
        </div>
      ))}
    </div>
  </Section>
);

const FAQS = [
  { q: 'How is this different from a basic VPS?', a: "A VPS gives you a blank Linux box — you install, patch, monitor, and back up everything yourself. Nilou Network gives you a managed multi-region network that's already configured, kept current, and backed by a real person you can email." },
  { q: 'Can I migrate to self-hosting later?', a: 'Yes. The clients we recommend are all open-source. We will export your config in standard formats free of charge, and our pricing pages document the rough cost of self-hosting equivalent infrastructure.' },
  { q: "What's your refund policy?", a: 'Subscriptions can be cancelled any time from your dashboard. Refunds for unused service time are processed within 7 business days of an approved request — calculated on the fraction of unused traffic and time, whichever is greater.' },
  { q: "What's your uptime target?", a: "We target 99.9% monthly uptime per region. We do not offer a contractual SLA at the current scale — we'd rather be honest about being a small operation than promise enterprise guarantees we can't keep." },
  { q: 'Where are nodes hosted?', a: 'Tokyo, Osaka, Singapore, Hong Kong, Los Angeles, San Jose, Seattle, Frankfurt, London, and four others. The full list with realtime status is on the Status page.' },
  { q: 'Do you keep traffic logs?', a: 'No. We retain only what is necessary for billing (bytes transferred, aggregated daily) and abuse mitigation (connection counts, no destinations). Connection content and destinations are not logged.' },
];

const FAQList = ({ defaultOpen = 0 }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ maxWidth: 780, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {FAQS.map((f, i) => {
        const isOpen = open === i;
        return (
          <div key={f.q} style={{
            background: 'var(--surface)',
            border: `1px solid ${isOpen ? 'var(--brand-teal)' : 'var(--border-soft)'}`,
            borderRadius: 10, overflow: 'hidden', boxShadow: isOpen ? 'var(--shadow-sm)' : 'none',
          }}>
            <button onClick={() => setOpen(isOpen ? -1 : i)} style={{
              width: '100%', textAlign: 'left', background: 'transparent', border: 0,
              padding: '18px 22px', fontWeight: 600, color: 'var(--brand-navy)',
              fontSize: '1rem', display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', gap: 16, cursor: 'pointer', fontFamily: 'var(--font-body)',
            }}>
              {f.q}
              <span style={{ color: 'var(--brand-teal)', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.18s' }}>
                <Icon name="chevronDown" size={16} />
              </span>
            </button>
            {isOpen && (
              <div style={{ padding: '0 22px 18px', color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.95rem' }}>
                <p style={{ margin: 0 }}>{f.a}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export { FeatureIcon, FEAT_GLYPHS, Hero, FeatureGrid, PricingGrid, FAQList, FAQS, PLANS, FEATURES };
