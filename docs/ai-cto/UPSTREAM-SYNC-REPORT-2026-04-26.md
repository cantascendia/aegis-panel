# Upstream sync 报告 — 2026-04-26

> 周期性盘点 `marzneshin/marzneshin` 自我们 fork 点(`d3b25e2`,2025-10-02)
> 以来的活动。下次 sync 报告:**2026-07-26**(每季度)。
>
> 本文件留档,用于 quarter-by-quarter delta 对比。

---

## TL;DR(一句话)

**Upstream Marzneshin 实质 dormant** —— 6 个月 24 天里只有 **2 个 commit**(都是 fork 当天的 hotfix),最后官方 release `v0.7.4` 已经 **9.5 个月前**。Sync 风险接近零;**继续按 hard-fork 独立运营是正确战略**。

---

## 数据(GitHub API,2026-04-26 抓取)

### Repo 整体

| 指标 | 值 |
|---|---|
| `archived` | **false** |
| 最后 push | **2025-10-04T03:24:11Z**(7 个月前) |
| Stars | 677(fork 时 ~673,几乎无增长) |
| Forks | 107 |
| Open issues | **128**(社区在提,维护者不响应) |
| Open PRs | **10**(最早 2025-08-01,无人合) |

### 自 fork 点 `d3b25e2`(2025-10-02)以来的所有 commit

```
2025-10-03  d3b25e2  Update admin.py (#911)         ← fork 点本身
2025-10-03  1512b6b  Fix cli commands error (#915)
2025-10-03  00ca64e  fix(routes): check websocket is running (#916)
```

**只有 2 个 commit 在 fork 之后**,都在 fork 后 24 小时内,都是 fix。**6 个月没有 feat / 重构 / 安全更新**。

### Release / 版本节奏

| 版本 | 日期 | 距今 |
|---|---|---|
| v0.7.4 | 2025-07-12 | **9.5 个月** |
| v0.7.3 | 2025-03-06 | 13 个月 |
| v0.7.2 | 2025-02-12 | 14 个月 |
| v0.7.1 | 2025-02-12 | — |
| v0.7.0 | 2024-12-28 | — |

**过去 6 个版本平均节奏 ~6 周一次**(2024-12 到 2025-07);**自 v0.7.4 起完全停摆**。

### `nightly` 标签

- tag: `nightly`,target_commitish: `2106a2d`
- created_at: 2025-10-03(同 fork 当天)
- 最新 build 名: "Marzneshin nightly release 20260426"
- **解读**:GitHub Actions 的 nightly artifact 重建管线还在跑(每天打新 zip),但**指向的 commit 自 2025-10 起没动**。是 CI 假象,不是真活动。

### 最近开 issue(全部仍 open)

| # | 日期 | 标签 | 标题 |
|---|---|---|---|
| #930 | 2026-02-23 | bug | [BUG] Xhttp |
| #910 | 2025-09-13 | bug | [BUG] Nodes not connect |
| #884 | 2025-07-26 | feature | [FEAT] ECH support |
| #883 | 2025-07-16 | feature | [FEAT] proxySetting in sub config |

**社区仍在提 issue + 提 PR;维护者 6 个月未回应**。这是 abandonware-in-progress 的标准模式。

---

## 我们 fork 状态对比(自 fork 点起)

aegis-panel 在过去 6 个月 24 天合并 PR **#1 ~ #71 共 71 个**(其中 71 个 squash + 部分 docs-only)。差异化 #1 SNI 选型器 + 计费数据面 + IP 限制 MVP + 安全基线 + CI infra + 多 session 协作 framework + Round 1 leftover 全清,**远超 upstream 的 0 commit**。

实际上**我们已经从"fork"变成"独立项目"**,只是 git 历史里仍以 d3b25e2 为根。

---

## 战略意涵

### 1. Sync 风险 ≈ 0,但不变维护成本不为 0

