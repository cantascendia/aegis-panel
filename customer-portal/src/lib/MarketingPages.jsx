// Marketing pages: Home, Features, Pricing, FAQ, About, Contact, Status, Legal
import React from 'react';
import { LotusMark, Eyebrow, Btn, Icon, Pill, StatusDot, Divider } from './Atoms.jsx';
import { Section, SectionHead } from './Marketing.jsx';
import { Hero, FeatureGrid, PricingGrid, FAQList } from './MarketingSections.jsx';

const HomePage = () => (
  <>
    <Hero />
    <Divider />
    <FeatureGrid />
    <Divider />
    <Section bg="var(--surface)" pad="80px 0">
      <SectionHead eyebrow="In numbers" title="A network that" accent="adds up." />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 22 }}>
        {[
          ['14', 'PoPs across 4 continents'],
          ['99.9%', 'Monthly uptime target'],
          ['~14 ms', 'Median Tokyo→Osaka RTT'],
          ['0', 'Traffic destination logs'],
        ].map(([n, l]) => (
          <div key={n} style={{ padding: 24, border: '1px solid var(--border-soft)', borderRadius: 10, background: 'var(--surface-alt)' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '2.4rem', color: 'var(--brand-teal)', lineHeight: 1 }}>{n}</div>
            <div style={{ marginTop: 10, color: 'var(--text-secondary)', fontSize: '0.92rem' }}>{l}</div>
          </div>
        ))}
      </div>
    </Section>
    <Divider />
    <PricingGrid />
    <Divider />
    <Section id="faq" bg="var(--surface)">
      <SectionHead eyebrow="Frequently asked" title="Honest answers" accent="to honest questions." />
      <FAQList />
      <div style={{ textAlign: 'center', marginTop: 40 }}>
        <Btn variant="secondary" to="/faq">See all FAQs <Icon name="arrow" size={16} /></Btn>
      </div>
    </Section>
  </>
);

const FeaturesPage = () => (
  <>
    <Section bg="linear-gradient(180deg, var(--brand-cream-warm) 0%, var(--surface) 100%)" pad="96px 0 64px">
      <SectionHead eyebrow="What we operate" title="The work you'd do," accent="if you had the time." center />
    </Section>
    <FeatureGrid />
    <Divider />
    <Section bg="var(--surface)" pad="80px 0">
      <SectionHead eyebrow="Protocol support" title="Standard clients," accent="standard subscriptions." center />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 18 }}>
        {[
          { name: 'VMess', d: 'Legacy V2Ray protocol; AEAD ciphers required, time-fuzz for OOO clocks.' },
          { name: 'VLESS + Reality', d: 'Lightweight, no encryption layer; pairs with Reality TLS for indistinguishability.' },
          { name: 'Trojan-go', d: 'TLS 1.3 wrapper; routes failed handshakes to a real backend website.' },
          { name: 'Hysteria 2', d: 'QUIC-based, congestion-aware. Best on lossy mobile or transpacific links.' },
          { name: 'Shadowsocks', d: 'AEAD-only (chacha20-ietf-poly1305, aes-256-gcm). Single-port multi-user routing.' },
          { name: 'TUIC v5', d: 'QUIC + UDP relay. Useful when you actually need P2P or low-latency UDP.' },
        ].map(p => (
          <div key={p.name} style={{ padding: '20px 18px', border: '1px solid var(--border-soft)', borderRadius: 10, background: 'var(--surface)' }}>
            <div style={{ fontWeight: 600, color: 'var(--brand-navy)', marginBottom: 6, fontSize: '0.98rem' }}>{p.name}</div>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{p.d}</p>
          </div>
        ))}
      </div>
    </Section>
    <Divider />
    <Section bg="var(--brand-navy)" pad="72px 0">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, alignItems: 'center', color: 'var(--text-on-dark)' }}>
        <div>
          <Eyebrow color="var(--brand-gold-soft)">Compatibility</Eyebrow>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '2.2rem', color: 'var(--text-on-dark)', margin: '0 0 16px' }}>Works with the clients you already use.</h2>
          <p style={{ color: 'var(--brand-gold-soft)', opacity: 0.84, lineHeight: 1.7, margin: 0 }}>One subscription URL. Drop into v2rayN, Clash Meta, Stash, Shadowrocket, sing-box, Mihomo, FlClash. We don't ship a custom client — there's nothing for you to install but what you'd already have.</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {['v2rayN','Clash Meta','Stash','Shadowrocket','sing-box','Mihomo Party','FlClash','Hiddify'].map(c => (
            <div key={c} style={{ padding: '14px 16px', background: 'rgba(245,236,220,0.06)', border: '1px solid rgba(245,236,220,0.12)', borderRadius: 8, fontSize: '0.92rem', color: 'var(--text-on-dark)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--brand-teal-soft)' }} />{c}
            </div>
          ))}
        </div>
      </div>
    </Section>
  </>
);

