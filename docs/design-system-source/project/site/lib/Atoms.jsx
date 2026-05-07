// Shared layout primitives and atoms used across all pages.
// Lives at site/lib/Atoms.jsx — paths assume CSS at ../../colors_and_type.css

const { useState, useEffect, useRef, createContext, useContext } = React;

// -------- Routing (hash-based, no deps) --------
const RouteContext = createContext({ path: '/', go: () => {} });

const Router = ({ children }) => {
  const [path, setPath] = useState(() => window.location.hash.slice(1) || '/');
  useEffect(() => {
    const onHash = () => setPath(window.location.hash.slice(1) || '/');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const go = (to) => { window.location.hash = to; window.scrollTo({ top: 0, behavior: 'instant' }); };
  return <RouteContext.Provider value={{ path, go }}>{children}</RouteContext.Provider>;
};

const useRoute = () => useContext(RouteContext);

const Link = ({ to, children, style, className, onClick }) => {
  const { go } = useRoute();
  return (
    <a href={`#${to}`} onClick={(e) => { e.preventDefault(); onClick && onClick(); go(to); }}
       style={{ textDecoration: 'none', ...(style || {}) }} className={className}>
      {children}
    </a>
  );
};

// -------- Lotus + brand --------
const LotusMark = ({ size = 48, color = 'var(--brand-teal)', breathe = false }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" aria-hidden="true"
       style={{ color, animation: breathe ? 'lotus-breathe 7s ease-in-out infinite' : 'none' }}>
    <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <g strokeOpacity="0.92">
        {[0,45,90,135,180,225,270,315].map(r => (
          <path key={r} d="M100 20 C 130 50, 130 90, 100 100 C 70 90, 70 50, 100 20 Z" transform={`rotate(${r} 100 100)`} />
        ))}
      </g>
      <circle cx="100" cy="100" r="6" />
      <circle cx="100" cy="100" r="2.5" fill="currentColor" />
    </g>
  </svg>
);

const Eyebrow = ({ children, color = 'var(--brand-gold)' }) => (
  <p style={{
    display: 'inline-block', fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.18em',
    textTransform: 'uppercase', color, margin: '0 0 24px',
    padding: '6px 14px', background: 'rgba(201,162,83,0.1)', borderRadius: 999
  }}>{children}</p>
);

const Btn = ({ variant = 'primary', children, to, onClick, type, style = {}, full }) => {
  const { go } = useRoute();
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: '12px 22px', borderRadius: 6, fontWeight: 600, fontSize: '0.94rem',
    border: '2px solid transparent', cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.4,0,0.2,1)', letterSpacing: '0.01em',
    textDecoration: 'none', fontFamily: 'var(--font-body)',
    width: full ? '100%' : 'auto',
  };
  const variants = {
    primary: { ...base, background: 'var(--brand-teal)', color: '#fff', boxShadow: 'var(--shadow-sm)' },
    secondary: { ...base, background: 'var(--surface)', color: 'var(--brand-teal)', borderColor: 'var(--brand-teal)' },
    ghost: { ...base, background: 'transparent', color: 'var(--text-secondary)' },
    gold: { ...base, background: 'var(--brand-gold)', color: 'var(--brand-navy)', boxShadow: 'var(--shadow-sm)' },
    dark: { ...base, background: 'var(--brand-navy)', color: 'var(--text-on-dark)' },
  };
  const handle = (e) => {
    if (onClick) onClick(e);
    if (to) { e.preventDefault(); go(to); }
  };
  if (to) {
    return <a href={`#${to}`} onClick={handle} style={{ ...variants[variant], ...style }}>{children}</a>;
  }
  return <button type={type || 'button'} onClick={handle} style={{ ...variants[variant], ...style }}>{children}</button>;
};

const Divider = () => (
  <div aria-hidden="true" style={{
    height: 64,
    backgroundImage: "url('../assets/pattern-arabesque.svg')",
    backgroundRepeat: 'repeat-x', backgroundSize: 'auto 64px', backgroundPosition: 'center',
    color: 'var(--brand-gold)', opacity: 0.4
  }} />
);

