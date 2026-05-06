# SPEC: customer-portal-p2

**Status**: DRAFT — awaiting CTO review + senior engineer second sign per §32.1 / §37.3.
**Owner**: spec-planner (Claude Opus 4.7) → CTO seal pending.
**Created**: 2026-05-06.
**Authority**: D-018 (DECISIONS.md, ACTIVE 2026-05-06, double-signed).
**Reliability surface**: `docs/ai-cto/PORTAL-RELIABILITY.md` §1, §2, §4, §5 (P2 scope).
**Forbidden-path triggers**: `customer-portal/src/lib/AuthPages.jsx` (§32.1) — this PR series is `requires-double-review` + needs golden trajectory eval (`.claude/rules/eval-gate.md`).
**Estimated effort**: 7–10 person-days (~1.5 weeks at 20–30 h/week part-time CONSTITUTION cadence). Split across 3 sub-PRs (P2.1 / P2.2 / P2.3).

---

## CTO Pre-Seal Notes (2026-05-06)

> 本段是 CTO 对 spec-planner 草稿的初轮 review。把 10 个 TBD 分成"CTO 单独可签"和"必须用户 + senior 双签"两堆,加快 P2.1 启动节奏(技术 TBD 可立即 SEAL,业务 TBD 等用户)。

### TBD CTO 倾向 SEAL(技术决策,推荐随 SPEC 一并签)

| TBD | 决策 | CTO 立场 |
|---|---|---|
| TBD-1 | TSX strictness graduated | ✅ SEAL — full strict 在 P1 mock data 上炸 ~50 false-positive,graduated 是务实选择 |
| TBD-2 | Token localStorage | ✅ SEAL — backend Bearer header 无 cookie 的路径下,localStorage 是唯一不需后端改的方案;XSS 风险已在 R-2 文档化 |
| TBD-3 | i18n single namespace | ✅ SEAL — dashboard 模式已验证 5 年,无理由分叉 |
| TBD-4 | react-router-dom v6 HashRouter | ✅ SEAL — 闭环 PORTAL-RELIABILITY §5 row 4(query-string),手写 router 维护成本 > 标准库收益 |
| TBD-5 | `<RequireAuth>` wrapper | ✅ SEAL — 单元可测 + 与 v6 `<Route element>` 习语一致 |
| TBD-7 | 3 sub-PRs 顺序 | ✅ SEAL — 单会话 + 顺序减小 worktree 冲突(L-018);TSX → i18n → Auth 拓扑正确 |
| TBD-9 | Marketing 翻译只做 skeleton | ✅ SEAL — P4 重写,P2 全译浪费;锁 panel + auth 全译,marketing 留 TODO 标记 |

### TBD 必须用户 + senior engineer 决策(不 CTO 单签)

| TBD | 决策 | 为什么不能 CTO 单签 |
|---|---|---|
| **TBD-6** | Auth scope option A / B / C | 🔴 privilege 架构,触及 §32.1 forbidden;Option A 满足 D-018 字面但实际上仅 staging 可用 — **用户必须明确"P2 不接真实终端用户登录"**,否则有 R-1 暴雷风险 |
| TBD-8 | Translation labor source | 💰 成本/时间权衡(自译 vs 外包 vs DeepL),CTO 无权代决预算 |
| TBD-10 | Mutation testing tool | 🔧 跨项目工具选型(dashboard/portal 共用),用户 stack 决策 |

### CTO 已识别但 SPEC 未充分覆盖的隐患

1. **D-018 与现实的张力**:D-018 文本说 P2 = "Login/Signup 接 admin auth",但合理理解后只能是 Option A(admin 内测);如果用户原意是"真实用户也能用",则 P2 实际等于 Option B(新建 User 表),需要修订 D-018 范围。**用户决策前不能进 P2.3。**
2. **AGPL footer 在 panel 页(已登录态)的可见性**:R-5 提到了 marketing footer + panel footer + login page,但 panel sidebar 是 sticky 不滚动,如果 footer 只在底部、用户从来不滚到底,实际上看不到源码链接 — 需 P2.3 补一个 sidebar 底部的 ⓘ 图标 hover 显示源码链接。
3. **token 续期 UX 缺**:60 分钟后用户在 #/panel/billing 中途填表 → 令牌过期,表单数据丢失。R-7 提到 redirect 但没说"保留中途填写的表单数据"。P2.3 视情况加 `localStorage.setItem('draft_<page>', ...)` 兜底,或显式接受"60 分钟内必须完成"。
4. **i18n 中"Trial"/"Plan tier"等品牌术语**:dashboard 6 语言里这些术语已有翻译,P2 应当 grep 复用,避免又造一套术语表(L-039 documentation drift 风险)。

### 推荐节奏

- 即刻:用户决策 TBD-6 / TBD-8 / TBD-10 → SPEC SEALED → 启动 P2.1
- 7 个技术 TBD 连同 SPEC 一并签:用户单独"OK 技术 TBD 全签"即可
- P2.1(TSX) 不依赖任何 TBD 内容,可在 SPEC SEAL 当天启动

---

## 0. Context

### 0.1 Trigger event

D-018 (2026-05-06) recorded:

> "P2(后续 PR):i18n (ja/zh) + JSX→TSX + Login/Signup 接 Marzneshin admin auth(复用现有 JWT/cookie)"

P1 shipped as PR #240 (commit `5d43be5`, "feat(customer-portal): P1 static prototype — 19 pages visual + mock data"). With P1 land, P2 is next in the four-phase plan. PORTAL-RELIABILITY (§0 table) marks P2 in scope for §1 (panel API failure modes — partial; only auth surface), §2 (full auth failure semantics), §4 (error boundaries — P2 must fix), §5 (silent-failure routes — P2 starts the migration to react-router-dom + query strings).

