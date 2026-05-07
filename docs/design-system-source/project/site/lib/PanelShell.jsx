// Panel shell — sidebar + topbar + page wrapper for the user dashboard.

const PanelShell = ({ active, children }) => {
  const { go } = useRoute();
  const nav = [
    { to: '/dashboard', icon: 'home', label: 'Dashboard' },
    { to: '/panel/nodes', icon: 'nodes', label: 'Nodes' },
    { to: '/panel/traffic', icon: 'chart', label: 'Traffic' },
    { to: '/panel/plans', icon: 'tag', label: 'Plans' },
    { to: '/panel/billing', icon: 'receipt', label: 'Billing' },
    { to: '/panel/tickets', icon: 'ticket', label: 'Tickets' },
    { to: '/panel/invite', icon: 'heart', label: 'Invite' },
    { to: '/panel/account', icon: 'user', label: 'Account' },
  ];
  const docs = [
    { to: '/panel/docs', icon: 'book', label: 'Quick start' },
    { to: '/status', icon: 'rss', label: 'Status' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '256px 1fr', minHeight: '100vh', background: 'var(--surface-alt)' }}>
      <aside style={{ background: 'var(--surface)', borderRight: '1px solid var(--border-soft)', padding: '20px 14px', position: 'sticky', top: 0, height: '100vh', overflowY: 'auto' }}>
        <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '6px 10px 22px', color: 'var(--brand-navy)', fontWeight: 700, fontSize: '1.02rem' }}>
          <LotusMark size={26} />
          <span>Nilou Network</span>
        </Link>
        <NavGroup title="Workspace" items={nav} active={active} />
        <NavGroup title="Resources" items={docs} active={active} />
        <div style={{ marginTop: 32, padding: 14, background: 'linear-gradient(135deg, var(--brand-cream) 0%, var(--brand-cream-warm) 100%)', borderRadius: 10, border: '1px solid var(--border-soft)' }}>
          <div style={{ fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--brand-gold)', fontWeight: 600 }}>Trial</div>
          <div style={{ marginTop: 6, color: 'var(--brand-navy)', fontSize: '0.9rem', lineHeight: 1.5 }}>2 days, 7 hours remaining</div>
          <Btn variant="primary" to="/panel/plans" style={{ marginTop: 12, padding: '8px 14px', fontSize: '0.84rem', width: '100%' }}>Upgrade</Btn>
        </div>
      </aside>
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <PanelTopbar />
        <main style={{ flex: 1, padding: '28px 36px 56px' }}>{children}</main>
      </div>
    </div>
  );
};

const NavGroup = ({ title, items, active }) => (
  <div style={{ marginBottom: 18 }}>
    <div style={{ padding: '8px 12px', fontSize: '0.7rem', letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>{title}</div>
    <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {items.map(it => {
        const isActive = active === it.to;
        return (
          <Link key={it.to} to={it.to} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 6,
            color: isActive ? 'var(--brand-teal)' : 'var(--text-secondary)',
            background: isActive ? 'rgba(58,145,136,0.08)' : 'transparent',
            fontWeight: isActive ? 600 : 500, fontSize: '0.92rem',
            borderLeft: `3px solid ${isActive ? 'var(--brand-teal)' : 'transparent'}`,
            paddingLeft: 9,
          }}>
            <Icon name={it.icon} size={18} />
            <span>{it.label}</span>
          </Link>
        );
      })}
    </nav>
  </div>
);

const PanelTopbar = () => {
  const [open, setOpen] = useState(false);
  return (
    <header style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border-soft)', padding: '14px 36px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, position: 'sticky', top: 0, zIndex: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-muted)', flex: 1, maxWidth: 460, padding: '8px 12px', background: 'var(--surface-alt)', borderRadius: 8, border: '1px solid var(--border-soft)' }}>
        <Icon name="search" size={16} />
        <input placeholder="Search nodes, tickets, invoices…" style={{ flex: 1, border: 0, background: 'transparent', outline: 'none', color: 'var(--brand-navy)', fontFamily: 'var(--font-body)', fontSize: '0.92rem' }} />
        <kbd style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: 'var(--text-muted)', background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 4, padding: '2px 6px' }}>⌘K</kbd>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button style={iconBtn}><Icon name="bell" size={18} /></button>
        <button style={iconBtn}><Icon name="globe" size={18} /></button>
        <div style={{ height: 24, width: 1, background: 'var(--border-soft)' }} />
        <button onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'transparent', border: 0, cursor: 'pointer', padding: 4 }}>
          <span style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, var(--brand-teal) 0%, var(--brand-teal-deep) 100%)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: '0.86rem' }}>LW</span>
          <span style={{ textAlign: 'left' }}>
            <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--brand-navy)' }}>Liu Wei</div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Trial · ID #28104</div>
          </span>
          <Icon name="chevronDown" size={14} />
        </button>
      </div>
    </header>
  );
};
const iconBtn = { background: 'transparent', border: 0, color: 'var(--text-secondary)', cursor: 'pointer', padding: 6, display: 'grid', placeItems: 'center', borderRadius: 6 };

const PanelHead = ({ title, sub, actions }) => (
  <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
    <div>
      <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.9rem', color: 'var(--brand-navy)', letterSpacing: '-0.02em' }}>{title}</h1>
      {sub && <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: '0.96rem' }}>{sub}</p>}
    </div>
    {actions && <div style={{ display: 'flex', gap: 10 }}>{actions}</div>}
  </div>
);

const Card = ({ children, pad = 22, style = {} }) => (
  <div style={{ background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 10, padding: pad, ...style }}>{children}</div>
);
const CardHeader = ({ title, sub, action }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
    <div>
      <h3 style={{ margin: 0, color: 'var(--brand-navy)', fontWeight: 600, fontSize: '1rem' }}>{title}</h3>
      {sub && <div style={{ marginTop: 2, color: 'var(--text-muted)', fontSize: '0.84rem' }}>{sub}</div>}
    </div>
    {action}
  </div>
);

Object.assign(window, { PanelShell, PanelHead, Card, CardHeader, iconBtn });
