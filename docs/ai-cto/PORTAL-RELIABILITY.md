# customer-portal Reliability Surface (§43)

> 本文件预定义 customer-portal 的可靠性边界 — 在 P3(后端 API 接入)启动**之前**冻结失败模式 / fallback / cost cap / circuit breaker / 错误边界。
> 状态:**DRAFT** — P1 land 后由 reliability-auditor 起草(2026-05-06,wave-11 R2)。P3 SPEC 必须引用并细化本文件。
> 更新触发:每次 P2/P3/P4 阶段交付前。

---

## 0. Scope

只覆盖 `customer-portal/`(用户自助门户 SPA),不含 `dashboard/`(操作员面板,Marzneshin 上游)或 `marketing/nilou-network/`(纯静态站)。

| 阶段 | 范围 | 本文件适用? |
|---|---|---|
| P1(已 ship #240)| Visual + mock data,无后端调用 | ⚠️ 仅 hash-router 错误边界条目 |
| P2 | Login/Signup 接 Marzneshin admin auth | ✅ §1 §2 §5 |
| P3 | Panel 9 页接真后端 API(traffic / billing / tickets / invite) | ✅ 全部 |
| P4 | Marketing 页接管 nilou-network 三语 | ✅ §6 (CDN cache + i18n fallback) |

---

## 1. API 失败模式预定义(P3 启动前必填表)

每个 panel 页对应一个 API endpoint。下表列出失败行为契约 — P3 实现必须按此表执行,**不接受"边写边定义"**。

| Page | Endpoint | Timeout | Retry | Fallback UI | Circuit breaker |
|---|---|---|---|---|---|
| `#/dashboard` | `GET /api/v1/me/usage` | 4 s | 1× exp-backoff | KPI cards 显示 `—` + "Couldn't load usage. Retry" | 5 fail/min → degrade to cached value 30 min |
| `#/dashboard` | `GET /api/v1/me/subscription` | 3 s | 0 | 显示 mock URL + "Subscription URL temporarily unavailable" warning pill | TBD |
| `#/panel/nodes` | `GET /api/v1/me/nodes` | 5 s | 2× | Empty state with reload button + last-known status from localStorage(<1h)| TBD |
| `#/panel/traffic` | `GET /api/v1/me/traffic?range=14d` | 6 s | 1× | Skeleton chart + "Traffic data lagging — last sync N min ago" | TBD |
| `#/panel/plans` | `GET /api/v1/plans` | 4 s | 2× | 显示 PLANS 常量(MarketingSections.jsx 的 hardcoded 4 tiers,作为 fallback) | TBD — plan list 改动频率低,可大胆用静态 fallback |
| `#/panel/billing` | `GET /api/v1/me/invoices` | 5 s | 1× | 显示 "Invoices loading… check back in a moment" + 不暴露付款入口避免重复扣款 | **关键**:5 fail/min → 完全禁用 charge 按钮(防 race 二次扣款) |
| `#/panel/tickets` | `GET /api/v1/me/tickets` | 4 s | 1× | Empty state | TBD |
| `#/panel/invite` | `GET /api/v1/me/referrals` | 4 s | 1× | 显示 invite link + "Stats loading…" | TBD |
| `#/panel/account` | `GET /api/v1/me/profile` | 3 s | 0 | Form 显示空 + 禁用 save 按钮 + "Profile failed to load — refresh" | TBD |

> **关键失败语义**:任何 endpoint 5xx 5 次/分钟 → 全局 toast 通知用户 "Some panel data is temporarily unavailable. We're aware." 且**不**自动登出。

---

## 2. Auth 失败语义(P2 起)

| 场景 | 行为 |
|---|---|
| Login 401 | Form 显示 "Email or password incorrect" — 不区分(防探测) |
| Login 429 | "Too many attempts. Wait 60s." + 60s 倒计时锁定 |
| Login 5xx | "Sign-in temporarily unavailable. Try again in a moment." 不进入 panel |
| Token 过期(panel 页 401)| 静默 refresh 1 次;失败则 redirect `#/login?reason=expired`,**保留** intended path 用 `?next=` |
| CSRF 失败 | 全局错误对话框 "Session invalid. Sign out and back in." 不自动重 auth |
| Refresh token 撤销(用户在另一设备登出) | 同上,redirect `#/login` |

---

## 3. Cost Cap 与 Rate Limit(P3 必备)

`docs/ai-cto/CONSTITUTION.md` 列出 ">200 用户" 警告。Portal 写操作密集页(billing / tickets / account)需限流避免 user 滥用 / 误触刷接口:

| Endpoint pattern | 限流(per-user)| 触发后 |
|---|---|---|
| `GET /api/v1/me/*` (read) | 60/min | 429 + 显示 "Slow down — refresh in 1 min" |
| `POST /api/v1/me/*` (write) | 10/min | 429 + 禁用 submit 60s |
| `POST /api/v1/me/charge` (billing) | 3/hour | 429 + 进入"已申请,等管理员处理"分支 |
| `POST /api/v1/me/tickets` (create) | 5/day | 429 + "工单上限触达,请等待回复" |

**Backend cost cap**(Marznode gRPC 调用 traffic):per-user `me/traffic` cache 60s in Redis,绝不逐请求穿透到 gRPC。

---

## 4. 错误边界(React Error Boundary)— P1 已知缺陷

### 现状
- `customer-portal/src/App.jsx` 无 `<ErrorBoundary>`,任何 panel 页 JSX runtime error → 整个 SPA 白屏
- Hash router 拼错(`#/panel/nodez`)→ `App.jsx` line 79 已有 NotFound 兜底 ✅
- 无 sentry / posthog / analytics 监控 — 用户白屏后 operator 不会知道

### P2 必修
- 加 `<ErrorBoundary>` 包住 `<App />` 内的每个 page route
- Fallback UI:"Something didn't load right. The team has been notified. Refresh, or [contact]."
- 接最小遥测(可考虑 self-hosted plausible / postlog,**不**接 Google Analytics — 与 §3 隐私承诺矛盾)
- 边界要分两层:
  1. App-level(catch 所有未捕获错误)
  2. PanelShell-level(panel 内单页崩溃不影响 sidebar / topbar)

---

## 5. 隐式 silent failure 路径(wave-11 audit 发现)

| 路径 | 风险 | 何时修 |
|---|---|---|
| Mock data → real API switch 无 feature flag | P3 启动时一刀切替换,某 endpoint 没接好就全员看到错误 | P2 末尾起加 `VITE_PANEL_API_MOCK=true` 环境变量,允许"局部 mock + 局部真接" |
| 订阅 URL 显示用 mock UUID | 用户复制后接客户端 → 客户端连 dead URL,用户骂"不能用" | P3 第一个落地:必须先验证 URL 真接通 |
| 邀请链接 `LOTUS-LW28` 是 hardcoded | 用户分享后,链接全是同一个 invite code 池,奖励统计失效 | P3 必修,优先级高于 panel/traffic |
| Hash router URL 上有 `?plan=monthly` 等 query string | 浏览器刷新会丢 query(hash 路由 quirk),Signup 第二步重置 | P2 切 react-router-dom 时整体修复 |
| `localStorage` 用于 fallback cache(节点列表)| 跨浏览器 / 隐身模式不一致 | 文档化,不修(可接受) |

---

## 6. CDN / 缓存策略(P4 营销页接管时必备)

P4 把 `marketing/nilou-network/{en,ja,zh}/` 替换为 portal SPA 的 marketing 路由后:

- **Marketing 页**(`#/`、`#/features` 等):Cloudflare Pages 边缘 cache 静态资产 1 年 + immutable;HTML cache 5 min
- **Panel 页**(`#/dashboard` 等):**绝不** cache(`Cache-Control: private, no-store`),与 marketing 共用 SPA 但 nginx 层判 path
- **i18n fallback**:`#/?lang=ja` 但 `ja/` 翻译缺失 → fall back to `en/`,不显示半英半日

---

## 7. 监控与 SLO(P3 起)

| 指标 | 目标 | 告警阈值 |
|---|---|---|
| Portal LCP(Largest Contentful Paint) | < 2.5 s p95 | > 4 s 持续 5 min |
| Portal API endpoint p95 latency | < 800 ms | > 2 s 持续 5 min |
| Portal 5xx 率 | < 0.5% | > 2% 持续 1 min |
| Portal hash-router 404(NotFound)触发率 | < 1% sessions | > 5% — 说明有死链 |
| Portal Login 失败率(429 + 5xx)| 监控,不告警 | > 10% — 说明限流不当 |

---

## 8. 引用与依赖

- 失败模式契约由本文件 §1-§4 冻结,P3 SPEC 必须引用 `[PORTAL-RELIABILITY §1 表]`
- 与 `.claude/rules/forbidden-paths.md` 配合:涉及 §1 billing endpoint 改动必须双签
- 与 D-018 (DECISIONS.md)配合:推翻条件之一"6 个月内 portal 实际使用率 < 10% 注册用户"= 本文件 §7 数据驱动

---

## 修订历史

| 日期 | 变更 | 触发 |
|---|---|---|
| 2026-05-06 | 初版 DRAFT | wave-11 reliability-auditor 建议(harness-auditor §43 缺口)|
