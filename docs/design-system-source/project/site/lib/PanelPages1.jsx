// Panel pages: Dashboard, Nodes, Traffic, Plans, Billing, Tickets, Invite, Account, Docs

const Sparkline = ({ data, color = 'var(--brand-teal)', h = 36, fill = true }) => {
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const w = 120;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" style={{ display: 'block' }}>
      {fill && <polygon points={`0,${h} ${pts} ${w},${h}`} fill={color} opacity="0.12" />}
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

const KPI = ({ label, value, sub, trend, sparkData, accent = 'teal' }) => {
  const colors = { teal: 'var(--brand-teal)', gold: 'var(--brand-gold)', emerald: 'var(--accent-emerald)', coral: 'var(--accent-coral)' };
  return (
    <Card pad={20}>
      <div style={{ fontSize: '0.74rem', letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 500, color: 'var(--brand-navy)', marginTop: 4, lineHeight: 1.05 }}>{value}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <span style={{ fontSize: '0.84rem', color: trend === 'down' ? 'var(--accent-coral)' : 'var(--brand-teal-deep)' }}>{sub}</span>
      </div>
      {sparkData && <div style={{ marginTop: 10 }}><Sparkline data={sparkData} color={colors[accent]} /></div>}
    </Card>
  );
};

const DashboardPage = () => (
  <PanelShell active="/dashboard">
    <PanelHead title="Welcome back, Liu Wei" sub="Your network is operating normally. 2 days, 7 hours left on trial."
      actions={<><Btn variant="secondary" to="/panel/docs"><Icon name="book" size={16}/> Quick start</Btn><Btn variant="primary" to="/panel/plans">Upgrade plan</Btn></>} />

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 22 }}>
      <KPI label="Used this cycle" value="38.6 GB" sub="↑ 12% vs last week" sparkData={[12,18,16,22,28,32,38]} />
      <KPI label="Remaining" value="61.4 GB" sub="of 100 GB · 61%" accent="gold" sparkData={[88,82,84,78,72,68,61]} />
      <KPI label="Active devices" value="3" sub="of 3 allowed" />
      <KPI label="Avg. latency" value="34 ms" sub="Tokyo → SG · 24h" accent="emerald" sparkData={[28,30,32,34,36,33,34]} />
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14, marginBottom: 22 }}>
      <Card>
        <CardHeader title="Traffic, last 14 days" sub="Upload + download, daily totals"
          action={<div style={{ display: 'flex', gap: 4, padding: 3, background: 'var(--surface-alt)', borderRadius: 6, fontSize: '0.78rem' }}>
            {['7d','14d','30d'].map((t, i) => <button key={t} style={{ padding: '4px 10px', border: 0, borderRadius: 4, background: i === 1 ? 'var(--surface)' : 'transparent', color: i === 1 ? 'var(--brand-navy)' : 'var(--text-muted)', fontWeight: i === 1 ? 600 : 500, cursor: 'pointer' }}>{t}</button>)}
          </div>} />
        <div style={{ height: 220, position: 'relative', padding: '0 8px' }}>
          <BigChart />
        </div>
      </Card>
      <Card>
        <CardHeader title="Quota" sub="Resets May 1, 00:00 JST" />
        <RingMeter percent={61} label="61.4 GB" sub="of 100 GB" />
        <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Row a="Download" b="32.4 GB" />
          <Row a="Upload" b="6.2 GB" />
          <Row a="Avg. per day" b="2.7 GB" />
        </div>
      </Card>
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <Card>
        <CardHeader title="Subscription URL" sub="Drop into your client" action={<Btn variant="secondary" style={{ padding: '6px 12px', fontSize: '0.82rem' }}><Icon name="copy" size={14}/> Copy</Btn>} />
        <div style={{ padding: 12, background: 'var(--surface-alt)', borderRadius: 8, fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--brand-navy)', wordBreak: 'break-all', lineHeight: 1.55, border: '1px solid var(--border-soft)' }}>
          https://nilou.network/api/v1/sub/<span style={{ color: 'var(--brand-teal)' }}>a8f2d1c4-e7b9-4f3a-8c2e-9d1b5e4f7a2c</span>?flag=clash
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
          {['Clash','sing-box','v2rayN','Shadowrocket','Stash'].map((c, i) => (
            <button key={c} style={{ padding: '6px 12px', fontSize: '0.82rem', borderRadius: 6, border: `1px solid ${i === 0 ? 'var(--brand-teal)' : 'var(--border-soft)'}`, background: i === 0 ? 'rgba(58,145,136,0.08)' : 'var(--surface)', color: i === 0 ? 'var(--brand-teal)' : 'var(--text-secondary)', fontWeight: 500, cursor: 'pointer' }}>{c}</button>
          ))}
        </div>
      </Card>
      <Card>
        <CardHeader title="Recent activity" />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {[
            ['Subscription synced', 'Clash Meta · 3 nodes returned', '4 min ago', 'emerald'],
            ['Login from new device', 'iPhone 15 · Tokyo', '2 hours ago', 'amber'],
            ['Trial started', '100 GB · 3 days', '17 hours ago', 'teal'],
            ['Account created', 'liu.wei@nilou-demo.network', '17 hours ago', 'navy'],
          ].map(([t, s, d, tone], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 0', borderBottom: i < 3 ? '1px solid var(--border-soft)' : 'none' }}>
              <span style={{ marginTop: 6 }}><StatusDot tone={tone} /></span>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--brand-navy)', fontSize: '0.92rem', fontWeight: 500 }}>{t}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>{s}</div>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{d}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  </PanelShell>
);

const Row = ({ a, b }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.86rem' }}>
    <span style={{ color: 'var(--text-muted)' }}>{a}</span>
    <span style={{ color: 'var(--brand-navy)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{b}</span>
  </div>
);

const RingMeter = ({ percent, label, sub }) => {
  const r = 56, c = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', display: 'grid', placeItems: 'center', padding: '12px 0' }}>
      <svg width="160" height="160" viewBox="0 0 160 160" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--border-soft)" strokeWidth="10" />
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--brand-teal)" strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - percent / 100)} />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 500, color: 'var(--brand-navy)', lineHeight: 1 }}>{label}</div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>
      </div>
    </div>
  );
};

const BigChart = () => {
  // generate plausible 14-day data
  const dl = [2.1, 2.8, 1.6, 3.2, 2.4, 1.9, 4.1, 3.8, 2.9, 3.4, 4.6, 3.1, 5.2, 4.8];
  const ul = [0.4, 0.6, 0.3, 0.5, 0.5, 0.4, 0.7, 0.6, 0.5, 0.6, 0.8, 0.5, 0.9, 0.7];
  const max = Math.max(...dl) * 1.15;
  const w = 100, h = 100;
  const x = (i) => (i / (dl.length - 1)) * w;
  const y = (v) => h - (v / max) * h;
  const path = dl.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ');
  const upath = ul.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ');
  const fill = `M 0 ${h} ${dl.map((v, i) => `L ${x(i)} ${y(v)}`).join(' ')} L ${w} ${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="100%" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id="dlg" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#3a9188" stopOpacity="0.32" />
          <stop offset="100%" stopColor="#3a9188" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0,25,50,75,100].map(p => <line key={p} x1="0" x2={w} y1={h*p/100} y2={h*p/100} stroke="var(--border-soft)" strokeWidth="0.3" />)}
      <path d={fill} fill="url(#dlg)" />
      <path d={path} fill="none" stroke="#3a9188" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
      <path d={upath} fill="none" stroke="#c9a253" strokeWidth="1.2" strokeDasharray="3 2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
};

// ---- Nodes page ----
const NODES = [
  { tag: 'JP', region: 'Tokyo · NTT', host: 'tk1.nilou.network', proto: 'VLESS+Reality', mult: '1x', tone: 'emerald', latency: 12, load: 42, premium: false },
  { tag: 'JP', region: 'Tokyo · IIJ', host: 'tk2.nilou.network', proto: 'Hysteria2', mult: '1x', tone: 'emerald', latency: 14, load: 38, premium: false },
  { tag: 'JP', region: 'Osaka · KDDI', host: 'os1.nilou.network', proto: 'Trojan-go', mult: '1x', tone: 'emerald', latency: 16, load: 51, premium: false },
  { tag: 'JP', region: 'Tokyo · IEPL → CN', host: 'tk-iepl1', proto: 'VLESS+Reality', mult: '1.5x', tone: 'emerald', latency: 28, load: 22, premium: true },
  { tag: 'SG', region: 'Singapore', host: 'sg1.nilou.network', proto: 'VLESS+Reality', mult: '1x', tone: 'emerald', latency: 52, load: 67, premium: false },
  { tag: 'HK', region: 'Hong Kong', host: 'hk1.nilou.network', proto: 'Hysteria2', mult: '1.5x', tone: 'amber', latency: 38, load: 84, premium: true },
  { tag: 'US', region: 'Los Angeles', host: 'la1.nilou.network', proto: 'VLESS+Reality', mult: '1x', tone: 'emerald', latency: 108, load: 44, premium: false },
  { tag: 'US', region: 'San Jose · IEPL', host: 'sj1.nilou.network', proto: 'Trojan-go', mult: '2x', tone: 'emerald', latency: 124, load: 32, premium: true },
  { tag: 'US', region: 'Seattle', host: 'se1.nilou.network', proto: 'TUIC v5', mult: '1x', tone: 'emerald', latency: 118, load: 28, premium: false },
  { tag: 'EU', region: 'Frankfurt', host: 'fr1.nilou.network', proto: 'VLESS+Reality', mult: '1x', tone: 'emerald', latency: 188, load: 19, premium: false },
  { tag: 'EU', region: 'London', host: 'lo1.nilou.network', proto: 'Trojan-go', mult: '1x', tone: 'coral', latency: null, load: 0, premium: false, note: 'Maintenance' },
  { tag: 'TW', region: 'Taipei', host: 'tw1.nilou.network', proto: 'Hysteria2', mult: '1x', tone: 'emerald', latency: 34, load: 41, premium: false },
];

const NodesPage = () => {
  const [filter, setFilter] = useState('all');
  const filtered = filter === 'all' ? NODES : NODES.filter(n => n.tag === filter);
  return (
    <PanelShell active="/panel/nodes">
      <PanelHead title="Nodes" sub="12 nodes across 4 regions. Premium nodes (1.5x and up) require Quarterly or Annual."
        actions={<><Btn variant="secondary"><Icon name="refresh" size={16}/> Sync</Btn><Btn variant="primary"><Icon name="download" size={16}/> Subscription URL</Btn></>} />

      <Card pad={0} style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 4, padding: 14, borderBottom: '1px solid var(--border-soft)', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {[
              ['all', 'All', 12], ['JP', 'Japan', 4], ['SG', 'Singapore', 1], ['HK', 'Hong Kong', 1], ['TW', 'Taiwan', 1], ['US', 'United States', 3], ['EU', 'Europe', 2],
            ].map(([k, l, n]) => (
              <button key={k} onClick={() => setFilter(k)} style={{
                padding: '7px 12px', border: 0, borderRadius: 6, background: filter === k ? 'rgba(58,145,136,0.10)' : 'transparent',
                color: filter === k ? 'var(--brand-teal)' : 'var(--text-secondary)', fontWeight: filter === k ? 600 : 500, cursor: 'pointer',
                fontSize: '0.86rem', display: 'inline-flex', alignItems: 'center', gap: 6,
              }}>{l}<span style={{ fontSize: '0.74rem', color: filter === k ? 'var(--brand-teal-deep)' : 'var(--text-muted)' }}>{n}</span></button>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: '0.84rem' }}>
            <Icon name="search" size={14} /><input placeholder="Filter…" style={{ border: 0, background: 'transparent', outline: 'none', fontFamily: 'var(--font-body)', fontSize: '0.86rem', width: 120 }} />
          </div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ background: 'var(--surface-alt)', textAlign: 'left' }}>
              {['Region', 'Hostname', 'Protocol', 'Mult.', 'Latency', 'Load', ''].map((h, i) => (
                <th key={h+i} style={{ padding: '11px 18px', fontSize: '0.74rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((n, i) => (
              <tr key={n.host} style={{ borderBottom: i < filtered.length - 1 ? '1px solid var(--border-soft)' : 'none' }}>
                <td style={{ padding: '14px 18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <StatusDot tone={n.tone} />
                    <div>
                      <div style={{ color: 'var(--brand-navy)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {n.region}
                        {n.premium && <Pill tone="gold">Premium</Pill>}
                      </div>
                      {n.note && <div style={{ fontSize: '0.78rem', color: 'var(--accent-coral)', marginTop: 2 }}>{n.note}</div>}
                    </div>
                  </div>
                </td>
                <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{n.host}</td>
                <td style={{ padding: '14px 18px', color: 'var(--text-secondary)' }}>{n.proto}</td>
                <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', color: n.mult === '1x' ? 'var(--text-muted)' : 'var(--brand-gold)', fontWeight: 600 }}>{n.mult}</td>
                <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', color: 'var(--brand-navy)' }}>{n.latency ? `${n.latency} ms` : '—'}</td>
                <td style={{ padding: '14px 18px', minWidth: 140 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 5, background: 'var(--surface-alt)', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{ width: `${n.load}%`, height: '100%', background: n.tone === 'amber' ? 'var(--accent-amber)' : n.tone === 'coral' ? 'var(--accent-coral)' : 'var(--brand-teal)' }} />
                    </div>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', width: 30, textAlign: 'right' }}>{n.load}%</span>
                  </div>
                </td>
                <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                  <button style={iconBtn}><Icon name="copy" size={16}/></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </PanelShell>
  );
};
const iconBtn = { background: 'transparent', border: 0, color: 'var(--text-muted)', cursor: 'pointer', padding: 6, display: 'inline-grid', placeItems: 'center', borderRadius: 6 };

Object.assign(window, { DashboardPage, NodesPage, KPI, Sparkline, RingMeter, BigChart, NODES });
