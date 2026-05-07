# SPEC — Operator Dashboard 全面重写为 Nilou Design

> Status: DRAFT, awaiting user sign-off before agent spawn.
> Owner: CTO + Sub-agent C (this session).
> Created: 2026-05-07.

## Context

PR #245 / v0.4.5 仅做了 token 层重定义,大量 Marzneshin 上游组件硬编码 Tailwind 调色板,绕过 HSL 变量,导致右侧内容面板视觉未变。后续 commit a208d28 (Phase 1+2+3) 在 `feat/dashboard-deep-theme` 分支补齐了 palette + 9 文件 token 化,但**页面布局仍是 Marzneshin 上游的**:TanStack Table 默认表格,无 KPI 卡片,无 RingMeter / Sparkline / BigChart,无 Cormorant 标题,无 Nilou 视觉语言。

用户决定:**全面重写,1:1 复刻 design 包视觉,丢弃 Marzneshin 上游布局,设计里有但 dashboard 没有的功能要加不能减。**

## What

把 `/HFPB5MLu/` 下 14 个运营者路由全部从 Marzneshin 上游布局迁移到 design 包(`docs/design-system-source/project/site/lib/PanelShell.jsx + PanelPages1/2.jsx`)的视觉语言:

- Sidebar 256px(LotusMark + 分组 nav + Trial 卡)
- Topbar 14px padding(search + bell + globe + avatar 下拉)
- 主区 cream 卡片 + Cormorant 标题 + KPI 网格 + Sparkline / RingMeter / BigChart
- 表格:design Nodes-style(StatusDot + 等宽 host + Pill mult + 进度条 load)

**保留所有现有功能**:数据 hook(API queries / mutations)100% 复用,只换 UI 层。新增 design 里有 dashboard 没有的元素(KPI / Sparkline / RingMeter / BigChart / Pill / StatusDot 视觉化)。

## Why

1. **消解用户"右边没变"反馈** — palette token 治标不治本,布局结构不变就是 Marzneshin 视觉
2. **品牌一致性** — customer-portal 是 Nilou,operator dashboard 也得是 Nilou,客户/运营者跨产品体验统一
3. **脱钩 upstream** — 重写后 `dashboard/src/routes/_dashboard/` 完全 fork-owned,quarterly upstream merge 不再触及这块
4. **加分功能** — KPI / Sparkline 让运营者一眼看到关键指标,比上游 Marzneshin 默认表格信息密度高得多

## How

### 数据形态映射(运营者 vs design 客户)

| Design 元素 | 客户场景(原意) | 运营者复用方式 |
|---|---|---|
| `KPI "Used this cycle"` | 该客户本月流量 | "全网总流量 / 本月" |
| `KPI "Active devices"` | 该客户的设备数 | "在线节点数 / 在线用户数" |
| `KPI "Avg. latency"` | 该客户到节点延迟 | "节点平均健康分 / 平均延迟" |
| `RingMeter` | 该客户的配额使用 | "总流量配额使用率(所有付费用户合计 / Cap)" |
| `BigChart 14d` | 该客户的 14 天用量 | "全平台 14 天总流量曲线" |
| `NODES` 表 | 客户能连的节点列表 | **1:1** — 运营者的 marznode VPS 列表 |
| `StatusDot tone` | 节点连接状态 | 用户/节点/服务的健康状态 |
| `Pill "Premium"` | 高倍率节点 tag | 用户付费等级 / 节点 mult tag |
| `Subscription URL` 卡 | 该客户的订阅 URL | n/a (运营者用不到自己的订阅) |
| `Recent activity` | 该客户的近期事件 | **替换为 audit log 最近 10 条** |

### 14 路由映射

| # | Route | 原 Marzneshin | 新设计 |
|---|---|---|---|
| 1 | `/login` | shadcn Card | port `customer-portal/AuthPages.jsx` LoginPage(简化) |
| 2 | `/admins` | DataTable | KPI(总/sudo/最近活动)+ Nodes-style 表 |
| 3 | `/users` | DataTable | KPI(总/活跃/将到期/超额)+ Nodes-style 表 + 行内 RingMeter mini + Pill plan |
| 4 | `/hosts` | DataTable | 改 Nodes-style 表 |
| 5 | `/services` | DataTable | 改 Nodes-style 表 |
| 6 | `/nodes` | DataTable + 日志 | **1:1 design NodesPage** + 日志抽屉 |
| 7 | `/reality` | TargetRow + FindingList | KPI(green/yellow/red)+ 卡片网格(每节点一卡,score Ring + finding list) |
| 8 | `/audit` | filter + table | KPI(总/失败/今日)+ filter card + 表 |
| 9 | `/health` | status grid | **类 Dashboard 主页** — KPI 4 个 + BigChart(健康分趋势)+ 子系统状态卡网格 |
| 10 | `/billing/plans` | DataTable | port `customer-portal/MarketingSections.PricingGrid`(运营者编辑模式) |
| 11 | `/billing/invoices` | DataTable | KPI(MRR/未付/已付)+ Nodes-style 表 |
| 12 | `/billing/purchase` | Form | Card 单列表单 + 选客户 + 选 plan + 一键 credit |
| 13 | `/billing/channels` | Form | 两 Card(TRC20 / EPay)并排 |
| 14 | `/settings` | Form | 分 section Card 列表 |
| + | `/dashboard` 主页 | 简单卡片 | **类 design DashboardPage** — KPI 4 + 主图 BigChart + RingMeter quota + Recent activity(audit) |

### 共享组件层(`dashboard/src/common/components/nilou/`)

新建 fork-only 组件库,从 design 包 jsx 移植:

