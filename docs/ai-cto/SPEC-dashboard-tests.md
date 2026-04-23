# SPEC — 前端测试基建(S-X session)

> **状态**:X.0 已 flesh out(2026-04-23)。后续按 §PR sequencing 走 X.1-X.4。
>
> 参考:handbook §7 Spec-Driven、LESSONS L-012 / L-017(i18n 抽取)、
> SESSIONS.md §S-X、SPEC-billing-a2-a3.md §A.4(本 spec 的测试对象)。

## Kickoff prompt(X.1+ 继续用)

```
/cto-resume

你是 Aegis Panel 项目 S-X session(前端测试基建)。

必读:
- docs/ai-cto/SESSIONS.md §S-X
- docs/ai-cto/SPEC-dashboard-tests.md(本 spec)
- dashboard/package.json(vitest 已装)
- dashboard/vitest.config.ts(已有,jsdom)

地盘:
- dashboard/vitest.config.* 可改
- dashboard/src/test-utils/** 新增
- dashboard/src/**/*.test.tsx|ts 新增(只加配对测试,不改组件源)
- dashboard/package.json devDeps append
- .github/workflows/dashboard-ci.yml 改 unit-test job 的 command
  (append-only 以外的例外:修 `pnpm test` → `pnpm test:ci` 的
  bug,见 §CI 集成)

禁动: 任何 .tsx 源组件、任何 .ts 源 hook(只加 .test.tsx 配对
文件)
```

---

## What

给 `dashboard/` 建成熟的单元测试 + 组件测试基建,写第一批覆盖。
**不追 E2E**(Playwright 留给 v0.3)。目标:

- 全新 session 写新组件时能 `pnpm test` 立即验证
- PR CI 有 `test` job,失败阻塞 merge(目前 job 存在但 **watch
  模式 bug**,见 §CI 集成)
- 为 A.4 已落地的 `modules/billing/user/` 组件补全 leaf 单元

## Why

- 商业化前端开始变复杂(cart 计算、状态机轮询),回归靠目测不
  可持续
- 手册铁律 #1:服务产品愿景 —— 测试基建是商业化稳定性前提
- `cart-summary` 里是 **money math**(qty × price_cny_fen),回
  归 = 用户看到错总价,支持工单暴涨

## 非目标

- ❌ E2E (Playwright / Cypress)
- ❌ 视觉回归 (Chromatic 已接但只 workflow,不扩充)
- ❌ 改任何现有组件源文件;只加配对 `.test.tsx`
- ❌ 换测试运行器(vitest 1.6 固定,与 vite 5.4 匹配)

---

## 现状快照(X.0 测得,2026-04-23)

```
pnpm test 结果:
  Test Files  6 passed (6)
  Tests       40 passed (40)
```

| 文件 | 测数 | 来源 |
|---|---|---|
| `features/support-us/support-us.test.tsx` | 5 | 旧,保留 |
| `features/support-us/use-support-us.test.ts` | 2 | 旧,保留 |
| `modules/billing/user/api/mock-gate.test.ts` | 8 | A.4 随 #41 |
| `modules/billing/user/components/invoice-status-badge.test.tsx` | 9 | A.4 随 #41 |
| `modules/billing/user/components/cart-summary.test.tsx` | 9 | A.4 随 #41 |
| `modules/billing/user/components/plan-card.test.tsx` | 7 | A.4 随 #41 |

已装依赖(`package.json` 摘录,不需再装):

```
"vitest": "^1.6.0",
"@vitest/ui": "^1.6.0",
"@vitest/coverage-istanbul": "^1.6.0",
"@testing-library/jest-dom": "^6.6.3",
"@testing-library/react": "^14.3.1",
"@testing-library/user-event": "^14.5.2",
"jsdom": "^24.1.3"
```

> **vitest 版本修正**:骨架原文说 "vite 6.x / vitest 2.x",与实
> 际不符。项目是 vite **5.4.11** → vitest 1.6 是**正确**的锁定,
> 不要盲升。

---

## How(S-X 细化)

### Vitest + RTL 基础

- Vitest 1.6(与 vite 5.4 对齐)—— **不要升 2.x**,除非 vite 一
  起升,这是 X.0 之外的单独 PR
- `@testing-library/react@14` + `user-event@14` + `jest-dom@6` 均
  已装