### 0.2 Current project stage

Per STATUS.md (most recent merges) the project is in Phase B商业化 (200+ paid users target). Customer-portal P1 is the first user-facing surface; until P2 ships, panel routes are unguarded mock-only and cannot accept real users. Other Phase-B threads (RBAC SPEC `D-019`, audit-log `D-018-audit`, EPay/TRC20 billing `D-010`, AGPL self-check `D-017`) are independent and proceed in parallel sessions.

### 0.3 P1 baseline (ground truth from recon)

- **Stack**: Vite 6 + React 18.3 + **JSX (not TS)** + pnpm. Port 5174, base `/portal/`.
- **Routing**: handwritten hash router in `customer-portal/src/lib/Atoms.jsx` (`Router` / `useRoute` / `Link`). Does **not** parse query strings — `#/signup?plan=monthly` arrives at the router with literal path `"/signup?plan=monthly"`. PORTAL-RELIABILITY §5 row 4 flags this for P2 fix.
- **Files** (10 source files, all `.jsx`):
  - `src/main.jsx`, `src/App.jsx`
  - `src/lib/Atoms.jsx` — Router, primitives, icons
  - `src/lib/Marketing.jsx`, `MarketingPages.jsx`, `MarketingSections.jsx` — 8 marketing pages (P4 will replace `marketing/nilou-network/` with these)
  - `src/lib/AuthPages.jsx` — LoginPage, SignupPage (forbidden path)
  - `src/lib/PanelShell.jsx` — sidebar/topbar layout
  - `src/lib/PanelPages1.jsx`, `PanelPages2.jsx` — 9 panel pages incl. BillingPage (forbidden path, P3 trigger)
- **Auth state**: `LoginPage` `onSubmit` → `e.preventDefault(); go('/dashboard')` (`AuthPages.jsx:50`). Pure mock. **No auth guard** on `#/dashboard` or `#/panel/*` — anyone can access.
- **i18n**: single English locale; copy is hardcoded inline. No i18n library installed.
- **No Tailwind / shadcn**: pure CSS variables in `src/styles/tokens.css`.
- **Mock data**: hardcoded UUID subscription URL, `LOTUS-LW28` invite code, etc. (PORTAL-RELIABILITY §5 rows 2–3 — those are P3 fixes; out of P2 scope).

### 0.4 Backend admin auth (already exists — recon ground truth)

| Aspect | Value |
|---|---|
| Token endpoint | `POST /api/admins/token` (`app/routes/admin.py:68`) |
| Payload | OAuth2PasswordRequestForm (`username`, `password` form fields — **not JSON**) |
| Response shape | `{access_token: str, is_sudo: bool, token_type: "bearer"}` (`app/models/admin.py:25`) |
| Token alg | HS256 |
| TTL | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 60 min (`app/config/env.py:67`) |
| Claims | `{sub, access: "admin"\|"sudo", iat, exp}` (`app/utils/auth.py:12`) |
| Refresh token | **none** — `.env` comment "deferred to P3" (`app/config/env.py:62`) |
| Logout endpoint | **none** — client discards token |
| Bearer header | `Authorization: Bearer <access_token>` |
| Rate limit | `RATE_LIMIT_ADMIN_LOGIN`, default `"5/minute"` (slowapi + Redis) |
| JWT secret | `.env` `JWT_SECRET_KEY` (deprecated DB fallback exists) |
| Auth guards | `AdminDep`, `SudoAdminDep` (`app/dependencies.py:19-50`) |

### 0.5 Dashboard i18n pattern (mirror this)

- Library: `react-i18next` 14.1.3 + `i18next-browser-languagedetector` + `i18next-http-backend`.
- Init: `dashboard/src/features/i18n/index.ts` (57 lines). 8 langs in dashboard; portal needs only `en, ja, zh-cn` for P2.
- Locale files: `dashboard/public/locales/<lang>.json` flat per-language file (no namespaces).
- Detection order: `['localStorage', 'sessionStorage', 'cookie', 'navigator']`.
- Switcher: `dashboard/src/features/language-switch/index.tsx` calls `i18n.changeLanguage()`.

### 0.6 Related history & lessons

- D-016 (推翻 by D-018): original "no user portal" decision; D-018 documents the conditions under which D-016 was overturned, and lists推翻 conditions (≥3 customer requests for self-service, etc.). P2 is the first commitment under the new D-018 regime.
- D-005: SPEC-driven template — this SPEC follows postgres-redis SPEC structure.
- D-008 / D-006: Redis is opt-in; `RATE_LIMIT_ENABLED=false` default. Portal login UI must surface 429 cleanly (PORTAL-RELIABILITY §2 row 2). If a deployment runs without Redis, admin login rate-limit is disabled — portal must NOT assume 429 will ever fire.
- L-018 (worktree isolation): a P2.1/P2.2/P2.3 sub-PR series can run in a single session (sequential) or each in its own worktree (parallel). Recommend sequential under one session because they share the TSX scaffolding.
- §32.1 forbidden paths: `AuthPages.jsx` is listed; PR series must carry `requires-double-review` label and have a golden-trajectory eval (`.claude/rules/eval-gate.md`).

---

## 1. What

P2 ships **three sub-deliverables** plus reliability scaffolding, in three sub-PRs:

### 1.1 Deliverable A — JSX → TSX migration (sub-PR P2.1)

