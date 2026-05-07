// Topbar — sticky glass header
const Topbar = ({ active = 'features' }) => (
  <header style={{
    background: 'rgba(255, 255, 255, 0.88)',
    backdropFilter: 'saturate(180%) blur(14px)',
    WebkitBackdropFilter: 'saturate(180%) blur(14px)',
    borderBottom: '1px solid var(--border-soft)',
    position: 'sticky', top: 0, zIndex: 50,
  }}>
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
      <a style={{ display: 'inline-flex', alignItems: 'center', gap: 12, fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--brand-navy)', textDecoration: 'none' }}>
        <LotusMark size={30} />
        <span>Nilou Network</span>
      </a>
      <nav style={{ display: 'flex', gap: 32, alignItems: 'center', fontSize: '0.94rem' }}>
        {['features', 'pricing', 'faq', 'about'].map(k => (
          <a key={k} href={`#${k}`} style={{
            color: active === k ? 'var(--brand-teal)' : 'var(--text-secondary)',
            fontWeight: 500, textDecoration: 'none', textTransform: 'capitalize'
          }}>{k.toUpperCase() === 'FAQ' ? 'FAQ' : k.charAt(0).toUpperCase() + k.slice(1)}</a>
        ))}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 2, padding: 3, background: 'var(--surface-alt)', border: '1px solid var(--border)', borderRadius: 6, fontSize: '0.78rem' }}>
          <a style={{ color: 'var(--brand-navy)', background: 'var(--surface)', fontWeight: 600, padding: '4px 10px', borderRadius: 4, boxShadow: 'var(--shadow-sm)', textDecoration: 'none' }}>EN</a>
          <a style={{ color: 'var(--text-muted)', fontWeight: 500, padding: '4px 10px', textDecoration: 'none' }}>日本語</a>
          <a style={{ color: 'var(--text-muted)', fontWeight: 500, padding: '4px 10px', textDecoration: 'none' }}>中文</a>
        </span>
        <a style={{ background: 'var(--brand-teal)', color: '#fff', padding: '10px 20px', borderRadius: 6, fontWeight: 600, fontSize: '0.92rem', boxShadow: 'var(--shadow-sm)', textDecoration: 'none' }}>Subscribe</a>
      </nav>
    </div>
  </header>
);

const Hero = () => (
  <section style={{
    position: 'relative', padding: '128px 0 96px',
    background: 'radial-gradient(ellipse 80% 60% at 50% 0%, var(--brand-cream-warm) 0%, transparent 60%), var(--surface)',
    overflow: 'hidden',
  }}>
    {/* Ripples */}
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

    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 24px', display: 'grid', gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)', gap: 96, alignItems: 'center', position: 'relative', zIndex: 1 }}>
      <div>
        <LotusMark size={84} breathe={true} />
        <div style={{ height: 32 }} />
        <Eyebrow>Managed hosting</Eyebrow>
        <h1 style={{
          fontFamily: 'var(--font-display)', fontWeight: 500,
          fontSize: 'clamp(2.4rem, 5vw, 3.8rem)', lineHeight: 1.12,
          letterSpacing: '-0.025em', margin: '0 0 32px', color: 'var(--brand-navy)',
        }}>
          <span style={{ display: 'block' }}>Self-hosted apps,</span>
          <span style={{ display: 'block', color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>without the self-hosting.</span>
        </h1>
        <p style={{ fontSize: '1.12rem', lineHeight: 1.72, color: 'var(--text-secondary)', maxWidth: 560, margin: '0 0 48px' }}>
          We run open-source applications on cloud infrastructure on your behalf — dashboards, monitoring tools, productivity apps. You subscribe; we handle servers, upgrades, backups, and uptime so you can focus on the work itself.
        </p>
        <div style={{ display: 'flex', gap: 16, marginBottom: 32 }}>
          <Btn variant="primary">View plans</Btn>
          <Btn variant="secondary">Talk to us</Btn>
        </div>
        <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 24, listStyle: 'none', margin: 0, padding: 0, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
          {['Operated from Japan', 'Open-source software', 'Cancel any time', 'No tracking'].map((t, i) => (
            <li key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--brand-gold)' }} />{t}
            </li>
          ))}
        </ul>
      </div>
      <div style={{
        position: 'relative', background: '#e8f0ee', border: '1px solid var(--border)',
        borderRadius: 14, boxShadow: '0 1px 3px rgba(20,41,64,0.08), 0 12px 32px rgba(20,41,64,0.10), 0 32px 64px rgba(58,145,136,0.10)',
        overflow: 'hidden', aspectRatio: '16/11'
      }}>
        <img src="../../assets/hero-dashboard-v3.png" alt="" style={{ width: '115%', height: '115%', objectFit: 'cover', objectPosition: 'center', margin: '-7.5% 0 0 -7.5%', display: 'block' }} />
      </div>
    </div>
  </section>
);

Object.assign(window, { Topbar, Hero });