| 文件 | 来源 | 责任 |
|---|---|---|
| `PanelShell.tsx` | PanelShell.jsx | 整体壳子(sidebar + topbar + main) |
| `PanelHead.tsx` | PanelShell.jsx PanelHead | 页面标题区 |
| `Card.tsx` | PanelShell.jsx Card | 包 cream 卡片 |
| `KPI.tsx` | PanelPages1.jsx KPI | KPI 卡 |
| `Sparkline.tsx` | PanelPages1.jsx Sparkline | mini SVG 图 |
| `RingMeter.tsx` | PanelPages1.jsx RingMeter | 圆环进度 |
| `BigChart.tsx` | PanelPages1.jsx BigChart | 大图(改成 props 收数据) |
| `StatusDot.tsx` | Atoms.jsx StatusDot | 状态点 |
| `Pill.tsx` | Atoms.jsx Pill | 圆角标签 |
| `Row.tsx` | PanelPages1.jsx Row | label/value 行 |
| `LotusMark.tsx` | Atoms.jsx LotusMark | 莲花 logo |

数据形态(对外 prop 类型)保持简单 — `data: number[]` / `percent: number` / `tone: 'emerald' | ...` 等,不绑死任何 API 模型。

### 重写策略 — 数据保留 + UI 替换

每个路由按这个 pattern 重写:

```tsx
// 旧 routes/_dashboard/users.lazy.tsx
function UsersPage() {
  const { data } = useUsers(...)  // ← 原 hook 100% 保留
  return <DataTable data={data} columns={oldColumns} />  // ← 这部分换
}

// 新 routes/_dashboard/users.lazy.tsx
function UsersPage() {
  const { data, kpis } = useUsers(...)  // ← 同 hook,可加 KPI 计算
  return (
    <PanelShell active="/users">
      <PanelHead title="Users" sub="..." actions={<Btn>Add user</Btn>} />
      <KpiGrid kpis={kpis} />
      <Card pad={0}>
        <NodesStyleTable rows={data} columns={newColumns} />
      </Card>
    </PanelShell>
  )
}
```

DataTable 提供的功能(分页 / 排序 / 筛选 / 多选)在 NodesStyleTable 必须保留。第一版若工程量超时,允许保留 TanStack Table 内核,只改样式 — 但视觉必须像 design Nodes 表(StatusDot / 行 hover / 等宽 / hairline border)。

### 路由树整体替换

`dashboard/src/__root.tsx` + `_dashboard.tsx`(layout)整体替换为基于 `PanelShell` 的 layout。原 Marzneshin SidebarLayout 删除。

### 国际化

design 是英文单语,但 dashboard 已接 6 语言(`react-i18next`)。**不退回单语** — 新组件用 i18n key,文案留 8 语言占位(en/ja/zh-cn 必须有,其他用 en fallback)。

## Risks

1. **工程量** — 14 路由 + 11 共享组件 ≈ 40 文件新建/重写 ≈ 3000-4000 LOC
2. **回归** — 现有运营者依赖 dashboard 日常工作,迁移期客户支持可能受影响
3. **TanStack Table 与 Nodes-style 视觉** — TanStack 默认 row hover / sort caret 不符合 design;需要 className 重写或部分手动渲染
4. **i18n 文案缺口** — 新增 KPI label / Pill 文案需要 8 语言 fallback
5. **多 agent 协作冲突** — 14 路由分给多 agent 并行,共享组件库 (`common/components/nilou/`) 必须先 done 才能并行后续路由

## Acceptance

- [ ] 14 个路由全部按 design 视觉重写,**无一遗漏**
- [ ] 所有现有 API hook / mutation 保持调用,无功能减少
- [ ] 新增 design 元素(KPI / Sparkline / RingMeter / BigChart / Pill / StatusDot)在至少 3 个路由中实际渲染并使用
- [ ] `pnpm build` / `pnpm lint` / `pnpm test` 全绿
- [ ] 视觉检查:cream 背景 + Cormorant 标题 + teal 主操作 + gold accent — 每路由抽样 1 张截图对照 design
- [ ] 暗色模式工作正常
- [ ] i18n:en/ja/zh-cn 完整,其他语言至少 fallback 不报错
- [ ] 生产部署后 PostgreSQL / SQLite 两种 DB 路径都能登录到主页

## Kickoff

- Phase 0: 通过本 SPEC ✅(本文件)
- Phase 1: PLAN 拆 wave + agent 分工 → `PLAN-dashboard-rewrite.md`
- Phase 2: TASKS 列原子任务 → `TASKS-dashboard-rewrite.md`
- Phase 3: 主线开 wave-S(共享组件库,串行) — 本会话执行
- Phase 4: spawn N 个 code-generator agent 并行做 wave-A/B/C 各路由,worktree 隔离
- Phase 5: 主线整合(merge worktree → 跑 build/lint/test → 修冲突 → PR)
- Phase 6: 部署 v0.4.6/v0.4.7 → 生产眼检 → 关闭 SPEC

## TBDs(用户确认)

1. **i18n 范围** — 新组件文案是 (a) 仅 en + 自动 fallback, (b) en/ja/zh-cn 必填, (c) 全 8 语言? 推荐 (b),实际操作上每个 agent 加 en + ja + zh-cn key 已经 OK,其他语言后台脚本批量空填。
2. **截止时间** — 全 14 页一次性上,还是 wave-by-wave 增量上(每 wave 一个 PR + tag)? 推荐 wave-by-wave,降低风险。
3. **TanStack Table 取舍** — 保留内核重样式,还是自己写一个简化 Nodes-table 组件? 推荐保留内核(分页/排序逻辑省事),用 wrapper override 视觉。
