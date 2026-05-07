# PLAN — Operator Dashboard 重写 wave 拆分 + 多 agent 并行

> 配套 `SPEC-dashboard-rewrite.md`。
> 创建:2026-05-07。
> Owner: 主线 + 4 个 sub-agent worktree。

## Wave 拆分

执行串行依赖 → 并行扇出 → 串行整合 的三段:

```
Wave-S (Serial Foundation)        ← 主线本会话执行
  │
  ├─ Wave-A (3 agents parallel)   ← spawn after wave-S done
  ├─ Wave-B (3 agents parallel)
  └─ Wave-C (2 agents parallel)
        │
        └─ Wave-I (Integration)   ← 主线
              │
              └─ Wave-D (Deploy)
```

## Wave-S — Foundation(主线串行,~1.5h)

**目标**:Nilou 共享组件库 + Layout 替换骨架。所有 wave-A/B/C agent 都 import 这一层,所以必须先完成。

### S.1 — `dashboard/src/common/components/nilou/` 组件库

按 `SPEC §How.shared-component`,移植 11 文件 jsx → tsx,加 i18n 钩子:

- [ ] `LotusMark.tsx` — 从 `docs/design-system-source/project/site/lib/Atoms.jsx` 96 行
- [ ] `StatusDot.tsx` — Atoms.jsx 110 行
- [ ] `Pill.tsx` — Atoms.jsx 102 行
- [ ] `Card.tsx` + `CardHeader.tsx` — PanelShell.jsx 103-114 行
- [ ] `Sparkline.tsx` — PanelPages1.jsx 3-14 行
- [ ] `KPI.tsx` — PanelPages1.jsx 16-28 行,`accent` enum 接 4 色
- [ ] `RingMeter.tsx` — PanelPages1.jsx 106-121 行
- [ ] `BigChart.tsx` — PanelPages1.jsx 123-148 行,**改 props 收数据**(原文是写死 14 天)
- [ ] `Row.tsx` — PanelPages1.jsx 99-104 行
- [ ] `PanelHead.tsx` — PanelShell.jsx 93-101 行
- [ ] `PanelShell.tsx` — PanelShell.jsx 3-40 行,**nav items 用 dashboard 路由表**

### S.2 — Layout 替换

- [ ] `dashboard/src/__root.tsx` — 改 `<PanelShell>` 包 `<Outlet />`
- [ ] `dashboard/src/routes/_dashboard.tsx` — sidebar / topbar 删除,委托 PanelShell
- [ ] 验证既有路由仍能 navigate(数据层零改动,只 UI 包装变了)

### S.3 — 可选:i18n key 框架

- [ ] `dashboard/src/i18n/locales/en/common.json` — 加 `nilou.kpi.*` 等 key 占位
- [ ] zh-cn / ja 同步翻译

### S.4 — 验证

- [ ] `pnpm build` 通过
- [ ] `pnpm lint` 0 warning
- [ ] localhost:5173 打开,登录后能看到新 PanelShell 包住老路由(老页面仍是上游样式 — 后续 wave 替换)

### S.5 — Commit + push

- [ ] commit message: `feat(dashboard): wave-S foundation - Nilou shared components + PanelShell layout`
- [ ] 不 PR,留在 `feat/dashboard-deep-theme` 分支等 wave-A/B/C merge 后一起

---

## Wave-A — 用户面 + 节点面(3 agent 并行,worktree)

预计每 agent ~2.5h。

### A.1 — Agent X: `users / admins`

worktree: `aegis-tmp-users-rewrite`
分支:`feat/dashboard-rewrite-users` 

任务:
- [ ] `routes/_dashboard/users.lazy.tsx` — KPI 4 + Nodes-style 表
- [ ] `routes/_dashboard/admins.lazy.tsx` — KPI 3 + Nodes-style 表
- [ ] 既有 dialog(create / edit user)保留功能,UI 改 Card / 衬线标题
- [ ] 行内 mini RingMeter 显示 traffic 使用率
- [ ] Pill 显示 plan tier

acceptance:
- [ ] CRUD 全部正常
- [ ] 4 KPI 数字真的从 API 算出来,不是写死
- [ ] 移动端响应式(sidebar collapse)

### A.2 — Agent Y: `nodes / hosts / services`

worktree: `aegis-tmp-nodes-rewrite`
分支:`feat/dashboard-rewrite-nodes`

任务:
- [ ] `routes/_dashboard/nodes.lazy.tsx` — **1:1 复刻 design NodesPage**(filter tabs + StatusDot + Pill mult + load 进度条 + iconBtn 操作)+ 日志抽屉
- [ ] `routes/_dashboard/hosts.lazy.tsx` — Nodes-style 表
- [ ] `routes/_dashboard/services.lazy.tsx` — Nodes-style 表

acceptance:
- [ ] /nodes 视觉与 design 包 NodesPage 截图对照差异 < 5%
- [ ] log container 抽屉打开仍走 `useNodesLog` hook(已有)
- [ ] 删除/重启节点功能保留

### A.3 — Agent Z: `dashboard 主页 + health`

worktree: `aegis-tmp-overview-rewrite`
分支:`feat/dashboard-rewrite-overview`

