# BRIEF — A.4 用户购买流卡在 user-auth 模型未定义

> **状态**:决策待定。本 brief 是 S-F session 在 PR #41 后(A.4 skeleton flag-gated OFF)发现的根本性 blocker。需 CTO 拍板走哪条路再继续。
>
> _Created: 2026-04-26 by S-F session 接力_

## 现象

A.4 skeleton(PR #41)落地时按 `SPEC-billing-mvp.md` §"User journey" step 3-4 假设用户能登录 panel,看到 plan 列表,加入购物车,自助 checkout。skeleton 用 fixtures + flag 把 UI 撑起来等后端就绪。

到 2026-04-26,后端已经完成:
- ✅ A.2.1 EPay provider(PR #46)
- ✅ A.2.2 webhook + admin checkout(PR landed,见 `ops/billing/checkout_endpoint.py`)
- ✅ A.3 TRC20 provider + poller(PR #79)
- ✅ A.5 scheduler / apply-paid(PR #77)

**但所有 billing 路由都是 admin-only**:
- `POST /api/billing/cart/checkout` — `SudoAdminDep`,接收 `user_id`,admin 代下单
- `GET /api/billing/admin/{plans,channels,invoices}` — `SudoAdminDep`
- `GET/POST /api/billing/admin/invoices/{id}/...` — `SudoAdminDep`

**用户自服务路径(`/api/billing/plans` 公开 / `/invoices/me` / 用户视角 checkout)完全不存在**。

## 根因:Marzneshin 没有给 VPN 用户做 web 认证

`app/dependencies.py` 的 auth 模型:

| Dep | 谁能用 | 怎么 auth |
|---|---|---|
| `get_admin` / `sudo_admin` | 运营管理员 | username + password → JWT |
| `get_subscription_user` | VPN 用户 | URL 里的 `username + key` (16 进制 token),非交互 |
| `get_user(username, ...)` | admin-mediated 查询 | 需要 admin JWT |

**VPN 用户没有任何 "web 登录" 路径**。订阅 URL 是"知道就用"的 bearer token,不能用来 cookie session 进 SPA。

`SPEC-billing-mvp.md` 写"user 登录 panel,选套餐,checkout"时**默认了 user web auth 存在,实际不存在**。这是一个 spec 假设穿了的洞,A.1-A.3 backend 一路推进时没暴露(因为只做 admin 路径),A.4 frontend skeleton 才撞墙。

## 决策选项

### 选项 A:**重定位 A.4 为 "Admin-on-behalf-of-user" UI**(推荐,最小改动)

A.4 不是用户 SPA,而是 admin 在 dashboard 里给某个用户开订单 + 付款的 admin 工具。流程:

1. 运营在 `/dashboard/billing/checkout` 选 user(下拉 + 搜索)+ plans
2. 选支付通道(EPay 哪个码商 / TRC20)
3. 提交后:
   - EPay → 拿到 `payment_url`,**复制给用户**(私聊 Telegram / 邮件)
   - TRC20 → 拿到 invoice id,UI 显示 QR + memo + 金额,**截图给用户** 或导出 PDF
4. `/dashboard/billing/my-invoices` → admin 看 user 的全部历史(已存在 `/admin/invoices?user_id=X`)

**优势**:
- 零新 backend(全用 `/admin/*`)
- 本周可以做完
- 符合中国机场实际运营模式(运营人工拉群、客服推链接,用户不直接进 panel)
- 我 A.4 skeleton 的代码 90% 可复用,只需把 user_id 从 "auth 取" 改 "下拉选"

**劣势**:
- 不"自动化",规模大了运营累
- 不如真自助 UX 干净

**触面**:仅 `dashboard/src/modules/billing/user/**` 改名 → `admin-checkout/**`,加 user 选择器组件。零 ops/ 触碰。

---

### 选项 B:**给 VPN 用户做 web auth**(大动作)

新增 user-side 登录:用订阅 URL 里的 `key` 换 short-lived JWT,然后正常 React app cookie session。

**需要的 backend 改动**(S-B 工作):
1. `POST /api/user/auth/exchange` — body: `{username, key}`,返回 JWT(15min)
2. 新 dep `current_user`(decode user JWT)
3. 5 个新路由:
   - `GET /api/billing/plans` — `current_user`,enabled-only
   - `GET /api/billing/channels` — `current_user`,enabled-only(过滤掉 secret_key)
   - `POST /api/billing/cart/checkout` — `current_user`,user_id 从 JWT,不接收
   - `GET /api/billing/invoices/me` — `current_user`,filter `user_id == current_user.id`
   - `GET /api/billing/invoices/{id}` — `current_user`,additional ownership check

**优势**:真自助,符合 SPEC 原意,>200 用户规模可持续

**劣势**:
- 用户 JWT 注销 / refresh / 多设备 / 撤销 全要做
- 需要 SPEC-user-auth.md 走 spec-driven
- 至少 1-2 个 sprint,延迟商业化上线 2 周
- VPN 用户密码学习成本(他们只有 subscription URL,没"账号密码"概念)

**触面**:`app/dependencies.py`(upstream 同步区,L-022 须看 3 条件)+ `app/routes/user_auth.py` 新文件 + ops/billing/ 加 user 路由 + 整套 dashboard /login user 页

---

### 选项 C:**用 subscription URL 做 token,跳过 web 登录**

用户点击订阅链接里我们追加的 `?billing=1` 参数 → SPA 启动时把 `username + key` 缓存到 sessionStorage → 每个 billing 请求带这俩做 query string auth。

**优势**:利用现有 `get_subscription_user` dep,backend 改动小

**劣势**:
- key 放 URL/sessionStorage = security smell,被截屏 / 浏览器历史泄露
- 用户每次新设备 / 清缓存都要重粘订阅 URL
- 不能登出
- 我们订阅 URL 已经是事实上的 secret,把它再当 web auth 是 reuse 错位

---

## 推荐

**选 A**。理由:

1. **配合实际运营模式**:中国机场 99% 是 Telegram/微信群运营,用户在群里 @ 运营要新套餐,运营 1 分钟开单回链接。完全自助 SPA 是欧美 SaaS 的形态,在这个市场属于 over-engineering
2. **零 backend 阻塞**:今天 / 明天就能做完,把 A.4 从"等 X 才能继续"变成"已完成"
3. **可演化路径**:如果以后真要做选项 B,选 A 的 admin UI 是 production-ready 的运营工具,不浪费;选 B 时把同样的 React 组件包到 user-auth 路径下复用即可

## 行动项(待 CTO 决策后)

**若选 A**(推荐):
- [ ] S-F 重命名 `dashboard/src/modules/billing/user/` → `dashboard/src/modules/billing/admin-checkout/`
- [ ] 加 `<UserSelector>` 组件(基于现有 admin user 列表 API)
- [ ] checkout.mutate 接 admin checkout endpoint(`POST /api/billing/cart/checkout` with `user_id`)
- [ ] my-invoices 改成 `/admin/invoices?user_id={selected}`
- [ ] flip-on:删 `mock-gate.ts` + `fixtures.ts`,sidebar Account 组改为 sudo only
- [ ] L-018 follow-up:更新 SESSIONS.md S-F charter 反映新 scope(`admin-checkout/` 而非 `user/`)

**若选 B**:
- [ ] CTO 排期 1-2 sprint
- [ ] 写 SPEC-user-auth.md
- [ ] 拆给 S-B(backend auth + endpoints)和 S-F(frontend login flow + 组件接 real APIs)

**若选 C**:
- [ ] 写 SPEC-subscription-url-as-billing-token.md
- [ ] 评估 subscription URL 信息密度是否够、能否撤销

## 历史包袱

A.4 skeleton(PR #41)的 fixtures 和 mock-gate 是有用的,无论选哪条都有价值:
- 选 A:fixtures 改成 admin-perspective 的 demo 数据,留着给 dashboard 单测用
- 选 B:fixtures 真正用作"backend 没 ready 时的 preview",原计划照样
- 选 C:同 B

无论哪条,**不要急着删 fixtures.ts**。

---

_Cross-references: SPEC-billing-mvp.md §User journey, SPEC-billing-a2-a3.md §A.2.2, ops/billing/checkout_endpoint.py:90 docstring "A.4 adds the user self-serve variant under a separate auth dep" (该 TODO 现在归本 brief 解决)_
