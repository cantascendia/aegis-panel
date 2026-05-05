# customer-portal

Nilou Network customer self-service portal — **P1 static visual prototype**.

> **Status**: P1 = visual + mock data only. No backend API, no real auth. The forms compile but submit to nowhere; the panel pages render mock subscription URLs / traffic / invoices.

## Why this exists

This directory implements [Constitution D-018](../docs/ai-cto/DECISIONS.md) (DRAFT, awaiting senior-engineer second sign), which overturns D-016's prior ban on a user self-service portal. The portal is staged in four phases:

| Phase | Scope | This PR? |
|---|---|---|
| **P1** | 19-page static prototype, mock data, Vite build | ✅ |
| P2 | i18n (ja/zh), JSX→TSX, Login/Signup wired to Marzneshin admin auth | ⬜ |
| P3 | Panel pages wired to real API (traffic ← Marznode gRPC, billing, tickets) | ⬜ |
| P4 | Marketing pages take over `marketing/nilou-network/{en,ja,zh}/` | ⬜ |

## Stack

- **Vite 6** + **React 18.3** + **JSX**
- **No Tailwind** — uses CSS variables from the design system (`src/styles/tokens.css`, lifted from `nilou-network-design-system/colors_and_type.css`)
- **Hash routing** (no `react-router-dom` yet — handwritten `Router` in `src/lib/Atoms.jsx`); P2 may swap in `react-router-dom`
- **Fonts** — Cormorant Garamond + Inter + JetBrains Mono via Google Fonts CDN

## Develop

```bash
pnpm install
pnpm dev          # http://localhost:5174/portal/
pnpm build        # output → dist/
pnpm preview      # serve dist/ locally
```

## Routes

| Hash | Page | Kind |
|---|---|---|
| `#/` | Home | marketing |
| `#/features` | Features | marketing |
| `#/pricing` | Pricing | marketing |
| `#/faq` | FAQ | marketing |
| `#/about` | About | marketing |
| `#/contact` | Contact | marketing |
| `#/status` | Status | marketing |
| `#/legal` | Legal · 特商法 | marketing |
| `#/login` | Sign in | auth |
| `#/signup` | Sign up | auth |
| `#/dashboard` | Dashboard | panel |
| `#/panel/nodes` | Nodes | panel |
| `#/panel/traffic` | Traffic | panel |
| `#/panel/plans` | Plans | panel |
| `#/panel/billing` | Billing | panel |
| `#/panel/tickets` | Tickets | panel |
| `#/panel/invite` | Invite | panel |
| `#/panel/account` | Account | panel |
| `#/panel/docs` | Quick start | panel |

## File structure

```
customer-portal/
├── index.html                  Vite entry — Google Fonts + #root
├── package.json
├── vite.config.js              base: '/portal/', port 5174
├── public/
│   └── assets/                 from design package — lotus.svg, arabesque, hero-dashboard PNG, feat-1..6 SVG, project-icon
└── src/
    ├── main.jsx                ReactDOM root + <Router>
    ├── App.jsx                 19-route matcher
    ├── styles/
    │   ├── tokens.css          design tokens (colors / type / spacing / shadows)
    │   └── global.css          resets + lotus-breathe / ripple keyframes
    └── lib/                    ported from design package, ES modules
        ├── Atoms.jsx           Router, Btn, Icon, Pill, StatusDot, LotusMark, Eyebrow, Divider, Link
        ├── Marketing.jsx       MarketingTopbar, MarketingFooter, Section, SectionHead
        ├── MarketingSections.jsx  Hero, FeatureGrid, PricingGrid, FAQList, FEATURES, PLANS, FAQS
        ├── MarketingPages.jsx     8 page components + Stat
        ├── AuthPages.jsx          LoginPage, SignupPage, FieldGroup, inputCss
        ├── PanelShell.jsx         PanelShell, PanelHead, Card, CardHeader, iconBtn
        ├── PanelPages1.jsx        DashboardPage, NodesPage, KPI, RingMeter, BigChart, NODES
        └── PanelPages2.jsx        TrafficPage, PlansPage, BillingPage, TicketsPage, InvitePage, AccountPage, DocsPage
```

## AGPL-3.0 compliance

The marketing footer (`src/lib/Marketing.jsx`, `MarketingFooter`) renders:

> AGPL-3.0 source-disclosure compliant — full source at github.com/cantascendia/aegis-panel

This satisfies AGPL §13 source-availability for the network-served version.

## Differences from the design prototype

The design package shipped a single-file `<script type="text/babel">` prototype with `Object.assign(window, …)` for cross-script sharing. This implementation:

| Item | Prototype | This impl |
|---|---|---|
| Module system | global vars via babel-standalone | ES modules with explicit `import`/`export` |
| React loading | unpkg CDN + babel-standalone | local `react`/`react-dom` deps, Vite-bundled |
| Asset paths | `../assets/foo.svg` | `${import.meta.env.BASE_URL}assets/foo.svg` (via `ASSET()` helper) |
| `iconBtn` collision | shadowed by re-declare | `PanelShell` exports `iconBtn`; `PanelPages1` declares local `mutedIconBtn` |
| Apostrophe in JSX text | one unescaped (`Don't`) | `&apos;` |

## Out of scope (P1)

- Real auth, real subscription URLs, real traffic data — all mock
- i18n (ja/zh) — English only
- Mobile responsive polish — tablet/desktop only in P1
- React Router DOM — handwritten hash router for P1
- Tailwind / shadcn migration — design tokens via CSS vars only
- Mock-data centralization to `src/data/mock.js` — kept inline per-file for P1 PR diff cleanliness; centralize in P2 refactor
