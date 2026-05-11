# Aegis Panel — Backend SLO（billing / scheduler / TRC20）

> **状态**：DRAFT — 2026-05-11，by CTO（Opus 4.7 1M）
> **触发**：reliability-auditor 2026-05-11 wave-14 R2（score 71/100），列 `docs/ai-cto/SLO.md` 为 P1 缺口；Phase B 商业化（Paddle/LS/Stripe）几天内启动，cutover 前必须冻结 SLO。
> **Scope**：billing apply / scheduler / TRC20 poller / webhook 后端子系统。Customer-portal SPA 侧 SLO 见 [PORTAL-RELIABILITY.md §7](./PORTAL-RELIABILITY.md#7-监控与-sloP3-起)，本文件**不重复**。
> **关联**：[SPEC-trc20-poller-alerting.md](./SPEC-trc20-poller-alerting.md)（PR #256，textfile metrics 来源）/ [SPEC-billing-scheduler-alerting.md](./SPEC-billing-scheduler-alerting.md)（applier 健康监控）/ [OPS-trc20-runbook.md](./OPS-trc20-runbook.md) §5-§6 / 铁律 #12 eval-gate / 手册 §43。
> **责任人现状**：项目当前仅 1 个 CTO+operator。所有 SLO 责任人 = CTO；未来扩 SRE 团队时按 §6 流程移交。

---

## 0. 总体原则

- **Error budget = 28-day rolling**（不复位窗口，避免月初挥霍）
- 阈值分两档：**target**（SLO 承诺）、**alert threshold**（Telegram 告警触发点，比 target 更严，留缓冲）
- 数据源仅限**已实现 / 本 SPEC 周期内将实现**的 metric；不规划尚无 backing 的指标
- 告警出口统一 Telegram（`app/notification/telegram.py.send_message()`，与 operator 现有订阅同通道）
- 任何 SLO violation → 必须在 28 天内 root-cause 写入 LESSONS.md（铁律 #4）

---

## 1. SLO 表

### 1.1 `billing.apply_latency` — paid → applied 用户感知延迟

| 项 | 值 |
|---|---|
| **定义** | invoice 从 `paid` 状态进入到 `applied` 状态的耗时（scheduler `_apply_paid_invoices_inner` 每分钟扫描，最坏延迟≈1 min + apply 耗时）|
| **数据来源** | DB query：`SELECT EXTRACT(EPOCH FROM applied_at - paid_at) FROM invoices WHERE applied_at >= now() - interval '28 days'`（无 textfile metric，靠周报脚本聚合）|
| **Target** | p95 < 90 s ; p99 < 180 s |
| **Alert threshold** | p95 > 120 s 持续 10 min → Telegram |
| **Error budget** | 28 天内 < 5% 的 invoice 超 180 s |
| **责任人** | CTO（兼 operator）|
| **Runbook** | OPS-billing-scheduler-runbook §3（待 SPEC-billing-scheduler-alerting 落盘）|

### 1.2 `billing.apply_failure_rate` — applier 失败率（按 reason 分桶）

| 项 | 值 |
|---|---|
| **定义** | `_apply_paid_invoices_inner` 失败次数 / 总尝试次数，按 `ApplierSkip.reason ∈ {user_missing, plan_missing, invalid_cart, internal}` 分桶 |
| **数据来源** | textfile collector：`applier_failures_total{reason="..."}` + `applier_apply_total`（由 SPEC-billing-scheduler-alerting `ops/billing/applier_health.py` 输出至 `BILLING_TRC20_METRICS_DIR/applier.prom`）|
| **PromQL** | `rate(applier_failures_total[5m]) / rate(applier_apply_total[5m])` |
| **Target** | `user_missing` + `plan_missing` 合计 < 0.5%（数据完整性，不应失败）; `internal` < 0.1%（bug / DB 抖动）; `invalid_cart` 不计入 budget（用户输入错误）|
| **Alert threshold** | `internal` 连续 3 次 OR `user_missing` 连续 3 次 → Telegram（去抖一次性告警，复用 PR #256 PollerHealth 模板）|
| **Error budget** | 28 天内 `internal` 失败 ≤ 5 起 |
| **责任人** | CTO |
| **Runbook** | OPS-billing-scheduler-runbook §3.1（reason 分诊表）|

### 1.3 `billing.trc20_lag` — TRC20 poller 上次成功 fetch 时延

| 项 | 值 |
|---|---|
| **定义** | 当前时刻距上次 `run_poll_trc20_invoices` 成功完成 Tronscan fetch 的秒数 |
| **数据来源** | textfile collector：`trc20_poller_lag_seconds`（PR #256 `ops/billing/trc20_health.py` 已实现，落盘到 `BILLING_TRC20_METRICS_DIR/trc20_poller.prom`，由 node_exporter `--collector.textfile.directory` 暴露）|
| **PromQL** | `trc20_poller_lag_seconds` |
| **Target** | p95 < 90 s（poll interval 30 s × 3）|
| **Alert threshold** | > 120 s 持续 90 s（≈3 次连续失败）→ Telegram；同时 `trc20_poller_consecutive_failures >= 3` |
| **Error budget** | 28 天内累计 lag > 600 s 时间窗 ≤ 30 min（≈99.93% 可用）|
| **责任人** | CTO |
| **Runbook** | [OPS-trc20-runbook §6.1](./OPS-trc20-runbook.md)（Tronscan 4xx/5xx 排查 + fallback 到 Trongrid）|

### 1.4 `billing.webhook_5xx_rate` — EPay / MoR webhook 5xx 率

| 项 | 值 |
|---|---|
| **定义** | `/api/v1/billing/webhook/{epay,paddle,lemonsqueezy,stripe}` 后端返回 5xx 的比例（4xx 视为上游签名错误，不计入 SLO）|
| **数据来源** | app log → 周报脚本聚合（**Phase B 当前实现**）；P3 计划接 OpenTelemetry exporter 后改 PromQL（**Phase B 不阻塞**）|
| **Phase B PromQL（log-based）** | `grep -c 'webhook.*5[0-9][0-9]' /var/log/aegis/app.log` per hour |
| **Target** | 5xx 率 < 0.5%（任何单一 webhook endpoint）|
| **Alert threshold** | 单一 endpoint 5 min 内 ≥ 3 起 5xx → Telegram |
| **Error budget** | 28 天内单一 endpoint 5xx ≤ 50 起 OR < 1% 总请求量（取小者）|
| **责任人** | CTO（Paddle/LS/Stripe MoR 通道激活时同步生效）|
| **Runbook** | OPS-epay-vendor-guide §4（EPay）+ 待补 OPS-mor-runbook §3（MoR，Phase B ship 后）|

---

## 2. 数据采集架构（现状）

```
┌─ ops/billing/trc20_health.py ──┐
│  trc20_poller_lag_seconds      │
│  trc20_poller_consecutive_     │──→ ${BILLING_TRC20_METRICS_DIR}/
│   failures                     │      trc20_poller.prom
│  trc20_poller_last_success_ts  │      applier.prom (待 SPEC-billing-scheduler-alerting)
└────────────────────────────────┘            │
                                              ↓
                                      node_exporter --collector.textfile
                                              ↓
                                      Prometheus scrape (待部署，Phase B+1 周)
                                              ↓
                                      Grafana dashboard (留下一个 PR — 不在本 SLO 范围)
```

**当前 gap**：Prometheus / Grafana 自身尚未部署，textfile metric 落盘但无 scrape 端。**临时手段**：CTO 每日 09:00 JST 手动 `cat $METRICS_DIR/*.prom`；告警仍走 Telegram（PR #256 已 wire）。Prometheus 接入留 D-021 决策。

---

## 3. SLO 复核节奏

| 周期 | 动作 | 责任人 |
|---|---|---|
| 每周一 09:00 JST | 跑 `scripts/slo_weekly.py`（待 PR）汇总四个 SLO 数据，对照 target / budget | CTO |
| 每月初 | 若上月任一 SLO violation → 写入 LESSONS.md（铁律 #4）+ 评估是否调整 target | CTO |
| 每季度 | 全表复审：是否引入新 SLO（webhook latency / portal API p95 已在 PORTAL-RELIABILITY）；阈值是否过紧/过松 | CTO |
| MoR 通道激活 | §1.4 webhook_5xx_rate 拆分到 per-vendor；OPS-mor-runbook 同步落盘 | CTO |

---

## 4. Out of scope（明确不承诺）

- **Marznode gRPC 可用性 SLO**：单个节点宕机由 dashboard 操作员监控，非用户感知关键路径（用户已订阅其他节点）。Phase C 多节点编排时再立 SPEC
- **Portal LCP / API latency**：见 PORTAL-RELIABILITY §7，本文件不重复
- **DB query p99**：项目规模 < 200 用户，DB 不是瓶颈；> 500 用户时再立 SLO
- **TRC20 链上确认延迟**：链外因素，operator 不可控；OPS-trc20-runbook §6 仅作排查指引
- **EPay 码商可用性**：码商侧 SLA 由合同约束，非本面板控制；webhook_5xx 已覆盖 panel 侧承诺

---

## 5. 引用与依赖

- 数据契约：[SPEC-trc20-poller-alerting.md §4.1](./SPEC-trc20-poller-alerting.md) metric 格式 / [SPEC-billing-scheduler-alerting.md §4.2](./SPEC-billing-scheduler-alerting.md) applier metric
- Runbook：[OPS-trc20-runbook.md §5-§6](./OPS-trc20-runbook.md)
- Constitution：[CONSTITUTION.md](./CONSTITUTION.md) §43 reliability 第 4 条要求"所有付款相关子系统必须有可量化 SLO"
- Forbidden path：`**/billing/**` 改动触及本 SLO 表的 metric 定义时必须更新 §1 对应行

---

## 6. 修订历史

| 日期 | 变更 | 触发 |
|---|---|---|
| 2026-05-11 | 初版 DRAFT，4 个 SLO domain | wave-14 R2 reliability-auditor（score 71/100）|