- **没有需要从 upstream 拉的代码**(2 个 hotfix 已审,与我们已修内容无重复)
- 但**我们仍要单方向"看一眼"**(每季度),原因:
  - 偶有用户在 upstream 提的 bug 也影响我们(本次 #930 Xhttp、#910 Nodes 都要核实)
  - upstream 偶尔被外部贡献者醒一下(罕见但不能 0 概率)

### 2. L-022 条件 #3 "upstream 会做相同事" 需要修订

L-022 第 3 条说"打破 'session 0 不改 upstream' 默认规则的硬条件之一是 'upstream 早晚必须做'"。当 upstream **实质 dormant** 时这条件**永远不会被满足** —— 我们成为事实 fork 主体,upstream "不会 eventually 做",只会"永不做"。

**修订意见**:L-022 第 3 条改为"upstream **如果还活着** 早晚必须做;如果 upstream dormant > 12 个月,本条豁免,只需第 1 + 第 2 条"。需要单独 LESSONS update PR,本报告不动 LESSONS.md(报告专注数据 + 战略,不做规则迭代;后续按需 follow up)。

### 3. v2share 评估(D-013)结论加固

v2share 维护者 = Marzneshin 维护者(`khodedawsh`),v2share 14 个月无 commit + Marzneshin 7 个月无 commit ⇒ **同一 dormancy 模式**。D-013 的 "vendor hedge plan" 不再是"备胎",而是"半备战" —— 如果 12 个月后 upstream 仍 dormant,直接触发 vendor PR(把 v2share 拷进 `vendor/` 取得编辑权)。

### 4. Round 4 商业化的反向影响

- **品牌定位**:产品如果出去,不能再说"based on Marzneshin"或"successor to Marzneshin",而是"originally forked from Marzneshin which is now dormant"。这影响 README / NOTICE.md 的措辞
- **License 风险**:upstream dormant 状态下,任何 license 变更(maintainer 突然 archive 仓库 / 改 license)都要我们独立应对。**当前 AGPL-3.0 的代码我们已合规承担,upstream 怎么处置我们 fork 都不受影响**(D-002 + NOTICE.md 已固化)
- **市场机会**:Hiddify-Manager 8.7k stars 仍活跃 + Marzneshin 677 stars dormant,我们如果做出 v1.0 + 商业化稳定,**有机会成为 "Marzneshin 继任者" 的事实承接者**(类似 Marzneshin 当年继承 Marzban 的剧本)

---

## 行动项

### 立即(本 PR 范围)

- ✅ 本报告归档,作为 quarter baseline
- ✅ STATUS.md 添加一条引用

### 短期(下次 round 决策时)

- ⏳ L-022 条件 #3 修订(单独 PR,半个章节)
- ⏳ NOTICE.md / README 措辞复审,看是否要降低对 upstream 的"承接"语气
- ⏳ v2share D-013 复评提前到 2026-07-26(同下次 sync 报告日期),不再等 10-26

### 长期(2026-Q4 触发条件)

- 若 upstream 12 个月仍 dormant(2026-10-04 后):触发 v2share vendor PR(D-013 第 4 点的硬条件之一)
- 若 upstream 突然复活:本报告基线作废,按届时 commit 数重写策略

---

## 复评程序

下次 S-O 触发(2026-07-26 ± 1 周)按以下顺序更新本文件,而非新建报告:

1. 用 `gh api 'repos/marzneshin/marzneshin/commits?since=2025-10-02T00:00:00Z'` 抓 commit list,与本报告"自 fork 点起"一节对比
2. 用 `gh api 'repos/marzneshin/marzneshin/releases'` 看是否新 release
3. 在本文件底部追加 `## 2026-07-26 Update` 段,只写 delta
4. 如出现"upstream 复活"信号(≥5 commits / 1 release),重新评估 L-022 / D-013 / NOTICE 措辞

---

_2026-04-26 初版,基于 GitHub API quarter snapshot。下次更新人:把"数据"段重新抓一遍,delta 写到底部不删旧。_
