# `modules/billing/user/` — admin-on-behalf-of-user checkout

> **2026-04-26 重定位**:本目录原为 PR #41 的"用户自助购买"skeleton(flag-gated OFF)。BRIEF-billing-user-auth-blocker.md 选项 A 拍板后,A.4 改为 admin 给用户开订单的客户结账 UI,因为 Marzneshin VPN 用户没有 panel web auth,自助路径在当前用户基础上不可行。
>
> 目录名 `user/` 保留是为最小化 diff;语义"我服务的那个用户"。后续 cleanup PR 会重命名为 `admin-checkout/`。

## 结构

```
user/
├── api/
│   ├── plans.query.ts          # GET /api/billing/admin/plans?include_disabled=false
│   ├── channels.query.ts       # GET /api/billing/admin/channels (filter enabled, append synth TRC20)
│   ├── checkout.mutate.ts      # POST /api/billing/cart/checkout (admin, 接收 user_id)
│   └── invoice-poll.query.ts   # GET /api/billing/admin/invoices/{id} 5s 轮询直到终态
├── components/
│   ├── user-selector.tsx       # 搜 + 选 VPN 用户 (debounced /users?username=)
│   ├── plan-card.tsx
│   ├── plans-grid.tsx
│   ├── flexible-addon-calculator.tsx
│   ├── cart-summary.tsx
│   ├── checkout-payment-picker.tsx
│   ├── trc20-payment-screen.tsx
│   └── invoice-status-badge.tsx
├── fixtures.ts                 # 组件测试 seed data,运行时不读
└── README.md                   # 本文件
```

## 单一入口

- `/_dashboard/billing/purchase` — 全套结账流程,SudoRoute 限定。sidebar 在 Billing 组下的 "Checkout"。
- 没有用户侧 `/billing/my-invoices`(已删除,被 admin invoices page #35 覆盖)。

## 工作流程

1. **选用户**:`<UserSelector>` 输入用户名,debounced 250ms 调 `/users?username=...&size=20`,下拉选中。组件向父级 emit `{id, username}`。
2. **选套餐**:`<PlansGrid>` 固定套餐 + `<FlexibleAddonCalculator>` 加量套餐(GB / 天)。`<CartSummary>` 实时显示总额(整数 fen `/100` 显示)。
3. **选支付**:`<CheckoutPaymentPicker>` Tabs:
   - **易支付** tab:radio 选 enabled 码商
   - **TRC20** tab:无子选择
4. **支付**:点 Pay 调 `POST /api/billing/cart/checkout`,body 包含 `{user_id, channel_code, lines[], success_url, cancel_url, subject?}`。
5. **支付完成后跳转**:
   - 易支付 → `window.open(payment_url, "_blank")`,运营复制链接私发用户(Telegram / 邮件)
   - TRC20 → SPA 跳 `/billing/invoices`(admin invoices 页),运营在 invoice detail dialog 看 memo + 金额 + countdown,截图发用户

## 钱相关硬约束

- 价格用**整数 fen**(1/100 CNY)在 wire + state;UI 仅在 display 边界 `/100` 格式化
- TRC20 金额用**整数 USDT-millis**(1/1000 USDT)
- 客户端 cart total 是镜像计算,不权威 —— 后端 `/cart/checkout` 重新核验
- 所有 `*.test.tsx` 钉死整数 fen 算法不漂移(见 cart-summary.test.tsx 多行总和测试)

## 边界(per SESSIONS.md S-F charter)

**独占**:本目录全部 + `routes/_dashboard/billing.purchase.lazy.tsx`

**追加共享**:`types/index.ts` 末尾 re-export、`locales/{en,zh-cn}.json` 的 `page.billing.purchase.*` subtree、`features/sidebar/items.tsx` 的 Billing.Checkout 行

**禁动**:`ops/**`, `hardening/**`, `app/**`, 别的 dashboard 模块

## 测试

- `*.test.tsx` 共 33 tests(2026-04-26)。覆盖 plan-card / cart-summary / invoice-status-badge / checkout-payment-picker / mock-gate(已删,test 也已删)
- 测试用 `@marzneshin/test-utils/render` 的 `renderWithProviders`(S-X session 提供)

## 历史

- **PR #41** A.4 skeleton(flag-gated user-self-serve mock UI)
- **PR #49** money-critical tests(CartSummary + PlanCard 16 tests)
- **PR #本次** option A flip-on:删 mock-gate / fixtures fallback / my-invoices route,加 UserSelector,接真 admin endpoints