const PricingPage = () => (
  <>
    <Section bg="linear-gradient(180deg, var(--brand-cream-warm) 0%, var(--surface) 100%)" pad="96px 0 48px">
      <SectionHead eyebrow="Pricing" title="Pay by cadence." accent="Same network either way." />
    </Section>
    <PricingGrid />
    <Divider />
    <Section bg="var(--surface)" pad="80px 0">
      <SectionHead eyebrow="Detailed comparison" title="Side-by-side" accent="with the fine print." center />
      <div style={{ overflowX: 'auto', border: '1px solid var(--border-soft)', borderRadius: 10 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.92rem', background: 'var(--surface)' }}>
          <thead>
            <tr style={{ background: 'var(--surface-alt)', textAlign: 'left' }}>
              {['Feature', 'Trial', 'Monthly', 'Quarterly', 'Annual'].map((h, i) => (
                <th key={h} style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--brand-navy)', borderBottom: '1px solid var(--border)', fontSize: '0.86rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['Monthly transfer','100 GB','500 GB','1.5 TB','6 TB'],
              ['Concurrent devices','3','5','5','10'],
              ['Premium nodes (low-latency, IEPL)','—','—','✓','✓'],
              ['Support response','Best-effort','Within 1 business day','Priority','Priority'],
              ['Custom routing rules','—','—','✓','✓'],
              ['API access','—','✓','✓','✓'],
              ['Effective monthly cost','—','¥30','¥27','¥20'],
            ].map((row, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-soft)' }}>
                {row.map((c, j) => (
                  <td key={j} style={{ padding: '14px 18px', color: j === 0 ? 'var(--brand-navy)' : 'var(--text-secondary)', fontWeight: j === 0 ? 600 : 400 }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 32, padding: '18px 22px', background: 'var(--surface-alt)', border: '1px solid var(--border-soft)', borderRadius: 10, color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: 1.65 }}>
        <strong style={{ color: 'var(--brand-navy)' }}>Honest note:</strong> The "effective monthly cost" math is just total ÷ months. Annual saves money only if you'd actually use the service for a year. For a trial-and-see, monthly is the better deal.
      </div>
    </Section>
    <Divider />
    <Section bg="var(--surface)">
      <SectionHead eyebrow="Payment methods" title="Whatever's" accent="convenient for you." center />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
        {['Alipay 支付宝','WeChat Pay 微信支付','Stripe / Card','PayPal','USDT (TRC-20)','Bank transfer (JP)'].map(p => (
          <div key={p} style={{ padding: 18, border: '1px solid var(--border-soft)', borderRadius: 10, textAlign: 'center', color: 'var(--brand-navy)', fontWeight: 600, fontSize: '0.94rem' }}>{p}</div>
        ))}
      </div>
    </Section>
  </>
);

const FAQPage = () => (
  <>
    <Section bg="linear-gradient(180deg, var(--brand-cream-warm) 0%, var(--surface) 100%)" pad="96px 0 48px">
      <SectionHead eyebrow="Frequently asked" title="Honest answers." accent="No corporate hedging." />
    </Section>
    <Section bg="var(--surface)" pad="0 0 88px">
      <FAQList defaultOpen={0} />
      <div style={{ textAlign: 'center', marginTop: 56, padding: '32px 24px', background: 'var(--surface-alt)', borderRadius: 10, maxWidth: 720, margin: '56px auto 0' }}>
        <h3 style={{ margin: '0 0 8px', color: 'var(--brand-navy)', fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.5rem' }}>Still wondering?</h3>
        <p style={{ margin: '0 0 20px', color: 'var(--text-secondary)' }}>Email us. A real person reads it.</p>
        <Btn variant="primary" to="/contact">Contact us</Btn>
      </div>
    </Section>
  </>
);

const AboutPage = () => (
  <>
    <Section bg="linear-gradient(180deg, var(--brand-cream-warm) 0%, var(--surface) 100%)" pad="96px 0 48px">
      <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
        <LotusMark size={64} breathe />
        <div style={{ height: 24 }} />
        <Eyebrow>About</Eyebrow>
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(2rem, 4vw, 3rem)', color: 'var(--brand-navy)', margin: '0 0 20px', letterSpacing: '-0.02em' }}>
          A small network operator,<br />
          <span style={{ color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>in plain language.</span>
        </h1>
      </div>
    </Section>
    <Section bg="var(--surface)" pad="48px 0 96px">
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <p style={{ fontSize: '1.08rem', lineHeight: 1.78, color: 'var(--text-secondary)' }}>
          Nilou Network is a single-operator 個人事業主 registered in Japan. We rent infrastructure across 14 PoPs and run open-source proxy software on top. We bill you in CNY, support you in three languages, and post our terms in plain text — including the AGPL source-disclosure notice for the software we deploy.
        </p>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.8rem', color: 'var(--brand-navy)', margin: '40px 0 16px' }}>Why we exist</h2>
        <p style={{ fontSize: '1.04rem', lineHeight: 1.78, color: 'var(--text-secondary)' }}>
          Most "airport" networks pop up overnight, run on whatever VPS panel was easiest to install, and disappear when the operator gets bored or busy. We wanted something we'd be willing to recommend to family — properly engineered, properly documented, properly accountable.
        </p>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.8rem', color: 'var(--brand-navy)', margin: '40px 0 16px' }}>Our promises, plainly</h2>
        <ul style={{ paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 14, margin: 0 }}>
          {[
            ['Transparent', "Operator name, business address, and tax ID are on the legal page. Not in a footer no one reads."],
            ['Audit-able', "All client software we recommend is open-source. Our pricing math is published. Our uptime is shown live on the Status page."],
            ["Won't disappear", "We commit to 30 days written notice before any service ends, and refunds for unused time. Always."],
            ['Privacy-respecting', "We log bytes and connection counts for billing and abuse mitigation. Connection destinations and content are not logged."],
          ].map(([t, d]) => (
            <li key={t} style={{ display: 'flex', gap: 16 }}>
              <div style={{ flexShrink: 0, width: 30, height: 30, borderRadius: '50%', background: 'rgba(58,145,136,0.12)', color: 'var(--brand-teal)', display: 'grid', placeItems: 'center' }}>
                <Icon name="check" size={14} />
              </div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--brand-navy)', marginBottom: 4 }}>{t}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.96rem', lineHeight: 1.65 }}>{d}</div>
              </div>
            </li>
          ))}
        </ul>
        <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.8rem', color: 'var(--brand-navy)', margin: '40px 0 16px' }}>The name</h2>
        <p style={{ fontSize: '1.04rem', lineHeight: 1.78, color: 'var(--text-secondary)' }}>
          Nilou is the Persian-Sumeru word for "lotus" — a flower that grows up out of muddy water without taking the mud with it. That's the brief, basically.
        </p>
      </div>
    </Section>
  </>
);

const ContactPage = () => (
  <Section bg="var(--surface)" pad="96px 0">
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <Eyebrow>Contact</Eyebrow>
      <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(2rem, 4vw, 2.6rem)', color: 'var(--brand-navy)', margin: '0 0 16px', letterSpacing: '-0.02em' }}>
        Email is the best way <span style={{ color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>to reach us.</span>
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '1.04rem', lineHeight: 1.7, margin: '0 0 40px' }}>
        We're a one-operator shop. Please don't expect instant chat — but do expect a real reply, usually inside one business day.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 40 }}>
        {[
          { icon: 'mail', l: 'General', v: 'hello@nilou.network' },
          { icon: 'shield', l: 'Abuse / takedown', v: 'abuse@nilou.network' },
          { icon: 'pin', l: 'Mailing address', v: '東京都渋谷区... (full address on Legal page)' },
        ].map(c => (
          <div key={c.l} style={{ padding: 18, border: '1px solid var(--border-soft)', borderRadius: 10 }}>
            <div style={{ color: 'var(--brand-teal)', marginBottom: 8 }}><Icon name={c.icon} size={20} /></div>
            <div style={{ fontSize: '0.78rem', letterSpacing: '0.16em', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>{c.l}</div>
            <div style={{ marginTop: 4, color: 'var(--brand-navy)', fontWeight: 500 }}>{c.v}</div>
          </div>
        ))}
      </div>
      <form onSubmit={(e) => e.preventDefault()} style={{ background: 'var(--surface-alt)', padding: 28, borderRadius: 12, border: '1px solid var(--border-soft)' }}>
        <h3 style={{ margin: '0 0 6px', color: 'var(--brand-navy)', fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 500 }}>Or send a message here</h3>
        <p style={{ margin: '0 0 22px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Goes to the same inbox.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <Field label="Your name"><input type="text" placeholder="Liu Wei" style={inputStyle} /></Field>
          <Field label="Email"><input type="email" placeholder="you@example.com" style={inputStyle} /></Field>
        </div>
        <Field label="Subject" style={{ marginTop: 14 }}>
          <select style={inputStyle}>
            <option>Pre-sales question</option><option>Billing</option><option>Technical issue</option><option>Other</option>
          </select>
        </Field>
        <Field label="Message" style={{ marginTop: 14 }}>
          <textarea rows="5" placeholder="As much detail as you can give us…" style={{ ...inputStyle, resize: 'vertical', fontFamily: 'var(--font-body)' }} />
        </Field>
        <div style={{ marginTop: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>We reply from a person, not a bot.</span>
          <Btn variant="primary" type="submit">Send message</Btn>
        </div>
      </form>
    </div>
  </Section>
);

const inputStyle = {
  width: '100%', padding: '11px 14px', borderRadius: 6, border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--brand-navy)', fontSize: '0.94rem',
  fontFamily: 'var(--font-body)', boxSizing: 'border-box', outline: 'none',
};
const Field = ({ label, children, style = {} }) => (
  <label style={{ display: 'block', ...style }}>
    <div style={{ fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>{label}</div>
    {children}
  </label>
);

const NODES_STATUS = [
  { region: 'Tokyo · NTT', host: 'tk1.nilou.network', tone: 'emerald', latency: '12 ms', uptime: '99.98%', load: 42 },
  { region: 'Tokyo · IIJ', host: 'tk2.nilou.network', tone: 'emerald', latency: '14 ms', uptime: '99.97%', load: 38 },
  { region: 'Osaka · KDDI', host: 'os1.nilou.network', tone: 'emerald', latency: '16 ms', uptime: '99.96%', load: 51 },
  { region: 'Singapore', host: 'sg1.nilou.network', tone: 'emerald', latency: '52 ms', uptime: '99.94%', load: 67 },
  { region: 'Hong Kong', host: 'hk1.nilou.network', tone: 'amber', latency: '38 ms', uptime: '99.81%', load: 84, note: 'High load · adding capacity' },
  { region: 'Los Angeles', host: 'la1.nilou.network', tone: 'emerald', latency: '108 ms', uptime: '99.95%', load: 44 },
  { region: 'San Jose · IEPL', host: 'sj1.nilou.network', tone: 'emerald', latency: '124 ms', uptime: '99.93%', load: 32 },
  { region: 'Seattle', host: 'se1.nilou.network', tone: 'emerald', latency: '118 ms', uptime: '99.96%', load: 28 },
  { region: 'Frankfurt', host: 'fr1.nilou.network', tone: 'emerald', latency: '188 ms', uptime: '99.92%', load: 19 },
  { region: 'London', host: 'lo1.nilou.network', tone: 'coral', latency: '—', uptime: '—', load: 0, note: 'Maintenance · ETA 2h' },
];

const StatusPage = () => (
  <>
    <Section bg="linear-gradient(180deg, var(--brand-cream-warm) 0%, var(--surface) 100%)" pad="96px 0 32px">
      <div style={{ maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
        <Eyebrow>Live status</Eyebrow>
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 'clamp(2rem, 4vw, 2.8rem)', color: 'var(--brand-navy)', margin: '0 0 20px', letterSpacing: '-0.02em' }}>
          All systems <span style={{ color: 'var(--brand-teal)', fontStyle: 'italic', fontWeight: 400 }}>mostly healthy.</span>
        </h1>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '10px 18px', background: 'rgba(232,176,75,0.16)', borderRadius: 999, color: '#9a6f1f', fontSize: '0.92rem', fontWeight: 500 }}>
          <StatusDot tone="amber" /> 1 region under maintenance · 1 high-load · 8 normal
        </div>
      </div>
    </Section>
    <Section bg="var(--surface)" pad="32px 0 88px">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
        {NODES_STATUS.map(n => (
          <div key={n.host} style={{ padding: 18, border: '1px solid var(--border-soft)', borderRadius: 10, background: 'var(--surface)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--brand-navy)' }}>{n.region}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{n.host}</div>
              </div>
              <StatusDot tone={n.tone} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <Stat l="Latency" v={n.latency} />
              <Stat l="30-day uptime" v={n.uptime} />
            </div>
            <div style={{ height: 6, background: 'var(--surface-alt)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ width: `${n.load}%`, height: '100%', background: n.tone === 'amber' ? 'var(--accent-amber)' : n.tone === 'coral' ? 'var(--accent-coral)' : 'var(--brand-teal)' }} />
            </div>
            <div style={{ marginTop: 8, fontSize: '0.82rem', color: 'var(--text-muted)' }}>{n.note ? n.note : `Load · ${n.load}%`}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 56 }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.5rem', color: 'var(--brand-navy)', margin: '0 0 18px' }}>Recent incidents</h3>
        <div style={{ border: '1px solid var(--border-soft)', borderRadius: 10, overflow: 'hidden' }}>
          {[
            { d: '2025-04-28', t: 'London region maintenance', s: 'Scheduled · in progress', tone: 'coral' },
            { d: '2025-04-22', t: 'Hong Kong load spike', s: 'Adding 2 nodes · ETA 36h', tone: 'amber' },
            { d: '2025-04-15', t: 'Tokyo NTT brief packet loss', s: 'Resolved · root cause: upstream peering flap', tone: 'emerald' },
            { d: '2025-04-02', t: 'Frankfurt cert auto-renewal', s: 'Resolved · LE rate-limit, manual renewal', tone: 'emerald' },
          ].map((r, i) => (
            <div key={i} style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: '120px 1fr auto', gap: 16, alignItems: 'center', borderBottom: i < 3 ? '1px solid var(--border-soft)' : 'none' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', color: 'var(--text-muted)' }}>{r.d}</div>
              <div style={{ color: 'var(--brand-navy)', fontWeight: 500 }}>{r.t}</div>
              <Pill tone={r.tone}>{r.s}</Pill>
            </div>
          ))}
        </div>
      </div>
    </Section>
  </>
);

const Stat = ({ l, v }) => (
  <div>
    <div style={{ fontSize: '0.74rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>{l}</div>
    <div style={{ marginTop: 2, color: 'var(--brand-navy)', fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.96rem' }}>{v}</div>
  </div>
);

const LegalPage = () => (
  <Section bg="var(--surface)" pad="96px 0">
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <Eyebrow>Legal · 特商法表記</Eyebrow>
      <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '2.4rem', color: 'var(--brand-navy)', margin: '0 0 24px', letterSpacing: '-0.02em' }}>Operator information</h1>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>Required disclosures under Japan's Act on Specified Commercial Transactions (特定商取引法).</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 24 }}>
        <tbody>
          {[
            ['販売業者', 'Nilou Network (個人事業主)'],
            ['運営責任者', 'A. Surname (full name on request)'],
            ['所在地', '〒150-XXXX 東京都渋谷区... (full address on request)'],
            ['連絡先', 'hello@nilou.network'],
            ['販売価格', '商品ページに記載 (CNY建て)'],
            ['支払方法', 'クレジットカード、Alipay、WeChat Pay、PayPal、USDT、銀行振込'],
            ['返品・キャンセル', '未使用分について7営業日以内に返金'],
            ['提供時期', '決済確認後ただちにアカウント発行'],
            ['動作環境', 'v2rayN, Clash Meta, Stash, Shadowrocket, sing-box, Mihomo Party'],
          ].map(([k, v]) => (
            <tr key={k} style={{ borderBottom: '1px solid var(--border-soft)' }}>
              <th style={{ padding: '14px 0', textAlign: 'left', verticalAlign: 'top', width: 200, color: 'var(--brand-navy)', fontWeight: 600, fontSize: '0.92rem' }}>{k}</th>
              <td style={{ padding: '14px 0', color: 'var(--text-secondary)', fontSize: '0.94rem', lineHeight: 1.65 }}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.5rem', color: 'var(--brand-navy)', margin: '40px 0 12px' }}>Open-source notice</h2>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>The proxy software we operate is licensed under AGPL-3.0 and similar copyleft licenses. Source for any modifications we run in production is mirrored at github.com/nilou-network and updated within 7 days of deployment, per AGPL §13.</p>
      <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: '1.5rem', color: 'var(--brand-navy)', margin: '40px 0 12px' }}>Trademark notice</h2>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>"Nilou" is also the name of a character in HoYoverse's Genshin Impact. Our service is unaffiliated; the lotus motif and name predate the game's character in Persian usage. We do not use HoYoverse artwork or branding.</p>
    </div>
  </Section>
);

export { HomePage, FeaturesPage, PricingPage, FAQPage, AboutPage, ContactPage, StatusPage, LegalPage, Stat };
