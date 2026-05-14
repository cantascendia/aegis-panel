# OPS — Billing Scheduler 运维手册

> **范围**:`ops/billing/scheduler.py` 三个 APScheduler 任务在生产环境的部署、监控、故障排查。
>
> **读者**:运营 / 运维。开发侧 SPEC 见 [SPEC-billing-mvp.md](./SPEC-billing-mvp.md) §A.5,告警 SPEC 见 [SPEC-billing-scheduler-alerting.md](./SPEC-billing-scheduler-alerting.md)。SLO 见 [SLO.md](./SLO.md)。
>
> **配套通道运维**:[OPS-trc20-runbook.md](./OPS-trc20-runbook.md)(TRC20 拉模型)、[OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md)(EPay 推模型)。
>
> **使用方式**:首次部署前通读 §1-§3;日常监控走 §4;故障时按 §5 跳到对应症状。

---

## 1. 三任务总览

`apply_panel_hardening` 注册的 APScheduler 实例运行三个 interval 任务:

| Job ID | 频率(默认)| 作用 | 失败影响 |
|---|---|---|---|
| `aegis-billing-reap` | 60s | `awaiting_payment` → `expired` 清扫 | 用户 UI 显示"超期未支付" 延迟最多 60s |
| `aegis-billing-apply` | 30s | `paid` → `applied`,grant 落 User 表 | **用户已付款但 grant 未发**(钱卡住) |
| `aegis-billing-trc20-poll` | 30s | Tronscan 拉链上 tx → `paid` | TRC20 用户付款延迟 30-60s 入账 |

**最关键**:`aegis-billing-apply`。它是"钱已收"到"用户收益"的最后一公里,任一通道(EPay / TRC20 / admin manual)的 `paid` invoice 都从这里 flush 到用户。

---

## 2. 告警与监控(2026-05-11 起,SPEC-billing-scheduler-alerting)

### 2.1 健康状态语义

`ops/billing/applier_health.py` 暴露三档:

| 状态 | 触发 | 出口 |
|---|---|---|
| OK | 单次成功 `apply_invoice_grant` | metric `applier_lag_seconds` 重置 |
| Degraded | 连续 N 次失败(默认 3,约 90s)`ApplierSkip` 或 `bare Exception` | Telegram 告警**一次**(去抖)+ `applier_alert_active=1` |
| Recovered | 退化后第一次成功 commit | Telegram 恢复消息 + 计数器清零 |

⚠️ **`InvoiceStateError` 不告警**:它是 idempotency 防线(state race)而非真失败,告警会噪声炸营。

### 2.2 Per-reason label

failure 分四个 reason 维度(便于 root-cause 加速):

| Reason | 来源 | 典型根因 |
|---|---|---|
| `user_missing` | `ApplierSkip("user_missing", ...)` | admin 删除了 user 但 invoice 已 paid |
| `plan_missing` | `ApplierSkip("plan_missing", ...)` | 运营改动 plan 表删/重建 |
| `invalid_cart` | `ApplierSkip("invalid_cart:*", ...)` | `compute_user_grant` 校验失败,如 plan 价格变更 |
| `internal` | bare Exception | DB 死锁 / SQLAlchemy 升级 schema mismatch / 不可预见 |

textfile metric(`applier.prom`):

```text
applier_last_success_timestamp        # Unix epoch
applier_lag_seconds                   # since last success
applier_consecutive_failures{reason}  # per-reason counter
applier_alert_active                  # 1 = Telegram fired but not yet recovered
```

### 2.3 部署 textfile collector

复用 `BILLING_TRC20_METRICS_DIR`(OPS-trc20-runbook §5.3),applier.prom 与 trc20_poller.prom 落同一目录:

```bash
# .env 配置(同 TRC20)
BILLING_TRC20_METRICS_DIR=/var/lib/node_exporter/textfile
```

### 2.4 Prometheus 告警示例

