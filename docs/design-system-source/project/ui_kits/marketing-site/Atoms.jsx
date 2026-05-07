// Marketing Site UI Kit — shared atoms
// Cormorant + Inter, teal/gold/navy on cream
// Source: marketing/nilou-network/styles.css + en/index.html

const LotusMark = ({ size = 84, color = '#3a9188', breathe = false }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" aria-hidden="true"
       style={{ color, animation: breathe ? 'lotus-breathe 7s ease-in-out infinite' : 'none' }}>
    <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <g strokeOpacity="0.92">
        {[0, 45, 90, 135, 180, 225, 270, 315].map(r => (
          <path key={r} d="M100 20 C 130 50, 130 90, 100 100 C 70 90, 70 50, 100 20 Z" transform={`rotate(${r} 100 100)`} />
        ))}
      </g>
      <circle cx="100" cy="100" r="6" />
      <circle cx="100" cy="100" r="2.5" fill="currentColor" />
    </g>
  </svg>
);

const Eyebrow = ({ children }) => (
  <p style={{
    display: 'inline-block', fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.18em',
    textTransform: 'uppercase', color: 'var(--brand-gold)', margin: '0 0 24px',
    padding: '6px 14px', background: 'rgba(201, 162, 83, 0.1)', borderRadius: '999px'
  }}>{children}</p>
);

const Btn = ({ variant = 'primary', children, ...rest }) => {
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    padding: '13px 28px', borderRadius: '6px', fontWeight: 600, fontSize: '0.96rem',
    border: '2px solid transparent', cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.4, 0, 0.2, 1)', letterSpacing: '0.01em',
    textDecoration: 'none', fontFamily: 'var(--font-body)',
  };
  const variants = {
    primary: { ...base, background: 'var(--brand-teal)', color: '#fff', boxShadow: 'var(--shadow-sm)' },
    secondary: { ...base, background: 'var(--surface)', color: 'var(--brand-teal)', borderColor: 'var(--brand-teal)' },
  };
  return <a style={variants[variant]} {...rest}>{children}</a>;
};

const Divider = () => (
  <div aria-hidden="true" style={{
    height: 64,
    backgroundImage: "url('../../assets/pattern-arabesque.svg')",
    backgroundRepeat: 'repeat-x', backgroundSize: 'auto 64px', backgroundPosition: 'center',
    color: 'var(--brand-gold)', opacity: 0.4
  }} />
);

// Inline SVGs — necessary so currentColor inherits from the host page.
// (Same paths as assets/icons/feat-N.svg, kept in sync.)
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
         strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {FEAT_GLYPHS[n]}
    </svg>
  </div>
);

Object.assign(window, { LotusMark, Eyebrow, Btn, Divider, FeatureIcon });
