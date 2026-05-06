// Marketing-site shell: Topbar + Footer used across marketing pages.
import React from 'react';
import { useRoute, Link, LotusMark, Eyebrow, Btn } from './Atoms.jsx';

const MarketingTopbar = () => {
  const { path } = useRoute();
  const items = [
    { to: '/features', label: 'Features' },
    { to: '/pricing', label: 'Pricing' },
    { to: '/faq', label: 'FAQ' },
    { to: '/about', label: 'About' },
    { to: '/status', label: 'Status' },
  ];
  return (
    <header style={{
      background: 'rgba(255,255,255,0.88)', backdropFilter: 'saturate(180%) blur(14px)',
      WebkitBackdropFilter: 'saturate(180%) blur(14px)',
      borderBottom: '1px solid var(--border-soft)', position: 'sticky', top: 0, zIndex: 50,
    }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
        <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 12, fontSize: '1.08rem', fontWeight: 700, color: 'var(--brand-navy)' }}>
          <LotusMark size={28} />
          <span>Nilou Network</span>
        </Link>
        <nav style={{ display: 'flex', gap: 28, alignItems: 'center', fontSize: '0.92rem' }}>
          {items.map(it => (
            <Link key={it.to} to={it.to} style={{
              color: path === it.to ? 'var(--brand-teal)' : 'var(--text-secondary)',
              fontWeight: 500, padding: '4px 0',
              borderBottom: path === it.to ? '2px solid var(--brand-teal)' : '2px solid transparent',
            }}>{it.label}</Link>
          ))}
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 2, padding: 3, background: 'var(--surface-alt)', border: '1px solid var(--border)', borderRadius: 6, fontSize: '0.76rem' }}>
            <a style={{ color: 'var(--brand-navy)', background: 'var(--surface)', fontWeight: 600, padding: '3px 9px', borderRadius: 4, boxShadow: 'var(--shadow-sm)' }}>EN</a>
            <a style={{ color: 'var(--text-muted)', fontWeight: 500, padding: '3px 9px' }}>日本語</a>
            <a style={{ color: 'var(--text-muted)', fontWeight: 500, padding: '3px 9px' }}>中文</a>
          </span>
          <Link to="/login" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Sign in</Link>
          <Btn variant="primary" to="/signup" style={{ padding: '9px 18px', fontSize: '0.88rem' }}>Subscribe</Btn>
        </nav>
      </div>
    </header>
  );
};

const MarketingFooter = () => (
  <footer style={{ background: 'var(--brand-navy)', color: 'var(--text-on-dark)', padding: '64px 0 40px', borderTop: '3px solid var(--brand-teal)' }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr 1fr', gap: 32, marginBottom: 48 }}>
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--text-on-dark)', fontWeight: 700, fontSize: '1.04rem', marginBottom: 12 }}>
            <LotusMark size={24} color="var(--brand-gold-soft)" />
            <span>Nilou Network</span>
          </div>
          <p style={{ fontSize: '0.88rem', lineHeight: 1.65, color: 'var(--brand-gold-soft)', opacity: 0.78, margin: 0, maxWidth: 280 }}>
            Managed open-source apps, operated from Japan. Audit-able infrastructure that won't disappear on you.
          </p>
        </div>
        {[
          { h: 'Product', items: [['Features','/features'], ['Pricing','/pricing'], ['Status','/status']] },
          { h: 'Company', items: [['About','/about'], ['Contact','/contact'], ['Legal & 特商法','/legal']] },
          { h: 'Resources', items: [['FAQ','/faq'], ['Open-source notice','/legal'], ['Trademark','/legal']] },
          { h: 'Languages', items: [['English','/'], ['日本語','/'], ['中文','/']] },
        ].map(col => (
          <div key={col.h}>
            <h4 style={{ fontSize: '0.74rem', fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--brand-gold-soft)', margin: '0 0 14px', fontFamily: 'var(--font-body)' }}>{col.h}</h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {col.items.map(([t, to]) => (
                <li key={t}><Link to={to} style={{ color: 'var(--text-on-dark)', fontSize: '0.9rem', opacity: 0.82 }}>{t}</Link></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div style={{ paddingTop: 24, borderTop: '1px solid rgba(245,236,220,0.12)', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, fontSize: '0.78rem', color: 'var(--brand-gold-soft)', opacity: 0.7 }}>
        <span>© 2025 Nilou Network · 個人事業主 in Japan</span>
        <span>
          AGPL-3.0 — source at{' '}
          <a
            href="https://github.com/cantascendia/aegis-panel"
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--brand-gold-soft)', textDecoration: 'underline' }}
          >
            github.com/cantascendia/aegis-panel
          </a>
        </span>
      </div>
    </div>
  </footer>
);

const Section = ({ id, children, bg, pad = '96px 0' }) => (
  <section id={id} style={{ background: bg || 'var(--surface)', padding: pad }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px' }}>{children}</div>
  </section>
);

const SectionHead = ({ eyebrow, title, accent, lead, center = true }) => (
  <div style={{ textAlign: center ? 'center' : 'left', maxWidth: center ? 760 : '100%', margin: center ? '0 auto 56px' : '0 0 40px' }}>
    {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
    <h2 style={{
      fontFamily: 'var(--font-display)', fontWeight: 500,
      fontSize: 'clamp(1.9rem, 3.4vw, 2.6rem)', letterSpacing: '-0.02em',
      color: 'var(--brand-navy)', margin: '0 0 16px', lineHeight: 1.2,
    }}>{title}{accent && <> <span style={{ color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>{accent}</span></>}</h2>
    {lead && <p style={{ color: 'var(--text-secondary)', fontSize: '1.06rem', margin: 0, lineHeight: 1.65 }}>{lead}</p>}
  </div>
);

export { MarketingTopbar, MarketingFooter, Section, SectionHead };