```yaml
- alert: BillingApplierStuck
  expr: applier_lag_seconds > 180
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Billing applier has not commit successfully for {{ $value }}s"
    runbook: "docs/ai-cto/OPS-billing-scheduler-runbook.md#5"

- alert: BillingApplierUserMissingSpike
  expr: rate(applier_consecutive_failures{reason="user_missing"}[5m]) > 0.1
  labels:
    severity: warning
  annotations:
    summary: "Applier rejecting due to deleted users — admin operation in progress?"
```

---

## 3. 标准部署流程

通过 `app/marzneshin.py::apply_panel_hardening` 启动时自动注册。无独立部署步骤。验证:

```bash
docker compose logs marzneshin | grep "billing scheduler started"
# 期望: billing scheduler started reap_interval=60s apply_interval=30s trc20_poll_interval=30s
```

**没看到** = `apply_panel_hardening` 没跑 = upstream lifespan 改了,参考 L-016。

---

## 4. 日常监控

### 4.1 关键日志(grep 这些字段)

| 日志 | 含义 | 告警级别 |
|---|---|---|
| `billing applier applied N invoice(s)` | 正常工作 | INFO,周对账时统计 |
| `applier: invoice X skipped (state race)` | idempotency 防线,无影响 | INFO,**不告警** |
| `applier: invoice X skipped (user_missing)` | admin 删了 user | WARN,运营查 audit log |
| `applier: invoice X skipped (plan_missing)` | plan 表被改 | **CRITICAL**,Phase B 商业化期间凡 plan 改动必走 SPEC |
| `applier: invoice X skipped (invalid_cart:*)` | 价格漂移 | WARN,可能 race condition |
| `applier: invoice X failed to apply` | bare Exception,严重 | **CRITICAL**,立即介入 |

### 4.2 业务对账(月度)

```sql
-- 当月所有通道 applied invoice 总览
SELECT
  provider,
  COUNT(*) FILTER (WHERE state = 'applied') AS applied_count,
  COUNT(*) FILTER (WHERE state = 'paid' AND created_at < now() - interval '1 hour') AS stuck_paid_count,
  SUM(total_cny_fen) FILTER (WHERE state = 'applied') / 100.0 AS revenue_cny
FROM aegis_billing_invoices
WHERE created_at >= date_trunc('month', now())
GROUP BY provider;
```

**`stuck_paid_count > 0`** = 有 invoice 卡在 `paid` 超过 1 小时 → §5.2 排查。

---

## 5. 故障排查

### 5.1 Scheduler 没启动

参考 OPS-trc20-runbook §6.2(同根因)。

### 5.2 invoice 卡在 `paid` 状态(未变 `applied`)

**症状**:用户已付款,reaper 没收回,applier 也没 grant。

**SOP**:

1. **查 PaymentEvent**:
   ```sql
   SELECT id, event_type, payload_json, created_at
   FROM aegis_billing_payment_events
   WHERE invoice_id = <id>
   ORDER BY id DESC LIMIT 10;
   ```
   若有 `state_paid` event 但无 `state_applied` event → applier 还没处理或被 `ApplierSkip` 拒绝
2. **查 applier 日志**:
   ```bash
   docker compose logs marzneshin --since 1h | grep "applier: invoice <id>"
   ```
   - `state race` → 罕见,通常自愈,30s 后再查
   - `user_missing` → §5.3
   - `plan_missing` → §5.4
   - `invalid_cart:*` → §5.5
   - `failed to apply` → §5.6
3. **告警是否已触发**:`cat /var/lib/node_exporter/textfile/applier.prom | grep alert_active` 若 = 1,Telegram 应该已经报

### 5.3 `user_missing`(admin 删了 user)

- 这是 **operator 操作错误**:在 paid invoice 存在时硬删了 user
- 应该 grant 退款,但用户已经付了钱 → 协商:重建账号还是 refund
- DB 修补(谨慎):
  - 重建账号:`INSERT INTO users ...` 后 `UPDATE invoice SET user_id = new_user.id` + 手动 `apply_manual`(admin endpoint)
  - Refund:走 §OPS-trc20-runbook §8(链上发还)或 EPay 后台

### 5.4 `plan_missing`(plan 表被改)