- **Environment**:维持 **`jsdom`**,不切 happy-dom
  - 理由 1:现有 6 个测试文件全基于 jsdom 特性(`mock-gate.test.ts`
    用 `window.history.replaceState`)
  - 理由 2:当前 40 test 全套在本地 ~60s,未到 perf 痛点
  - 理由 3:happy-dom 在 i18next 初始化路径上有已知不兼容报告
  - 结论:**等遇到痛点再换**,非 X.0 任务

### Render helper(`dashboard/src/test-utils/render.tsx`)—— X.2 交付

现状是每个测试文件 inline `<I18nextProvider i18n={i18n}>`。抽取
动机:

- 消除 6+ 份重复 wrapper
- 未来加 `QueryClientProvider`(为 `invoice-poll.query.test.ts`)
  时只改一处
- 让下一个 session 写新测试有统一入口

API(目标形态):

```tsx
// dashboard/src/test-utils/render.tsx
import { ReactElement } from "react";
import { render, RenderOptions, RenderResult } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import i18n from "@marzneshin/features/i18n";

interface ExtraOptions {
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  opts: RenderOptions & ExtraOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const queryClient = opts.queryClient ?? new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const result = render(ui, {
    ...opts,
    wrapper: ({ children }) => (
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </I18nextProvider>
    ),
  });
  return { ...result, queryClient };
}
```

**不包含** `MemoryRouter` —— 现有 leaf 组件都不读路由;等到需要
route-level 测时再加 `createMemoryHistory`。

**i18n 策略**:用真 instance(非 stub)。已验证:jest-dom fallback
让 `t("key")` 在 locale 未加载时返回 key 自身,断言用
`/support-us.title/i` 或 `/checkout/i` 即可。切 stub 会失去 i18n
接线本身的价值。

### 覆盖策略

| 类型 | 策略 | 例子 |
|---|---|---|
| 纯展示 leaf | 断言关键文本/角色存在,不做 DOM 快照 | `invoice-status-badge` |
| 交互 leaf | `user-event` + 回调 mock | `plan-card`(onAdd), `cart-summary`(onRemove / onCheckout) |
| 业务 hook | **fake timers + QueryClient**:轮询/状态机 | `invoice-poll.query`(X.2) |
| 算逻辑 util | 纯函数单测 | `mock-gate.shouldUseMock` |

禁止:
- DOM 快照(`toMatchSnapshot`)—— shadcn 类名抖动大,噪音成本高
- 断言 `aria-hidden` / 样式类 —— 脆,用户看不到

### 第一批覆盖(A.4 leaf) —— X.2