**In scope**:
- Convert all 10 `.jsx` source files in `customer-portal/src/` to `.tsx` (or `.ts` for non-JSX modules — none currently).
- Add `tsconfig.json` with **graduated strictness** (TBD-1 below; recommend `noImplicitAny: true`, `strictNullChecks: false` for P2; full `strict: true` for P3).
- Add `@types/react`, `@types/react-dom` devDeps; pin Vite 6 React plugin TS support.
- Type the `Router` / `useRoute` / `Link` / `Btn` / `Pill` / `Icon` / `LotusMark` / etc. exports in `Atoms.tsx` with `interface` declarations (no `any` for component props).
- Type the mock data shapes (Plan, Node, Invoice, Ticket) — these become the contracts P3 backend must honour.
- Update `vite.config.js` → `vite.config.ts`. Keep `base: '/portal/'` and dev port 5174.
- Update `package.json` build scripts: `tsc --noEmit && vite build` (typecheck before bundle).
- Add `pnpm typecheck` script and CI step (extend `.github/workflows/customer-portal.yml` if it exists, or create one mirroring dashboard's).

**Out of scope**:
- Logic changes (this is a pure rename + type annotation pass).
- Renaming exports or restructuring file boundaries.
- Tailwind / shadcn migration (CSS variables stay).
- Splitting `PanelPages1.tsx` / `PanelPages2.tsx` into per-page files (P3 candidate).

### 1.2 Deliverable B — i18n (sub-PR P2.2)

**In scope**:
- Install `react-i18next`, `i18next`, `i18next-browser-languagedetector`, `i18next-http-backend` (mirror dashboard versions exactly).
- Create `customer-portal/src/features/i18n/index.ts` modeled on `dashboard/src/features/i18n/index.ts`.
- Three locale files: `customer-portal/public/locales/en.json`, `ja.json`, `zh-cn.json`. Single `translation` namespace (mirror dashboard, see TBD-3).
- Extract every hardcoded UI string from the 10 source files into i18n keys. Estimated ~250–400 keys. Use dot-namespaced keys (`auth.login.title`, `panel.dashboard.kpi.dataUsed`, `marketing.hero.headline`).
- `LanguageSwitcher` component in topbar (panel) + footer (marketing). Mirror `dashboard/src/features/language-switch/index.tsx` minimally — three-flag dropdown.
- Detection order: `['localStorage', 'navigator']` (no cookie/sessionStorage in portal — simpler).
- Fallback chain: `ja` → `en`, `zh-cn` → `en` (PORTAL-RELIABILITY §6 row "no half-language UI").
- HTML `lang` attribute updated on `i18n.changeLanguage()`.

**Out of scope**:
- Translating BillingPage / TicketsPage / NodesPage **mock data strings** that will be replaced by API responses in P3 (e.g., plan names from API). Keep those English-only for now and add an `// i18n-skip-mock` comment.
- RTL support (no Arabic / Hebrew / Persian — different from dashboard which has fa/ar/ckb/kur).
- Marketing pages full translation (P4 might replace these wholesale; for P2 only translate panel + auth thoroughly, marketing gets EN keys + ja/zh skeleton with TODO markers).
- Pluralization rules beyond i18next defaults.

### 1.3 Deliverable C — Auth wiring (sub-PR P2.3)

**Recommended option: A** (admin-only login, see §4 Risks for full discussion).

**In scope (option A)**:
- `LoginPage` form posts to `POST /api/admins/token` as `application/x-www-form-urlencoded` with `username` + `password` fields.
- On 200: store `{access_token, is_sudo, expires_at}` in `localStorage` under key `aegis_portal_admin_token` (TBD-2: alternative is sessionStorage; recommend localStorage with explicit XSS-risk doc).
- On 401: show "Email or password incorrect" — do NOT distinguish (PORTAL-RELIABILITY §2 row 1).
- On 429: show "Too many attempts. Wait 60s." with a 60s countdown + disabled submit (PORTAL-RELIABILITY §2 row 2). Read `Retry-After` header if present.
- On 5xx / network error: show "Sign-in temporarily unavailable. Try again in a moment." Form not submitted.
- `SignupPage` stays a **mock** in P2 (option A) — show a banner "Sign-up not yet available — contact your operator" or hide the route entirely behind `VITE_PORTAL_SIGNUP_ENABLED=false` (default false).
- Logout: clear `localStorage` key + `go('/login')` (server has no logout endpoint).
- Auth guard: `<RequireAuth>` wrapper component (TBD-5: vs route-level HOC — recommend wrapper). Wraps every panel route (`#/dashboard`, `#/panel/*`). On no token / expired token, redirects to `#/login?next=<intended-path>` (PORTAL-RELIABILITY §2 row 4). Note: `?next=` requires the new react-router-dom — see Deliverable D below.
- Token expiry detection: client-side check `exp` claim before each API call; on expiry redirect to login with `?reason=expired&next=<path>`.
- Privilege banner: if `is_sudo === true`, show a small persistent banner in the panel "Admin/Sudo session — internal-only access" so operators don't forget they're logged in with elevated creds (mitigates Risk R-1 below).
- Document in `customer-portal/README.md` that P2 is **internal/staging only** until P3 builds the user table.

**Out of scope (option A)**:
- New `User` table or `/api/users/token` endpoint (deferred to P3 SPEC).
- Real signup / email verification / password reset (deferred to P3).
- OAuth providers (the existing P1 mock buttons "Google" / "GitHub" become hidden behind `VITE_PORTAL_OAUTH_ENABLED=false`, default false).
- Refresh token (backend doesn't have it — P3 deferral per `.env` comment).
- CSRF — bearer-header auth doesn't need CSRF as long as we never accept cookie auth.

### 1.4 Deliverable D — Router upgrade + auth guard scaffolding (folded into P2.3)

**In scope**:
- Swap handwritten hash Router (`Atoms.tsx`) for `react-router-dom` v6 `HashRouter` (TBD-4: vs keep handwritten + add query parser — recommend swap).
- Re-export a thin `useRoute()` shim that adapts `useNavigate()` + `useLocation()` so existing call sites in `PanelPages1.tsx` / `MarketingPages.tsx` keep working without 19-page refactor.
- Replace `Link` from `Atoms.tsx` with `react-router-dom` `<Link>` (one-line export swap).
- Add `useSearchParams()` consumers in SignupPage (`?plan=monthly`) and LoginPage (`?next=...&reason=expired`).
- Apply `<RequireAuth>` wrapper in route table (consolidate route definitions, currently scattered in `App.tsx`).

**Out of scope**:
- BrowserRouter (would require nginx rewrite rules — defer to P4 when marketing takes over).
- Lazy route loading (`React.lazy` + `Suspense`) — small bundle, defer.

### 1.5 Deliverable E — Error boundary scaffolding (folded into P2.3, PORTAL-RELIABILITY §4)

**In scope**:
- App-level `<ErrorBoundary>` wrapping the entire `<RouterProvider>` — catches unrecoverable errors with full-page fallback "Something didn't load right. The team has been notified. Refresh or contact support."
- PanelShell-level `<ErrorBoundary>` wrapping the `<Outlet />` in `PanelShell.tsx` so a single page crash doesn't take out the sidebar/topbar.
- Telemetry stub: `logBoundaryError(error, info)` that for now `console.error`s + buffers in localStorage (key `aegis_portal_errors`, FIFO cap 20). P3 wires this to a real endpoint. Do **not** integrate Google Analytics (PORTAL-RELIABILITY §4 explicit prohibition; conflicts with privacy stance).
- Unit test that throws in a panel page and asserts only that page's boundary catches (sidebar still rendered).

**Out of scope**:
- Sentry / PostHog / Plausible integration (P3, after telemetry SPEC exists).
- Source-mapped error reports.

---

## 2. Why

| Deliverable | User-visible value | Operator value |
|---|---|---|
| A. TSX | None directly | Type safety prevents class of bugs (mistyped prop, missing field on mock data); enables IDE refactor in P3 when API shapes change; aligns with dashboard tooling for shared mental model |
| B. i18n (en/ja/zh-cn) | Japanese + Simplified Chinese users see native UI, lowering support load for ~95% of D-010 target market | Per D-010 (~70% Chinese users), the JP market is the second-largest target; English-only blocks adoption with both groups |
| C. Auth wiring | Operators (admin-tier) can finally log into the portal in staging/preview environments to validate panel UX before P3 backend wiring | Removes the embarrassing "anyone can `#/dashboard`" privilege leak; satisfies D-018's literal P2 scope; unblocks PORTAL-RELIABILITY §2 contract finalization |
| D. Router swap | Refresh on `#/signup?plan=monthly` no longer drops the plan; `?next=` survives the login bounce; future deep-links to `#/panel/billing?invoice=N` work | Standard library = fewer custom-router bugs; community-tested edge cases (back/forward, scroll restoration) come free |
| E. Error boundaries | A single bad render no longer whitescreens the entire portal; user sees a recoverable message | Operator gets visibility into runtime errors before customers complain; lays groundwork for telemetry SPEC in P3 |

**Cost of not shipping P2**: every additional week the portal is unguarded mock-only delays D-018's推翻 condition window ("6-month <10% usage triggers re-eval"). P3 cannot start without P2's TSX foundation + auth guard scaffolding.

**Alignment with VISION**:商业化机场 with 200+ users requires self-service UI that renders correctly in ja/zh-cn. P2 is the minimum viable skeleton.

---

## 3. How (architecture, not implementation)

### 3.1 PR sequence (sequential, not parallel)

```
main
 └── feat/customer-portal-p2-1-tsx    (P2.1 — TSX migration, ~1-2 d)
      └── feat/customer-portal-p2-2-i18n   (P2.2 — i18n, ~2-3 d)
           └── feat/customer-portal-p2-3-auth  (P2.3 — auth + router + boundaries, ~3-4 d)
                → merge to main (final P2 land)
```

Sequential because:
- P2.2 keys and components are easier to extract from already-typed TSX.
- P2.3 RequireAuth needs typed routes; without P2.1, the wrapper signature would be untyped.
- A single session running all three avoids worktree contention (L-018).

Each sub-PR carries:
- `requires-double-review` label (P2.3 only — that's where AuthPages.tsx changes live, §32.1).
- A delta golden-trajectory eval YAML in `evals/golden-trajectories/` (P2.3 must add ≥1 case covering "Login form submits to /api/admins/token, on 401 stays on /login with error message"; per `.claude/rules/eval-gate.md`).

### 3.2 File-level plan

#### P2.1 — TSX migration

| Old path | New path | Action |
|---|---|---|
| `customer-portal/src/main.jsx` | `main.tsx` | Rename + add types |
| `src/App.jsx` | `App.tsx` | Rename + type route table |
| `src/lib/Atoms.jsx` | `lib/Atoms.tsx` | Rename + export typed components; Router becomes a re-export of react-router-dom (P2.3) but in P2.1 keep handwritten and just type it |
| `src/lib/AuthPages.jsx` | `lib/AuthPages.tsx` | Rename + type form state — **forbidden path triggers in P2.3 not P2.1** because P2.1 doesn't change behavior |
| `src/lib/PanelShell.jsx` | `lib/PanelShell.tsx` | Rename + type sidebar config |
| `src/lib/PanelPages1.jsx` | `lib/PanelPages1.tsx` | Rename + define `MockUsage`, `MockNode`, `MockTraffic` interfaces |
| `src/lib/PanelPages2.jsx` | `lib/PanelPages2.tsx` | Rename + define `MockInvoice`, `MockTicket`, `MockReferral` interfaces; **forbidden-path trigger because BillingPage lives here** — P2.1 keeps mock so technically PR is mechanical, but still warrants `requires-double-review` because the file path matches `.claude/rules/forbidden-paths.md` |
| `src/lib/Marketing.jsx` | `lib/Marketing.tsx` | Rename |
| `src/lib/MarketingPages.jsx` | `lib/MarketingPages.tsx` | Rename |
| `src/lib/MarketingSections.jsx` | `lib/MarketingSections.tsx` | Rename |
| `vite.config.js` | `vite.config.ts` | Rename |
| (new) | `tsconfig.json` | Graduated strict |
| (new) | `tsconfig.node.json` | For Vite config |

#### P2.2 — i18n

```
customer-portal/
├── public/
│   └── locales/
│       ├── en.json     ← extracted strings, ~250-400 keys
│       ├── ja.json     ← translated (operator/contracted translator)
│       └── zh-cn.json  ← translated
├── src/
│   ├── features/
│   │   ├── i18n/
│   │   │   └── index.ts  ← mirrors dashboard/src/features/i18n/index.ts
│   │   └── language-switch/
│   │       └── index.tsx ← three-flag dropdown
```

Key namespacing scheme (single `translation` namespace per TBD-3):
- `auth.login.*`, `auth.signup.*` (~30 keys)
- `panel.dashboard.*`, `panel.nodes.*`, `panel.traffic.*`, `panel.plans.*`, `panel.billing.*`, `panel.tickets.*`, `panel.invite.*`, `panel.account.*`, `panel.help.*` (~150 keys)
- `panel.shell.sidebar.*`, `panel.shell.topbar.*` (~20 keys)
- `marketing.hero.*`, `marketing.features.*`, `marketing.pricing.*`, etc. (~80 keys for 8 marketing pages — minimal, since P4 may replace)
- `common.button.*`, `common.error.*`, `common.unit.*` (~30 keys)

#### P2.3 — auth + router + boundaries

```
customer-portal/src/
├── features/
│   ├── auth/
│   │   ├── api.ts         ← postLogin(username, password) → bearer token
│   │   ├── storage.ts     ← localStorage get/set/clear, JWT exp parse
│   │   ├── RequireAuth.tsx ← <RequireAuth>{children}</RequireAuth> wrapper
│   │   └── useAuth.ts     ← hook: { token, isSudo, isAuthed, login, logout }
│   └── error-boundary/
│       ├── AppErrorBoundary.tsx
│       ├── PanelErrorBoundary.tsx
│       └── telemetry.ts    ← logBoundaryError() stub
├── lib/
│   └── AuthPages.tsx       ← LoginPage now calls useAuth().login()
└── App.tsx                 ← RouterProvider + AppErrorBoundary + RequireAuth wrappers
```

Concrete API contract (P2.3 client side):

```typescript
// features/auth/api.ts
async function postLogin(username: string, password: string): Promise<LoginResult> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE}/api/admins/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (res.status === 200) return { ok: true, ...(await res.json()) };
  if (res.status === 401) return { ok: false, kind: 'invalid' };
  if (res.status === 429) return { ok: false, kind: 'rate-limited', retryAfter: parseRetryAfter(res) };
  if (res.status >= 500) return { ok: false, kind: 'server' };
  return { ok: false, kind: 'unknown' };
}
```

Auth guard mechanism (TBD-5, recommend wrapper):

```tsx
// App.tsx route table
<Routes>
  <Route path="/" element={<MarketingHome />} />
  <Route path="/login" element={<LoginPage />} />
  <Route element={<RequireAuth><PanelShell /></RequireAuth>}>
    <Route path="/dashboard" element={<DashboardPage />} />
    <Route path="/panel/nodes" element={<NodesPage />} />
    {/* ... */}
  </Route>
</Routes>
```

### 3.3 Environment variables introduced

| Var | Default | Purpose |
|---|---|---|
| `VITE_PORTAL_API_BASE` | `''` (same-origin) | Override API base URL for cross-origin staging |
| `VITE_PORTAL_SIGNUP_ENABLED` | `false` | P2 hides signup; P3 flips to `true` |
| `VITE_PORTAL_OAUTH_ENABLED` | `false` | Hides Google/GitHub mock buttons |
| `VITE_PORTAL_API_MOCK` | `true` | PORTAL-RELIABILITY §5 row 1 — granular mock toggle (panel pages still mock in P2; P3 flips per-endpoint) |
| `VITE_PORTAL_DEFAULT_LOCALE` | `en` | Override detection |

These are documented in `customer-portal/.env.example` (new file in P2.3) and `customer-portal/README.md`.

---

## 4. Risks

### R-1 (CRITICAL) Privilege leakage from admin-scope tokens

**Description**: D-018 says "Login/Signup 接 Marzneshin admin auth (复用现有 JWT/cookie)". Marzneshin admin tokens carry `access: "admin" | "sudo"` claim; these are operator credentials with full panel privileges (Marznode access, billing admin, audit log read). If end-users get admin-scope tokens, they have full panel privileges.

**Mitigation (option A path, recommended)**:
- Document P2 as **internal/staging only** — explicitly in `customer-portal/README.md` and login page footer.
- `VITE_PORTAL_SIGNUP_ENABLED=false` default — no real signup possible.
- Persistent banner in panel UI when `is_sudo === true`.
- Backend `/api/admins/token` continues to require pre-provisioned admin accounts; no self-registration path → end-users cannot get tokens.
- P3 SPEC must build separate `User` table + `/api/users/token` before public launch.

**Residual risk**: An operator could share admin credentials with a real user; that's an operator-discipline issue, not a code issue. Document it.

**Alternative options (rejected for P2)**:
- **Option B**: Build `User` table + `/api/users/token` in P2 — adds 2-3 weeks; D-018 didn't authorize a new auth surface; would need a CONSTITUTION amendment.
- **Option C**: Postpone auth wiring entirely to P3 — fails D-018 literal scope; leaves portal unguarded for the entire P2 → P3 window (~4-6 weeks).

### R-2 Token leak via XSS (localStorage)

**Description**: localStorage is XSS-readable; an attacker injecting `<script>` would read the bearer token.

**Mitigation**:
- React's default escaping handles 99% of common injection; no `dangerouslySetInnerHTML` in current portal code (verified via `grep`).
- CSP header can be added at nginx level (P3 ops work, not P2 code).
- Bearer header (not cookie) means an XSS attacker can read the token but cannot CSRF without it.
- Document the trade-off in `features/auth/storage.ts` module docstring.

**Alternative**: httpOnly cookie. Rejected because Marzneshin admin endpoint returns a bearer token in JSON, not a Set-Cookie header — switching to cookies would require backend change which is out of P2 scope.

### R-3 Hash router → react-router-dom migration breakage

**Description**: 19 pages call `useRoute()`; if the shim doesn't perfectly match the old API, pages break.

**Mitigation**:
- Keep the `useRoute()` name and signature `{ path, go }` — implement as a thin wrapper over `useNavigate()` + `useLocation()`.
- Run the existing visual regression manually before merging P2.3 (each of the 19 routes loads, sidebar Link clicks navigate, browser back/forward works).
- Add a smoke test (vitest + RTL) that mounts `<App />` and asserts each route renders.

### R-4 i18n key drift between en/ja/zh-cn

**Description**: Adding a key to `en.json` but forgetting `ja.json` / `zh-cn.json` — runtime shows raw key.

**Mitigation**:
- CI step: `pnpm i18n:check` script that diffs key sets across the three files; fails on missing keys.
- i18next `fallbackLng: 'en'` so missing key in ja/zh-cn shows English (not raw key) — matches PORTAL-RELIABILITY §6 "no half-language UI" principle (English-only is acceptable; raw key is not).
- Translation labor is the bottleneck, not technical (~250 keys × 2 langs = ~500 strings; ~1-2 days operator time or ~1 day contracted translator).

### R-5 AGPL-3.0 compliance regression

**Description**: D-002 / D-018 / D-017 require portal footer to link to public source. P2 must preserve this.

**Mitigation**:
- `MarketingSections.tsx` footer already has source link in P1 (verify in P2.1 retype).
- Panel footer (PanelShell.tsx) must also have a `/source` link — add if missing.
- AGPL self-check (`deploy/agpl-selfcheck.sh` from D-017) should treat `customer-portal/dist/` as in-scope.

### R-6 Forbidden-path double-review backlog

**Description**: P2.3 touches `customer-portal/src/lib/AuthPages.tsx` (§32.1). Without senior engineer second sign + golden-trajectory eval, the PR cannot merge to main.

**Mitigation**:
- Add `evals/golden-trajectories/customer-portal-p2-auth.yaml` covering: (a) login 200 happy path, (b) login 401 stays on /login with error, (c) login 429 disables button + countdown, (d) RequireAuth redirects unauth to /login?next=/dashboard, (e) logout clears storage + redirects, (f) is_sudo banner renders when claim present.
- Reviewer checklist included in PR description (per `.claude/rules/forbidden-paths.md` "Spec-Driven" requirement; this SPEC IS that artifact).
- Mutation testing target ≥80% on `features/auth/*.ts` per `.claude/rules/forbidden-paths.md` "测试覆盖" rule. Use Stryker (mirror dashboard tooling) or equivalent.

### R-7 Token expiry UX confusion

**Description**: 60-min TTL — user mid-task will get bumped to login; if `?next=` doesn't work, they lose state.

**Mitigation**:
- `?next=<intended-path>` survives bounce (PORTAL-RELIABILITY §2 row 4 contract).
- Pre-emptive client-side check: if exp < now + 5 min, show non-blocking banner "Session expires soon — re-login to avoid interruption."
- Clear error: redirect to `/login?reason=expired&next=<path>` so banner copy can differentiate "session expired" from "first login."

### R-8 Backend admin login rate-limit dependency

**Description**: D-006 — `RATE_LIMIT_ENABLED=false` default. If the deployment runs without Redis, no 429 response will ever fire from `/api/admins/token`. Brute-force attempts on the portal login become unbounded.

**Mitigation**:
- Document in `customer-portal/README.md` that production deployments MUST set `RATE_LIMIT_ENABLED=true` + `REDIS_URL`.
- Portal frontend cannot enforce rate limits (client-side limits are bypassable). This is a backend deployment concern, not P2 scope, but flag it.
- Add a deploy-time check in `deploy/agpl-selfcheck.sh` or a new `deploy/portal-precheck.sh` (P3 candidate) that warns if portal is enabled but `RATE_LIMIT_ENABLED=false`.

### R-9 React-router-dom HashRouter quirk

**Description**: HashRouter does not support `?` in the URL path the same way BrowserRouter does. Query strings live in `location.search` parsed from the hash fragment.

**Mitigation**:
- Use `useSearchParams()` from react-router-dom v6 — handles HashRouter quirks correctly.
- Add explicit test that `#/login?next=/dashboard&reason=expired` parses both params.

---

## 5. Acceptance Criteria

A. **TSX (P2.1)**:
- [ ] All 10 source files renamed `.tsx`, no `.jsx` remains under `customer-portal/src/`.
- [ ] `pnpm typecheck` passes with `noImplicitAny: true`.
- [ ] `pnpm build` produces identical-or-smaller `dist/` size vs P1 baseline.
- [ ] CI pipeline added: `pnpm typecheck && pnpm build` runs on PR touching `customer-portal/**`.
- [ ] No runtime behavior change — visual smoke of all 19 routes confirms identical UI.

B. **i18n (P2.2)**:
- [ ] Three locale files exist: `en.json`, `ja.json`, `zh-cn.json`.
- [ ] Key parity: `pnpm i18n:check` reports zero missing keys across all three.
- [ ] Language switcher renders in topbar + footer; clicking changes UI language and persists in localStorage.
- [ ] HTML `<html lang="...">` updates on language change.
- [ ] Fallback verified: deleting a key from `ja.json` shows English text (not raw key).
- [ ] Detection: visiting with browser language `ja-JP` and empty localStorage defaults to `ja`.

C. **Auth wiring (P2.3 — forbidden path, double-signed)**:
- [ ] LoginPage submits `application/x-www-form-urlencoded` to `/api/admins/token` (verified via mocked fetch in test).
- [ ] On 200: token stored in localStorage; redirect to `?next=` path or `/dashboard`.
- [ ] On 401: error message renders; user stays on `/login`; password field clears.
- [ ] On 429: submit button disabled; countdown visible; re-enabled after `Retry-After` seconds.
- [ ] On 5xx: generic error renders; no token stored.
- [ ] `<RequireAuth>` redirects unauth to `/login?next=<current-path>`.
- [ ] `?reason=expired` shows differentiated banner copy on login page.
- [ ] Logout button clears localStorage + redirects to `/login`.
- [ ] `is_sudo` banner renders when claim is true.
- [ ] SignupPage hidden behind `VITE_PORTAL_SIGNUP_ENABLED=false` default.

D. **Router (P2.3)**:
- [ ] react-router-dom v6 HashRouter installed, handwritten Router removed.
- [ ] All 19 routes render correctly (smoke test passes).
- [ ] `#/login?next=/panel/billing` parses both params via `useSearchParams()`.
- [ ] Browser refresh on `#/signup?plan=monthly` preserves the `plan` query.
- [ ] Browser back/forward navigation works.

E. **Error boundaries (P2.3)**:
- [ ] App-level boundary catches a thrown error in any route — fallback UI renders, sidebar/topbar still visible if PanelShell-level boundary handles it first.
- [ ] PanelShell-level boundary scoped: thrown error in DashboardPage doesn't unmount sidebar.
- [ ] `logBoundaryError()` writes to localStorage `aegis_portal_errors` (capped FIFO 20).
- [ ] No GA / external analytics integrated.

F. **Eval (P2.3 — `.claude/rules/eval-gate.md`)**:
- [ ] `evals/golden-trajectories/customer-portal-p2-auth.yaml` exists with ≥6 cases (per R-6 mitigation list).
- [ ] `/cto-eval run` passes locally before merge.
- [ ] Mutation score ≥80% on `features/auth/**` (per `.claude/rules/forbidden-paths.md`).

G. **Compliance (cross-cutting)**:
- [ ] AGPL footer links present in marketing pages + panel footer + login page.
- [ ] `customer-portal/README.md` documents: P2 = internal/staging only; admin-tier login; signup deferred to P3; RATE_LIMIT_ENABLED requirement.
- [ ] `requires-double-review` label applied to P2.3 PR; senior engineer review recorded.

H. **No regression**:
- [ ] No change to dashboard/, app/, marketing/nilou-network/.
- [ ] No new Python dependencies.
- [ ] `dashboard/` continues to build and pass its own tests.

---

## 6. Kickoff

### 6.1 Next steps

1. **CTO review** of this DRAFT — seal each TBD or punt with explicit rationale.
2. **Senior engineer second sign** — required because P2.3 touches `customer-portal/src/lib/AuthPages.tsx` (§32.1).
3. Once SEALED → run `/cto-spec plan` for `SPEC-customer-portal-p2.md` to produce `PLAN-customer-portal-p2.md` (file/test list, ~30 tasks expected).
4. Then `/cto-spec tasks` → `TASKS-customer-portal-p2.md` (atomic task breakdown).
5. Code-generator sub-agent (sonnet) executes P2.1 → P2.2 → P2.3 as separate PRs.
6. Eval-runner gates P2.3 merge.
7. Update STATUS.md after P2 lands.
8. Add post-P2 calendar reminder: 2026-08-06 (3 months) — measure portal usage to feed D-018 推翻 condition data.

### 6.2 TBD register (awaiting CTO decision)

| ID | Question | Recommendation | Rationale |
|---|---|---|---|
| **TBD-1** | TSX strictness level for P2 | **Graduated**: `noImplicitAny: true`, `strictNullChecks: false` for P2; full `strict: true` in P3 | Full strict on P1's `defaultValue=`-heavy form code creates ~50 errors that aren't bugs; graduate path captures real type issues without churn |
| **TBD-2** | Token storage location | **localStorage** with documented XSS risk | Bearer header + no cookie auth means CSRF is moot; localStorage is simplest; httpOnly cookie would require backend change |
| **TBD-3** | i18n namespace structure | **Single `translation` namespace** (mirror dashboard) | Dashboard's flat-file pattern is proven; namespacing per-route adds bundler config without value at <500 keys |
| **TBD-4** | Router migration strategy | **Swap to react-router-dom v6 HashRouter** | PORTAL-RELIABILITY §5 row 4 wants query-string parsing; std library is cheaper than maintaining custom router; `useSearchParams` is a one-liner |
| **TBD-5** | Auth guard mechanism | **`<RequireAuth>` wrapper component** | Clearer in route table than HOC; aligns with react-router-dom v6 `<Route element={...}>` idiom; unit-testable in isolation |
| **TBD-6** | Auth scope option (CRITICAL) | **Option A: admin-only login, internal/staging only** | D-018 literal scope; no new backend surface; SignupPage stays mock; P3 SPEC will add User table. Risk R-1 mitigated by docs + banner |
| **TBD-7** | PR sequence | **3 sequential sub-PRs (P2.1 → P2.2 → P2.3)** | Smaller review surface; each builds on prior; single session avoids worktree contention (L-018) |
| **TBD-8** | Translation labor source | Punt — operator decision | Options: (a) operator self-translates ja/zh-cn (~1-2 days), (b) hire contracted translator (~1 day, $100-300), (c) DeepL machine translation + human polish |
| **TBD-9** | Marketing pages translation depth in P2 | **Skeleton only** — translate panel + auth fully; marketing gets EN keys + ja/zh skeletons with TODO markers | P4 may replace marketing pages wholesale; full marketing translation in P2 risks duplicate work |
| **TBD-10** | Mutation testing tool | Punt — recommend Stryker if dashboard introduces it; else manual coverage gate | Dashboard hasn't picked one yet; aligning later avoids two tools |

### 6.3 Recommended reviewers

- **CTO** (this user) — seal TBDs.
- **Senior engineer second sign** — required for §32.1 forbidden path (AuthPages.tsx). Specifically review: token storage choice (TBD-2), auth scope option A vs B vs C (TBD-6), error boundary telemetry stub (no GA / leak risk).
- **Eval-runner sub-agent** — gates P2.3 merge per `.claude/rules/eval-gate.md`.

### 6.4 Out of P2 scope (explicit deferrals)

- New `User` table + `/api/users/token` endpoint → P3 SPEC.
- Real signup / email verification / password reset → P3.
- Refresh tokens → P3 (matches backend `.env` comment).
- OAuth (Google / GitHub) → P3 or later; remove mock buttons in P2.
- Panel API failure modes (PORTAL-RELIABILITY §1 table) — only auth surface (§2) wired in P2; rest in P3.
- Real subscription URL / real invite codes (PORTAL-RELIABILITY §5 rows 2-3) → P3.
- Marketing page replacement of `marketing/nilou-network/` → P4.
- Telemetry SPEC + Plausible/PostHog integration → separate SPEC, P3-or-later.
- CSP headers, nginx config → ops work, separate runbook.
- Mutation testing infra (Stryker) — adopt if dashboard adopts; else punt.

### 6.5 Estimated effort breakdown

| Sub-PR | Deliverable | Effort | Notes |
|---|---|---|---|
| P2.1 | TSX migration | 1–2 d | Mechanical rename + types; bulk of time on Atoms.tsx generic component types |
| P2.2 | i18n setup + key extraction | 1 d code + 1–2 d translation | Translation labor is parallel to P2.3 code work |
| P2.3a | Router swap + RequireAuth | 1 d | react-router-dom shim |
| P2.3b | Auth wiring (login form + storage + hooks) | 1–2 d | Most code goes here |
| P2.3c | Error boundaries + telemetry stub | 0.5 d | Standard React patterns |
| P2.3d | Golden-trajectory eval | 0.5 d | Per `.claude/rules/eval-gate.md` |
| P2.3e | Tests (vitest + RTL) + mutation gate | 1 d | Forbidden-path 80% mutation requirement |
| **Total** | | **~7–10 d** | At 20–30 h/week → ~1.5 weeks calendar |

---

## 7. Citations

- D-018 (DECISIONS.md, 2026-05-06) — authorization for P2.
- PORTAL-RELIABILITY.md (2026-05-06) — §1, §2 (auth failure semantics), §4 (error boundaries), §5 (silent failures), §6 (i18n fallback).
- `.claude/rules/forbidden-paths.md` — `customer-portal/src/lib/AuthPages.jsx` listed; `requires-double-review` + spec-driven + ≥80% mutation.
- `.claude/rules/eval-gate.md` — golden-trajectory required for AuthPages changes.
- `.claude/rules/test-lock.md` — applies to all new tests in P2.3.
- D-002 — AGPL-3.0 footer/source link requirement.
- D-005 — SPEC-driven template (this SPEC follows postgres-redis structure).
- D-006 — `RATE_LIMIT_ENABLED` opt-in (Risk R-8 reference).
- D-008 — Redis optional + `RedisDisabled` semantics.
- D-016 (推翻 by D-018) — original "no user portal" decision context.
- L-018 — worktree isolation (P2 sub-PR sequencing recommendation).
- CLAUDE.md — customer-portal stack ground truth (Vite 6, React 18.3, JSX → TSX, port 5174, base `/portal/`).
- `app/routes/admin.py:68` — `POST /api/admins/token` endpoint.
- `app/models/admin.py:25-28` — Token response shape.
- `app/utils/auth.py:12-22` — JWT claims.
- `app/config/env.py:60-67` — JWT secret + TTL config.
- `dashboard/src/features/i18n/index.ts` — i18n template to mirror.

---

**End of SPEC-customer-portal-p2.md DRAFT.**