任务:
- [ ] `routes/_dashboard/index.lazy.tsx`(主页)— 类 design DashboardPage:
  - 4 KPI(全网流量 / 活跃用户 / 在线节点 / 平均健康)
  - BigChart 14d(全平台流量趋势,从 audit 或 traffic API 拉)
  - RingMeter quota(总配额使用率)
  - Recent activity(audit log 最近 10 条)
- [ ] `routes/_dashboard/health.lazy.tsx` — KPI + 子系统状态卡网格

acceptance:
- [ ] 主页加载 < 2s(含 KPI 数据)
- [ ] BigChart 用真实数据(降级:无数据时 placeholder skeleton)
- [ ] Recent activity 跳转 /audit 详情

---

## Wave-B — Reality + Audit + Billing(3 agent 并行)

### B.1 — Agent X: `reality / audit`

worktree: `aegis-tmp-realityaudit-rewrite`
分支:`feat/dashboard-rewrite-realityaudit`

任务:
- [ ] `routes/_dashboard/reality.lazy.tsx` — KPI(green/yellow/red counts)+ 卡片网格(每节点一卡, RingMeter score + 既有 FindingList)
- [ ] `routes/_dashboard/audit.lazy.tsx` — KPI(总/失败/今日)+ filter Card + Nodes-style 表

acceptance:
- [ ] 既有 FindingList 组件保留(已加固,无须重做)
- [ ] audit filter 状态保留(URL query param)

### B.2 — Agent Y: `billing/{plans,invoices,channels,purchase}`

worktree: `aegis-tmp-billing-rewrite`
分支:`feat/dashboard-rewrite-billing`

任务:
- [ ] `routes/_dashboard/billing/plans.lazy.tsx` — Card 网格(类 PricingGrid 编辑模式)
- [ ] `routes/_dashboard/billing/invoices.lazy.tsx` — KPI + 表
- [ ] `routes/_dashboard/billing/purchase.lazy.tsx` — Card 单列表单
- [ ] `routes/_dashboard/billing/channels.lazy.tsx` — 两 Card 并排

acceptance:
- [ ] TRC20 / EPay 两个 channel 配置 UI 都能渲染既有数据
- [ ] purchase 表单提交后跳转或弹 toast 反馈

### B.3 — Agent Z: `settings / login`

worktree: `aegis-tmp-settings-rewrite`
分支:`feat/dashboard-rewrite-settings`

任务:
- [ ] `routes/_dashboard/settings.lazy.tsx` — 分 section Card 列表
- [ ] `routes/_auth/login.tsx` — port `customer-portal/AuthPages.LoginPage`(简化为 admin auth)

acceptance:
- [ ] 设置项的 mutation 全部保留
- [ ] 登录与现有 token store 兼容(D-018 forbidden path,**只改 UI 不改 auth 逻辑**)

---

## Wave-I — 整合(主线)

预计 1-2h。

- [ ] Pull 所有 agent worktree 改动到 `feat/dashboard-deep-theme` 分支(squash 或 cherry-pick)
- [ ] `pnpm build` / `lint` / `test` 全跑
- [ ] 修任何视觉冲突 / TS error
- [ ] commit aggregator: `feat(dashboard): wave-A/B integrated - 14 routes Nilou design`
- [ ] 写 dashboard test:每个新 KPI / RingMeter / BigChart 至少 1 个 vitest snapshot

## Wave-D — 部署

- [ ] PR 写完整 description(SPEC + PLAN + 14 路由对照)
- [ ] codex 跨模型 review(`/cto-cross-review`)
- [ ] 合并到 main → tag `v0.4.6`(若 wave-S only)或 `v0.5.0`(若全 14 路由)
- [ ] `aegis-upgrade vX.Y.Z` 到生产
- [ ] 用户硬刷 + 14 路由眼检
- [ ] 反馈周期:user 抽样 5 路由对照 design 包,Card / KPI / RingMeter 出现率验收

---

## Agent 调用契约

每个 sub-agent 启动时给:

1. **角色** — `code-generator`(已有 prompt 模板,worktree 隔离)
2. **input bundle**:
   - 本 SPEC 路径
   - 本 PLAN 中分配给它的 wave 段(整段 paste)
   - design 源码路径 `docs/design-system-source/project/site/lib/`
   - wave-S 主线 commit SHA(让它从这个状态分叉)
3. **acceptance criteria**(同 SPEC §Acceptance + 该 wave 独立验收)
4. **output**:
   - worktree 内 commit + push 到分支
   - 报告产出文件清单
   - 自跑 `pnpm build` 通过 → 报 SHA
5. **isolation**: `aegis-tmp-<wave>-<agent>` 命名

主线整合时:
- 检查每 agent worktree 的 `pnpm build` 状态
- pull 到主线分支,跑 cross-build 验证
- 任何冲突由主线手动解,不再 callback agent

---

## 风险与回滚

| 风险 | 缓解 |
|---|---|
| Wave-S 失败,所有 wave 阻塞 | 主线先做完 wave-S 才 spawn,失败立即停 |
| 多 agent worktree 冲突 | 各 agent 路由互斥(不重叠文件)+ 共享组件由 wave-S 锁定不动 |
| 工期超预算 | wave-S done 后用户决定是 v0.4.6 ship Foundation only,or 等全部 wave 完成 ship v0.5.0 |
| 上游 quarterly merge 冲突变大 | 已知代价,本次重写就是为了脱钩 |

回滚:`aegis-upgrade v0.4.5`(token-only baseline)。