**已 ✅**(#41 随主 PR 落):

- `plan-card` —— 7 test(i18n 名字 / ¥X.XX / shape / CTA / 已在
  cart 禁用)
- `invoice-status-badge` —— 9 test(8 state 不崩 + variant 区分)
- `cart-summary` —— 9 test(empty / 单行 / 多行无浮点漂移 / remove
  / checkout disable / unknown plan_id 丢弃 / 总价一致性)
- `mock-gate` —— 8 test(env 各值 / URL ?mock=1 override / 非对
  称性 / mockResolve fake timers)

**X.2 待补**(同 A.4 目录):

- [ ] `checkout-payment-picker.test.tsx`
  - EPay 默认选中最高 priority channel
  - 切到 TRC20 tab,Pay 调 `onPay("trc20:...")`
  - pending=true 时按钮 disabled
  - 无 enabled EPay channel 时 EPay tab 不渲染 Pay 按钮
- [ ] `invoice-poll.query.test.ts`(hook,不走组件)
  - 进终态(`paid` / `applied` / `expired` / `cancelled` /
    `failed`)时 `refetchInterval` 返回 `false`(停轮询)
  - 非终态(`pending` / `awaiting_payment`)返回预期间隔
  - 用 `QueryClient` + `renderHook` from RTL,`vi.useFakeTimers()`

**X.2 非必须**(排期后置):

- `flexible-addon-calculator.test.tsx` —— 仅纯展示,ROI 低
- `plans-grid.test.tsx` —— 现已由 `plan-card` 的测覆盖大部分
- `trc20-payment-screen.test.tsx` —— 倒计时 fake-timer 测试有坑,
  等 A.3.2 真 poller 回路落地后再写

### CI 集成

`dashboard-ci.yml` 现状(`.github/workflows/dashboard-ci.yml`):

- `lint` job:pnpm@8,`pnpm lint` ✅
- `build` job:pnpm@**9**,`pnpm build`(needs: lint) ✅
- `unit-test` job:pnpm@8,`pnpm test`(needs: [lint, build]) ⚠️

**已知 bug**:
1. **line 139 `run: pnpm test`** —— 默认走 watch 模式,CI 下理论
   永 hang;实际依赖 stdin 关闭让 vitest 退出。必改:
   - 推荐加 `package.json` 脚本 `"test:ci": "vitest run"`,CI 调
     `pnpm test:ci`(比 `pnpm test -- --run` 显式)
2. **pnpm 版本不一致**(lint 8 / build 9 / unit-test 8)—— 统一
   为 9(build 已用,较新)
3. **line 138 `name: Build Dashboard`** —— 复制粘贴遗留,改为
   `Run unit tests`
4. **无 coverage upload** —— X.4 再加,X.1 只修功能性 bug

X.1 改动(修 CI + 基础 hygiene):

```json
// package.json scripts 追加
"test:ci": "vitest run"
```

```yaml
# dashboard-ci.yml unit-test job
- name: Run unit tests
  run: pnpm test:ci
```

把三个 `pnpm/action-setup` 的 `version` 统一为 `9`。

### Coverage(X.4,不阻塞)

- 先打印,后门槛:`vitest run --coverage` 在 CI 跑但 **不 fail**
- 收集 `src/modules/billing/user/**` 为初始焦点(money 区域)
- 门槛建议(到 X.4 再定):line 70%、branch 60%,低于报 warning
- 不 upload 到 codecov(商业化不依赖 SaaS;本地/CI artifact 即可)

---

## Acceptance criteria

### X.0(本 PR)

- [x] `pnpm test` 本地跑通(6 files / 40 tests 全绿)
- [x] SPEC 里 vitest 版本、env、CI 现状与实测一致
- [x] 本 PR 不改任何 .tsx/.ts 源文件(docs-only)

### X.1

- [ ] `package.json` 加 `test:ci` script
- [ ] `dashboard-ci.yml` `unit-test` job 用 `pnpm test:ci`,job
      step name 改对
- [ ] 三个 pnpm action-setup 版本统一 `9`
- [ ] CI 上 PR 触发 `unit-test` 为 required(merge-blocking)

### X.2

- [ ] `src/test-utils/render.tsx` 创建,含 QueryClientProvider
- [ ] 既有 4 个 billing test 文件迁移到 `renderWithProviders`
      (纯 refactor,diff 应小)
- [ ] 新增 `checkout-payment-picker.test.tsx`、
      `invoice-poll.query.test.ts`
- [ ] 总 tests 数 ≥ 50

### X.3(可选,v0.3 前不强制)

- [ ] `dashboard-ci.yml` coverage step(不 fail)
- [ ] `src/test-utils/README.md`:下一个 session 写新 test 的 1
      页速查(使用 `renderWithProviders`、fake timer 范式、mock
      hook 范式)

---

## Risks

| 风险 | 现状 | 对策 |
|---|---|---|
| i18next provider 在测试里初始化慢 | 实测 6 files / 40 tests 60s,setup 占 11s | 可接受;真慢再切 stub |
| TanStack Router `MemoryRouter` 不支持全部 lazy routes | 尚未涉及(leaf 组件不读路由) | 到 X.3+ 再处理 |
| `refetchInterval` 在 fake timers 下行为 | 未测 | X.2 用 `vi.useFakeTimers()` + `vi.advanceTimersByTimeAsync` |
| S-F 同时段改组件引发 conflict | #41 已合并,冲突面归零 | S-X 只加 `.test.tsx` 新文件 |
| vitest 1.6 watch 模式 logUpdate bug | `pnpm test` 尾部抛,但 exit 0,tests 全绿 | 用 `pnpm test:ci` 走 `vitest run`(无 watch);不追 1.7 升级 |

---

## PR sequencing

1. **X.0**(本次):flesh out 本 spec → docs-only PR → merge
2. **X.1**:CI 修 bug(`test:ci` script + pnpm 版本 + step name)
   → PR 小,1 hop
3. **X.2**:`test-utils/render.tsx` + 迁移 4 个既有测试 + 新增
   `checkout-payment-picker` + `invoice-poll.query`(hook)
4. **X.3**:coverage step(非阻塞打印)+ test-utils README
5. **X.4**:可选 coverage thresholds;等 A.4 之外组件(nodes /
   users / hosts)开始补测时再推

每个 PR 对应一个 "I touch" / "I don't touch" 表,见 SESSIONS.md §S-X。