- Plan 表 ID 主键 immutable 假设被破坏
- 立刻停 plan 表所有写操作
- DB 修补:重建 plan,ID 对回原值,`UPDATE invoice_lines SET plan_id = new_plan.id`
- 改完后 admin `apply_manual` 处理积压 invoice

### 5.5 `invalid_cart:*`

- 通常 `compute_user_grant` 在 plan 价格 / GB / days 与 invoice line 现存 quantity 不匹配时抛出
- 检查 invoice line 的 `quantity` 与当前 plan 字段是否一致
- 若 plan 已涨价但用户 invoice 没变 → 信任 invoice(用户付的是旧价格),手动 admin grant 等值

### 5.6 `failed to apply` bare Exception

- 罕见,通常 = DB 异常 / SQLAlchemy 升级 / 不可预见 schema mismatch
- 立刻看 panel 完整 traceback
- 如果反复,临时 `BILLING_APPLY_INTERVAL=999999` 停 applier,人工 `apply_manual` 处理直到根因修复
- 升 incident,通知 CTO

### 5.7 重复处理(idempotency 防线触发)

- 看到 `applier: invoice X skipped (state race)` 是**预期**的
- 多 worker 部署(蓝绿)时 SKIP_LOCKED 起作用,只一个 worker 真 apply
- 不需要任何操作

---

## 6. 周期维护

### 6.1 每周

- 查 `applier.prom` 文件 mtime — 应该每 30s 刷新一次,超过 5 min stale = scheduler 死
- 查 stuck_paid_count(§4.2)— 应该 = 0

### 6.2 每月

- 跑 §4.2 SQL,核对 provider 分布与 PaymentEvent 计数
- 跑 cross-check:`SELECT COUNT(*) FROM aegis_billing_payment_events WHERE event_type = 'state_applied'` 应等于 invoice `state = 'applied'` 的 count

### 6.3 升级 SQLAlchemy / Alembic 时

- bare Exception 风险升高,**升级前**临时降低 `BILLING_ALERT_THRESHOLD = 2`,加敏感度
- 升级后跑全套 billing pytest 套件
- 1 周后回 default 3

---

## 7. 紧急 SOP

### 7.1 Scheduler 完全死(applier 30 分钟无 commit)

1. `docker compose restart marzneshin`(优先)
2. 不行 → 查 `app/marzneshin.py:apply_panel_hardening` 是否被 upstream 改写
3. 手工 `python -c 'from ops.billing.scheduler import _apply_paid_invoices_inner; from app.db import GetDB; print(_apply_paid_invoices_inner(GetDB().__enter__()))'` 验证逻辑可跑
4. 极端情况:`apply_manual` admin endpoint 逐个手工 apply(慢但稳)

### 7.2 大规模 `internal` 失败(>50 invoice 卡 paid)

- 停 scheduler(`BILLING_APPLY_INTERVAL=999999`),防越陷越深
- 拉一份 paid invoice 全量 dump
- 让 CTO + DBA 介入,**不要**主线 yolo 改

---

## 8. 已知限制

- **告警仅 Telegram**:Phase B 期间 operator 单人值守。未来 multi-on-call 应接 PagerDuty(留 Phase C)
- **Per-reason metric 是 deque-based**:进程内统计,重启清零。Prometheus rolling window 是真相,本地 metric 是 hint
- **bare Exception** 分类粗:`internal` 概括太宽,Phase C 起逐步细化为 `db_deadlock` / `schema_mismatch` / `unknown` 三档

---

## 9. 关联文档

- [SPEC-billing-mvp.md](./SPEC-billing-mvp.md) §A.5 — applier 设计契约
- [SPEC-billing-scheduler-alerting.md](./SPEC-billing-scheduler-alerting.md) — 本告警体系 SPEC(实施中)
- [SLO.md](./SLO.md) — billing.apply_latency / billing.apply_failure_rate
- [OPS-trc20-runbook.md](./OPS-trc20-runbook.md) — 同源告警通道(trc20_health.py)
- `ops/billing/scheduler.py` + `applier_health.py`(实施后)— 代码权威
