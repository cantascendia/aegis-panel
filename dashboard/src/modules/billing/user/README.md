# `modules/billing/user/` — A.4 用户购买 UI skeleton

> **状态**:skeleton,flag-gated OFF 默认。backend `/api/billing/cart/checkout` + `/api/billing/invoices/me` 还没在 main 上,目前所有 API hooks 都走 fixtures。
>
> 本模块 PR:#41。分工 Charter 见 `docs/ai-cto/SESSIONS.md` §S-F。

## 结构

```
user/
├── api/
│   ├── mock-gate.ts            # VITE_BILLING_USER_UI + ?mock=1 判断
│   ├── plans.query.ts          # GET /api/billing/plans
│   ├── channels.query.ts       # GET /api/billing/channels
│   ├── checkout.mutate.ts      # POST /api/billing/cart/checkout
│   ├── my-invoices.query.ts    # GET /api/billing/invoices/me
│   └── invoice-poll.query.ts   # GET /api/billing/invoices/{id} 带 5s 轮询
├── components/
│   ├── plan-card.tsx
│   ├── plans-grid.tsx
│   ├── flexible-addon-calculator.tsx
│   ├── cart-summary.tsx
│   ├── checkout-payment-picker.tsx
│   ├── trc20-payment-screen.tsx
│   └── invoice-status-badge.tsx
├── fixtures.ts                 # 静态假数据,mock 模式返回
└── README.md                   # 本文件
```

路由入口:
- `/_dashboard/billing/purchase`(plan 展示 + 购物车)
- `/_dashboard/billing/my-invoices`(订单历史)
- `/_dashboard/billing/invoice/{id}`(**由 S-B 的 A.3.3 stub 填**)

## 开关

**默认状态**:`VITE_BILLING_USER_UI` 未设置或 `off` → hooks 返回 fixtures,sidebar 不显示 "Account" 组。

**preview / staging**:
```bash
# .env.development 或 .env.staging
VITE_BILLING_USER_UI=on
```

**review 时预览**(不改 env):在 URL 末尾加 `?mock=1`,任何运行环境都会强制 hooks 返回 fixtures,同时 sidebar 按照 env 决定是否显示。

## Flip-on 检查表(等 S-B 把 A.2.2 + A.3.1 落地后)

1. 确认 main 有 `POST /api/billing/cart/checkout` 和 `GET /api/billing/invoices/me` endpoint
2. 在 staging 设 `VITE_BILLING_USER_UI=on`,部署
3. smoke:
   - 普通用户登录 → 看到 sidebar "Account" 组 → Purchase / My invoices 两个入口
   - `/billing/purchase` plans 从真实 API 加载(不是 fixtures ¥35/88/198)
   - 加入购物车 → checkout → TRC20 标签 → 拿到真的 invoice_id 跳 `/billing/invoice/<id>`(S-B A.3.3 的 stub)
   - my-invoices 显示真订单
4. 再发一个 follow-up PR 删掉 `fixtures.ts` + hooks 里 mock 分支 + `mock-gate.ts`,全删干净

## 与 S-B 的边界

- S-B 的 A.3.3 会建 `modules/billing/components/trc20-payment-display.tsx`(admin demo stub)和 `modules/billing/api/checkout.mutate.ts`(admin 用)—— 和 **user/** 下的同名文件不冲突(不同路径)
- 合并后如需要清理重复,由**一个专门的 consolidation PR** 做,不混到 A.x / A.4 主 PR 里

## 钱相关的硬约束

- 所有价格走 **整数 fen**(1/100 CNY),UI 只在展示边界做 `/100` 格式化,禁止 float 参与运算
- TRC20 金额走 **整数 USDT-millis**(1/1000 USDT),同理
- Client 端 CartSummary 的总和计算是 **镜像**,不权威 —— 后端 `/cart/checkout` 会重新验证 total,客户端算错了后端也会拒

## 常见改动指引

- **加新 plan kind**(除了 fixed / flexible_traffic / flexible_duration):先改 `types/index.ts` 的 `PlanKind`,再到 `plan-card.tsx` + `flexible-addon-calculator.tsx` 加渲染分支
- **加新支付渠道**(比如 BTCPay):改 `types/user.ts` 的 `CheckoutChannelId` 联合类型,`checkout-payment-picker.tsx` 加一个 tab
- **改 TRC20 轮询间隔**:`invoice-poll.query.ts` 的 `POLL_INTERVAL_MS`,当前 5s

## 测试

见 `dashboard/src/modules/billing/user/**/*.test.tsx`。测试基建的完整 spec 在 `docs/ai-cto/SPEC-dashboard-tests.md`,由 **S-X session** 独立推进。本模块先写几个 leaf 组件 + hook 的高价值测试作为 S-X 落地的示范。
