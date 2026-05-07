// Panel pages part 2: Traffic, Plans, Billing, Tickets, Invite, Account, Docs
// P2 (Wave-P1): AccountPage wired to GET /api/customers/me.
import React, { useState, useEffect } from 'react';
import { Btn, Icon, Pill } from './Atoms.jsx';
import { getMe } from './customer-api.js';
import { clearToken } from './customer-auth.js';
import { PanelShell, PanelHead, Card, CardHeader, iconBtn } from './PanelShell.jsx';
import { KPI, BigChart } from './PanelPages1.jsx';
import { PLANS } from './MarketingSections.jsx';
import { Stat } from './MarketingPages.jsx';
import { FieldGroup, inputCss } from './AuthPages.jsx';

const TrafficPage = () => (
  <PanelShell active="/panel/traffic">
    <PanelHead title="Traffic" sub="Aggregated daily totals. We don't log destinations." 
      actions={<Btn variant="secondary"><Icon name="download" size={16}/> Export CSV</Btn>} />

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 22 }}>
      <KPI label="This cycle" value="38.6 GB" sub="of 100 GB · 38%" sparkData={[12,18,16,22,28,32,38]} />
      <KPI label="Yesterday" value="4.8 GB" sub="↑ 18% vs avg" accent="gold" sparkData={[3,4,3,5,4,3,5]} />
      <KPI label="Peak day" value="5.2 GB" sub="Apr 24 · Tue" accent="emerald" />
      <KPI label="Daily avg." value="2.7 GB" sub="last 14 days" />
    </div>

    <Card style={{ marginBottom: 14 }}>
      <CardHeader title="Traffic by day" sub="Download (solid) + Upload (dashed)" />
      <div style={{ height: 280 }}><BigChart /></div>
    </Card>

    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <Card>
        <CardHeader title="By node" sub="last 7 days" />
        {[
          ['Tokyo · NTT', 12.4, '#3a9188'],
          ['Singapore', 8.6, '#5bc0be'],
          ['Hong Kong', 6.2, '#c9a253'],
          ['Los Angeles', 4.8, '#e07856'],
          ['Frankfurt', 2.1, '#1e3a5f'],
        ].map(([n, v, c]) => (
          <div key={n} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.86rem', marginBottom: 4 }}>
              <span style={{ color: 'var(--brand-navy)' }}>{n}</span>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{v} GB</span>
            </div>
            <div style={{ height: 6, background: 'var(--surface-alt)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ width: `${v / 12.4 * 100}%`, height: '100%', background: c }} />
            </div>
          </div>
        ))}
      </Card>
      <Card>
        <CardHeader title="By hour" sub="Tokyo time, last 24h" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3, height: 140, alignItems: 'end' }}>
          {Array.from({ length: 24 }).map((_, i) => {
            const v = 30 + Math.sin(i / 4) * 25 + Math.cos(i / 2.3) * 15 + (i > 18 ? 30 : 0) + (i < 4 ? -15 : 0);
            const h = Math.max(8, v);
            return <div key={i} style={{ height: `${h}%`, background: i === 21 ? 'var(--brand-gold)' : 'var(--brand-teal)', borderRadius: 2, opacity: 0.85 }} />;
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
        </div>
      </Card>
    </div>
  </PanelShell>
);

const PlansPage = () => {
  const [cadence, setCadence] = useState('quarterly');
  return (
    <PanelShell active="/panel/plans">
      <PanelHead title="Plans" sub="You're on Trial. Pick something to keep going past Day 3." />
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 22 }}>
        <div style={{ display: 'inline-flex', padding: 4, background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: 999 }}>
          {[['monthly','Monthly'],['quarterly','Quarterly · -11%'],['annual','Annual · -33%']].map(([k, l]) => (
            <button key={k} onClick={() => setCadence(k)} style={{
              padding: '8px 18px', border: 0, borderRadius: 999,
              background: cadence === k ? 'var(--brand-teal)' : 'transparent',
              color: cadence === k ? '#fff' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '0.86rem', cursor: 'pointer',
            }}>{l}</button>
          ))}
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18 }}>
        {PLANS.map(p => (
          <div key={p.name} style={{
            position: 'relative', padding: '40px 22px 26px',
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
            <h3 style={{ margin: '6px 0 12px', color: 'var(--brand-navy)', fontSize: '0.96rem', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{p.name}</h3>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '2.4rem', fontWeight: 500, color: 'var(--brand-teal)', margin: '0 0 18px', lineHeight: 1 }}>
              {p.price}<small style={{ display: 'block', fontFamily: 'var(--font-body)', fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 400, marginTop: 6 }}>{p.sub}</small>
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 22px', textAlign: 'left' }}>
              {p.items.map(it => (
                <li key={it} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-soft)', color: 'var(--text-secondary)', fontSize: '0.86rem', display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--brand-teal)', fontWeight: 700 }}>✓</span>{it}
                </li>
              ))}
            </ul>
            <Btn variant={p.variant} full>{p.cta}</Btn>
          </div>
        ))}
      </div>

      <Card style={{ marginTop: 22 }}>
        <CardHeader title="Add traffic pack" sub="One-off, no commitment. Used after your monthly quota runs out." />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          {[['50 GB', '¥10'], ['200 GB', '¥30'], ['500 GB', '¥60'], ['1 TB', '¥110']].map(([s, p]) => (
            <button key={s} style={{ padding: '14px 18px', border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 8, textAlign: 'left', cursor: 'pointer' }}>
              <div style={{ color: 'var(--brand-navy)', fontWeight: 600 }}>{s}</div>
              <div style={{ fontFamily: 'var(--font-display)', color: 'var(--brand-teal)', fontSize: '1.4rem', fontWeight: 500, marginTop: 4 }}>{p}</div>
            </button>
          ))}
        </div>
      </Card>
    </PanelShell>
  );
};