const Pill = ({ tone = 'teal', children }) => {
  const tones = {
    teal: { bg: 'rgba(58,145,136,0.12)', fg: 'var(--brand-teal-deep)' },
    gold: { bg: 'rgba(201,162,83,0.16)', fg: '#8a6a2d' },
    emerald: { bg: 'rgba(91,192,190,0.16)', fg: '#1b6f6c' },
    amber: { bg: 'rgba(232,176,75,0.18)', fg: '#9a6f1f' },
    coral: { bg: 'rgba(224,120,86,0.16)', fg: '#a04a2c' },
    navy: { bg: 'rgba(30,58,95,0.10)', fg: 'var(--brand-navy)' },
  }[tone];
  return <span style={{
    display: 'inline-flex', alignItems: 'center', gap: 6,
    background: tones.bg, color: tones.fg,
    fontSize: '0.74rem', fontWeight: 600, letterSpacing: '0.04em',
    textTransform: 'uppercase', padding: '4px 10px', borderRadius: 999,
    fontFamily: 'var(--font-body)', whiteSpace: 'nowrap',
  }}>{children}</span>;
};

const StatusDot = ({ tone = 'emerald' }) => {
  const c = { emerald: '#5bc0be', amber: '#e8b04b', coral: '#e07856', muted: '#8a96b0' }[tone];
  return <span style={{
    width: 8, height: 8, borderRadius: '50%', background: c,
    boxShadow: tone === 'emerald' ? `0 0 0 3px ${c}26` : 'none', display: 'inline-block', flexShrink: 0,
  }} />;
};

// Inline icon system (currentColor)
const Icon = ({ name, size = 18 }) => {
  const paths = {
    home: <><path d="M3 11l9-7 9 7v9a2 2 0 0 1-2 2h-3.5v-6h-7v6H5a2 2 0 0 1-2-2z" /></>,
    nodes: <><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="6" cy="18" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8.5 6h7M8.5 18h7M6 8.5v7M18 8.5v7" /></>,
    chart: <><path d="M3 20h18" /><path d="M5 16l4-4 3 3 6-7" /><circle cx="5" cy="16" r="1.4" fill="currentColor" /><circle cx="9" cy="12" r="1.4" fill="currentColor" /><circle cx="12" cy="15" r="1.4" fill="currentColor" /><circle cx="18" cy="8" r="1.4" fill="currentColor" /></>,
    tag: <><path d="M3 12V4h8l10 10-8 8z" /><circle cx="7.5" cy="7.5" r="1.5" /></>,
    receipt: <><path d="M5 3v18l2-1.5 2 1.5 2-1.5 2 1.5 2-1.5 2 1.5 2-1.5V3z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    ticket: <><path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z" /><path d="M14 6v12" strokeDasharray="2 2" /></>,
    user: <><circle cx="12" cy="8.5" r="3.5" /><path d="M5 20c1-4 4-6 7-6s6 2 7 6" /></>,
    book: <><path d="M4 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4z" /><path d="M20 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z" /></>,
    bell: <><path d="M6 9a6 6 0 0 1 12 0v4l1.5 3h-15L6 13z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
    search: <><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    check: <><path d="M5 12.5l4 4 10-10" /></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></>,
    download: <><path d="M12 4v12M6 11l6 6 6-6M4 20h16" /></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8" /><path d="M21 4v4h-4" /><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16" /><path d="M3 20v-4h4" /></>,
    logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /><path d="M10 8l-4 4 4 4M6 12h11" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></>,
    shield: <><path d="M12 2.5L4 6v6c0 4.5 3.4 8.6 8 9.5 4.6-0.9 8-5 8-9.5V6z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></>,
    globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3c2.8 3 4.2 6 4.2 9s-1.4 6-4.2 9c-2.8-3-4.2-6-4.2-9s1.4-6 4.2-9z" /></>,
    chevronDown: <><path d="M6 9l6 6 6-6" /></>,
    chevronRight: <><path d="M9 6l6 6-6 6" /></>,
    qr: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><path d="M14 14h3v3h-3zM18 18h3M14 21h3" /></>,
    key: <><circle cx="8" cy="14" r="4" /><path d="M11 12l9-9M17 5l3 3M14 8l3 3" /></>,
    heart: <><path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.7A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" /></>,
    rss: <><path d="M5 5a14 14 0 0 1 14 14M5 12a7 7 0 0 1 7 7" /><circle cx="6" cy="18" r="1.5" fill="currentColor" /></>,
    code: <><path d="M9 8l-5 4 5 4M15 8l5 4-5 4M14 5l-4 14" /></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3.5 7l8.5 6 8.5-6" /></>,
    pin: <><path d="M12 21s-7-7.5-7-12a7 7 0 0 1 14 0c0 4.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.5" /></>,
    flame: <><path d="M12 3s5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 1-3s-1 5 2 5 1.5-4 1.5-5C11.5 7 12 3 12 3z" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name] || null}
    </svg>
  );
};

Object.assign(window, { Router, useRoute, Link, RouteContext, LotusMark, Eyebrow, Btn, Divider, Pill, StatusDot, Icon, useState, useEffect, useRef });
