# SPEC — 前端测试基建(S-X session)

> **状态**:骨架,待 S-X session 首日 flesh out。
>
> 参考:handbook §7 Spec-Driven、LESSONS L-012 / L-017(i18n 抽取)、
> SESSIONS.md §S-X。

## Kickoff prompt

```
/cto-resume

你是 Aegis Panel 项目 S-X session(前端测试基建)。

必读:
- docs/ai-cto/SESSIONS.md §S-X
- docs/ai-cto/SPEC-dashboard-tests.md(本骨架)
- dashboard/package.json(看 vitest 装了没)

地盘:
- dashboard/vitest.config.* 可改
- dashboard/src/test-utils/** 新增
- dashboard/src/**/*.test.tsx|ts 新增(只加配对测试,不改组件源)
- dashboard/package.json devDeps append
- .github/workflows/dashboard-ci.yml 加 test job(append-only,不动
  现有 job)

禁动: 任何 .tsx 源组件、任何 .ts 源 hook(只加 .test.tsx 配对
文件)

第一步: 跑 `cd dashboard && pnpm test` 看现状(PR #2 里 vitest 
config 已存在),把骨架 SPEC 的 TBD 补完 → docs-only PR。
```

---

## What

给 `dashboard/` 建成熟的单元测试 + 组件测试基建,写第一批覆盖。
**不追 E2E**(Playwright 留给 v0.3)。目标:

- 全新 session 写新组件时能 `pnpm test` 立即验证
- PR CI 有 `test` job,失败阻塞 merge
- 为 A.4 已落地的 `modules/billing/user/` 组件覆盖 leaf 单元 5-7 个

## Why

- 当前 `dashboard/` 只有 2 个 test 文件(`features/support-us/*`)
- 商业化前端开始变复杂(cart 计算、状态机轮询),回归靠目测不可
  持续
- 手册铁律 #1:服务产品愿景 —— 测试基建是商业化稳定性前提

## 非目标

- ❌ E2E (Playwright / Cypress)
- ❌ 视觉回归 (Chromatic 已接但只 workflow,不扩充)
- ❌ 改任何现有组件源文件;只加配对 `.test.tsx`

---

## How(S-X 细化)

### Vitest + RTL 基础

- Vitest 版本对齐 `vite` 大版本(本项目 vite 6.x,vitest 2.x)
- `@testing-library/react` + `@testing-library/user-event` +
  `@testing-library/jest-dom`
- `happy-dom` 比 jsdom 快,推荐

### Render helpers(`dashboard/src/test-utils/render.tsx`)

必要 providers:
- `QueryClientProvider`(TanStack Query)—— 每个测试 fresh client
- `I18nextProvider`(已有 instance)—— 加载真 locale JSON 还是
  stub? 推荐 stub(让 `t("key")` 返回 key 自身)避免 flaky
- `MemoryRouter`(TanStack Router)—— 用 `createMemoryHistory`

API:
```tsx
export function renderWithProviders(
  ui: ReactElement,
  { initialRoute = "/", queryClient = mkClient(), ... } = {},
): RenderResult
```

### 第一批优先测

**A.4 leaf 组件**(高 ROI,用户面 = money):
- `modules/billing/user/components/plan-card.test.tsx` — 渲染 +
  "alreadyInCart" disabled + onAdd call
- `modules/billing/user/components/invoice-status-badge.test.tsx`
  — 每个 state 的 variant 映射
- `modules/billing/user/components/cart-summary.test.tsx` — 空态 /
  算总 / 删行 / 结账按钮 disable 逻辑
- `modules/billing/user/components/checkout-payment-picker.test.tsx`
  — tab 切换 / EPay radio 选择 / pay 回调

**API hooks**(更重要,money math):
- `modules/billing/user/api/mock-gate.test.ts` — env flag 组合 /
  ?mock=1 override / URL 无 params
- `modules/billing/user/api/invoice-poll.query.test.ts` —
  refetchInterval 在终态停止(用 fake timers)

### CI 集成

`.github/workflows/dashboard-ci.yml` 的现状:TBD(S-X 检查) —
如果已有 `test` job,S-X 改 fail-fast + coverage upload;没有则新
增一个 job:
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: pnpm/action-setup@v4
    - run: pnpm install --frozen-lockfile
    - run: pnpm --filter dashboard test -- --run
```

---

## Acceptance criteria

- [ ] `pnpm test` 在本地 Windows + Linux CI 都能跑
- [ ] 第一批 6-8 个 test 文件全绿
- [ ] CI job 加入并在 PR 上 required(merge-blocking)
- [ ] `test-utils/render.tsx` 有 README / doc comment,让下一个
  session 写新测试不需重读 spec
- [ ] 不引入 `jsdom` 的默认(性能问题)—— 用 `happy-dom`
- [ ] `vitest.config.ts` 里 `test.environment = "happy-dom"`

## Risks

| 风险 | 对策 |
|---|---|
| i18next provider 在测试里初始化慢 | stub `t()` return key(跳过真加载) |
| TanStack Router `MemoryRouter` 不支持全部 lazy routes | 只测 component,不测 route 级交互 |
| `refetchInterval` 在 fake timers 下行为 | `vi.useFakeTimers("modern")` + `act(() => vi.advanceTimersByTime(...))` |
| S-F 在同时段改组件引发 conflict | S-X 只动 `.test.tsx` 新文件,零交叉 |

## PR sequencing

1. **X.0**:本 spec 补全,docs-only PR
2. **X.1**:`vitest.config` + `test-utils/render.tsx` + 1 个示例
   `plan-card.test.tsx`
3. **X.2**:剩余 A.4 组件测 + hook 测全家桶
4. **X.3**:dashboard-ci.yml 加 job
5. **X.4**:coverage thresholds(非阻塞初期,只打印)