const BillingPage = () => (
  <PanelShell active="/panel/billing">
    <PanelHead title="Billing" sub="Invoices, payment methods, and renewal." />
    <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14, marginBottom: 14 }}>
      <Card>
        <CardHeader title="Current plan" sub="Trial expires in 2 days, 7 hours" action={<Btn variant="primary" to="/panel/plans">Upgrade</Btn>} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
          <Stat l="Plan" v="Trial" />
          <Stat l="Renews" v="Apr 30, 09:00" />
          <Stat l="Next charge" v="—" />
        </div>
      </Card>
      <Card>
        <CardHeader title="Payment method" action={<button style={{ ...iconBtn, color: 'var(--brand-teal)' }}><Icon name="plus" size={16}/></button>} />
        <div style={{ padding: 14, border: '1px dashed var(--border)', borderRadius: 8, color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.92rem' }}>No payment method on file. Add one before your trial ends.</div>
      </Card>
    </div>

    <Card>
      <CardHeader title="Invoice history" />
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr style={{ textAlign: 'left' }}>
            {['Invoice', 'Date', 'Description', 'Amount', 'Status', ''].map(h => (
              <th key={h} style={{ padding: '10px 0', fontSize: '0.74rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[
            ['INV-2025-0428', 'Apr 28, 2025', 'Trial activation', '¥0', 'paid', 'emerald'],
          ].map(([id, d, desc, amt, status, tone], i) => (
            <tr key={i}>
              <td style={{ padding: '14px 0', fontFamily: 'var(--font-mono)', color: 'var(--brand-navy)', fontWeight: 500 }}>{id}</td>
              <td style={{ padding: '14px 0', color: 'var(--text-secondary)' }}>{d}</td>
              <td style={{ padding: '14px 0', color: 'var(--text-secondary)' }}>{desc}</td>
              <td style={{ padding: '14px 0', fontFamily: 'var(--font-mono)', color: 'var(--brand-navy)', fontWeight: 600 }}>{amt}</td>
              <td style={{ padding: '14px 0' }}><Pill tone={tone}>{status}</Pill></td>
              <td style={{ padding: '14px 0', textAlign: 'right' }}><button style={iconBtn}><Icon name="download" size={16}/></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  </PanelShell>
);

const TicketsPage = () => (
  <PanelShell active="/panel/tickets">
    <PanelHead title="Tickets" sub="Support requests. We reply within one business day." 
      actions={<Btn variant="primary"><Icon name="plus" size={16}/> New ticket</Btn>} />
    <Card pad={0}>
      {[
        ['#1284', 'Singapore node high latency from CN', 'Reply from operator · 3h ago', 'open', 'amber'],
        ['#1273', 'Add custom routing rule', 'Resolved · 2 days ago', 'closed', 'navy'],
        ['#1265', 'Subscription not refreshing in Stash', 'Resolved · 4 days ago', 'closed', 'navy'],
      ].map(([id, t, m, s, tone], i) => (
        <div key={id} style={{ padding: '16px 22px', display: 'grid', gridTemplateColumns: '90px 1fr auto', gap: 16, alignItems: 'center', borderBottom: i < 2 ? '1px solid var(--border-soft)' : 'none' }}>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.86rem' }}>{id}</span>
          <div>
            <div style={{ color: 'var(--brand-navy)', fontWeight: 600 }}>{t}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', marginTop: 2 }}>{m}</div>
          </div>
          <Pill tone={tone}>{s}</Pill>
        </div>
      ))}
    </Card>
  </PanelShell>
);

const InvitePage = () => (
  <PanelShell active="/panel/invite">
    <PanelHead title="Invite friends" sub="Both of you save ¥10 on the next renewal." />
    <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 14 }}>
      <Card>
        <CardHeader title="Your invite link" sub="Share with friends — no limit." />
        <div style={{ padding: 14, background: 'var(--surface-alt)', borderRadius: 8, fontFamily: 'var(--font-mono)', fontSize: '0.86rem', color: 'var(--brand-navy)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <span style={{ wordBreak: 'break-all' }}>https://nilou.network/r/<span style={{ color: 'var(--brand-teal)' }}>LOTUS-LW28</span></span>
          <Btn variant="secondary" style={{ padding: '6px 12px', fontSize: '0.82rem' }}><Icon name="copy" size={14}/> Copy</Btn>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginTop: 18 }}>
          <Stat l="Invited" v="3" />
          <Stat l="Activated" v="2" />
          <Stat l="Earned" v="¥20" />
        </div>
      </Card>
      <Card>
        <CardHeader title="How it works" />
        <ol style={{ paddingLeft: 18, margin: 0, color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: 1.8 }}>
          <li>Share your link with a friend.</li>
          <li>They sign up and pay any plan.</li>
          <li>You both get ¥10 off the next renewal.</li>
        </ol>
      </Card>
    </div>
  </PanelShell>
);

/**
 * AccountPage — P2 real /me wiring (Wave-P1).
 *
 * Fetches GET /api/customers/me on mount and replaces the P1 mock username
 * and account data with real values from the backend.
 *
 * States:
 * - loading: skeleton placeholder shown while fetch is in-flight
 * - error: fallback message + re-login link (e.g. expired token → 401)
 * - data: real CustomerMeResponse fields rendered in the same Card layout
 *
 * Visual layout is PRESERVED from P1 — same grid, same Cards, same FieldGroup
 * styling. Only Profile field values and the data source changed.
 */
const AccountPage = () => {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((data) => { if (!cancelled) { setMe(data); setLoading(false); } })
      .catch((err) => {
        if (!cancelled) {
          setError(err && err.detail ? err.detail : 'Could not load your account.');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const handleLogout = () => {
    clearToken();
    window.location.hash = '/login';
  };

  const skeletonBar = (w = '60%') => (
    <div style={{ height: 16, width: w, background: 'var(--border-soft)', borderRadius: 4, marginBottom: 4 }} />
  );

  return (
    <PanelShell active="/panel/account">
      <PanelHead
        title="Account"
        sub="Profile and API access."
        actions={
          <Btn variant="ghost" onClick={handleLogout} style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
            <Icon name="logout" size={15} /> Sign out
          </Btn>
        }
      />

      {error && (
        <div
          role="alert"
          style={{
            marginBottom: 18, padding: '14px 18px', borderRadius: 8,
            background: 'rgba(224,120,86,0.10)', border: '1px solid rgba(224,120,86,0.35)',
            color: 'var(--accent-coral, #c0522e)', fontSize: '0.92rem',
          }}
        >
          {error} — <a href="#/login" style={{ color: 'inherit', fontWeight: 600 }}>Re-login</a>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        <Card>
          <CardHeader title="Profile" />
          {loading ? (
            <div style={{ padding: '8px 0' }}>
              {skeletonBar('55%')}
              {skeletonBar('75%')}
              {skeletonBar('45%')}
            </div>
          ) : (
            <>
              <FieldGroup label="Username">
                <input style={inputCss} readOnly value={me ? me.username : ''} />
              </FieldGroup>
              <FieldGroup label="Status">
                <input
                  style={inputCss}
                  readOnly
                  value={me ? (me.is_active ? 'Active' : 'Inactive') : ''}
                />
              </FieldGroup>
              {me && me.expire_date && (
                <FieldGroup label="Expires">
                  <input
                    style={inputCss}
                    readOnly
                    value={new Date(me.expire_date).toLocaleDateString()}
                  />
                </FieldGroup>
              )}
              {me && me.note && (
                <FieldGroup label="Note">
                  <input style={inputCss} readOnly value={me.note} />
                </FieldGroup>
              )}
            </>
          )}
        </Card>
        <Card>
          <CardHeader title="Data usage" />
          {loading ? (
            <div style={{ padding: '8px 0' }}>
              {skeletonBar('60%')}
              {skeletonBar('40%')}
            </div>
          ) : (
            me && (
              <>
                <FieldGroup label="Used traffic">
                  <input
                    style={inputCss}
                    readOnly
                    value={`${(me.used_traffic / 1_073_741_824).toFixed(2)} GB`}
                  />
                </FieldGroup>
                <FieldGroup label="Data limit">
                  <input
                    style={inputCss}
                    readOnly
                    value={
                      me.data_limit
                        ? `${(me.data_limit / 1_073_741_824).toFixed(2)} GB`
                        : 'Unlimited'
                    }
                  />
                </FieldGroup>
                {me.data_limit_reset_strategy && (
                  <FieldGroup label="Reset strategy">
                    <input style={inputCss} readOnly value={me.data_limit_reset_strategy} />
                  </FieldGroup>
                )}
              </>
            )
          )}
        </Card>
      </div>
      <Card>
        <CardHeader title="API access" sub="For automation and integration with your own tools." action={<Btn variant="secondary" style={{ padding: '7px 14px', fontSize: '0.84rem' }}><Icon name="plus" size={14}/> New token</Btn>} />
        <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '14px 0' }}>
          API token management coming in P3.
        </div>
      </Card>
    </PanelShell>
  );
};

const DocsPage = () => (
  <PanelShell active="/panel/docs">
    <PanelHead title="Quick start" sub="Pick your client. Three minutes to traffic." />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 22 }}>
      {['v2rayN (Win)','Clash Meta (Win)','Stash (iOS)','Shadowrocket (iOS)','Mihomo Party (Mac)','sing-box (Linux)','Hiddify (Android)','FlClash (Android)'].map((c, i) => (
        <button key={c} style={{ padding: 18, textAlign: 'left', background: i === 0 ? 'rgba(58,145,136,0.06)' : 'var(--surface)', border: `1px solid ${i === 0 ? 'var(--brand-teal)' : 'var(--border-soft)'}`, borderRadius: 10, cursor: 'pointer' }}>
          <div style={{ color: 'var(--brand-teal)', marginBottom: 8 }}><Icon name="code" size={18} /></div>
          <div style={{ fontWeight: 600, color: 'var(--brand-navy)', fontSize: '0.94rem' }}>{c}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 2 }}>3-step setup</div>
        </button>
      ))}
    </div>
    <Card>
      <CardHeader title="v2rayN — Windows" sub="Default selection. Free, open-source, GUI." />
      <ol style={{ paddingLeft: 18, margin: 0, color: 'var(--text-secondary)', fontSize: '0.94rem', lineHeight: 1.85 }}>
        <li>Download v2rayN from the official GitHub releases page. (Windows 10+ · 64-bit)</li>
        <li>Open <strong>Subscription</strong> → <strong>Subscription Settings</strong> → <strong>Add</strong>. Paste your subscription URL.</li>
        <li>Select a node from the tray menu and toggle <strong>System Proxy</strong>.</li>
      </ol>
      <div style={{ marginTop: 18, padding: 16, background: 'var(--surface-alt)', borderRadius: 8, fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--brand-navy)', wordBreak: 'break-all' }}>
        <span style={{ color: 'var(--text-muted)' }}># Your subscription URL</span><br />
        https://nilou.network/api/v1/sub/<span style={{ color: 'var(--brand-teal)' }}>a8f2d1c4-e7b9-4f3a-8c2e-9d1b5e4f7a2c</span>
      </div>
    </Card>
  </PanelShell>
);

export { TrafficPage, PlansPage, BillingPage, TicketsPage, InvitePage, AccountPage, DocsPage };
