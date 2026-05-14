# SPEC — TRC20 Poller Health Alerting (P0 Reliability Fix)

> **Status**: DRAFT — 2026-05-11，by CTO（Opus 4.7 1M）
> **Trigger**: reliability-auditor 2026-05-11 audit（score 63/100），TRC20 poller silent-failure 列为 #1 blocker
> **Scope**: `ops/billing/trc20_poller.py` + `ops/billing/trc20_health.py`（新）
> **Forbidden path**: `**/billing/**` → 必须双签 + `requires-double-review` 标签（手册 §32 / 铁律 #15）
> **Constitution**: 服务 §43 reliability + §A.3 TRC20 通道契约

---

## 1. Context

**问题**：[ops/billing/trc20_poller.py](../../ops/billing/trc20_poller.py) 当前 8 个 try/except + 6 个 logger.* 调用，**零告警出口**。Tronscan API 持续宕机 / 限流 / 证书过期时，行为：

```text
[WARN] trc20 poller: tronscan fetch failed, skipping: <exc>
[WARN] trc20 poller: tronscan fetch failed, skipping: <exc>
[WARN] trc20 poller: tronscan fetch failed, skipping: <exc>
... (30s 一次，永远不停)
```

操作员看不见，用户付了 USDT 但状态停在 `awaiting_payment` → 用户超时投诉 → 退款 → Phase B 商业化信任崩盘。

**业务窗口**：Phase B 本周提交 Paddle/LS/Stripe，TRC20 当前 1 个活跃客户（nilou_trial01），未来 2 周预计扩到 5-10 客户。**此修复必须先于 Phase B 上线**。

**现有基础设施**：
- `app/notification/telegram.py` — `send_message()` 复用，无需新建
- `BILLING_TRC20_*` 配置体系完备（[trc20_config.py](../../ops/billing/trc20_config.py)）
- OPS-trc20-runbook.md §5.1 已规定**日志级别 → 告警等级**契约，但无落地实现

---

## 2. What（验收功能）

| # | 行为 | 验收 |
|---|---|---|
| F1 | poller 每次成功 fetch transfers 时记录 `last_success_at` | tick 成功后 health 状态变 `OK`，metric `trc20_poller_last_success_timestamp` 更新 |
| F2 | 连续 N 次（默认 3）`Trc20ClientError` 触发 Telegram 告警 | 第 3 次失败后 `send_message()` 被调用一次；第 4 次失败**不**重发（去抖） |
| F3 | API 恢复后下一次成功 tick 发送 recovery 告警 | "TRC20 poller recovered after N failures" 类消息 |
| F4 | textfile collector 产出 `trc20_poller_lag_seconds` 指标 | 文件路径 `BILLING_TRC20_METRICS_DIR / trc20_poller.prom`，可被 node_exporter `--collector.textfile.directory` 读取 |
| F5 | 配置项 env-driven，默认安全 | `BILLING_TRC20_ALERT_THRESHOLD=3`、`BILLING_TRC20_METRICS_DIR=`（空 = 禁用文件输出，不破坏现有部署）|

---

## 3. Why（设计取舍）

| 选择 | 取舍 | 拒绝的替代 |
|---|---|---|
| **In-memory 状态**（非 DB 列） | 简单，无 schema 迁移，重启即清零（重启已是 ops 介入信号）| DB 列：需 Alembic 迁移 + L-014 aggregator 改动，触及 forbidden path 面更大 |
| **复用现有 `aiogram`** | `app/notification/telegram.py.send_message()` 已经在用 | 不引入新依赖（reliability-auditor 报告强调） |
| **textfile collector 而非 prometheus_client** | 不引入新 Python 依赖，本地落盘最简单 | prometheus_client：需 HTTP exporter port + 部署改动 |
| **N=3 阈值（约 90s）** | 与 §5.1 runbook "持续 > 10 分钟告警" 比偏激进 | 因 Phase B 商业化敏感，宁愿 false-positive |
| **不告警于 `InvoiceStateError`** | 它是 idempotency 防线，每次重 poll 触发都是预期 | 告警于此 = 噪声炸营 |
| **告警仅出口 = Telegram** | 与现有 operator notification 同通道，operator 已订阅 | 邮件 / Sentry：未配置，引入冷启动成本 |

---

## 4. How（实施设计）

### 4.1 新模块 `ops/billing/trc20_health.py`

```python
# 状态容器（singleton 模块级变量）
_state = {
    "consecutive_failures": 0,
    "alert_sent": False,           # 去抖标志
    "last_success_at": None,       # datetime | None
    "last_failure_at": None,
    "last_failure_reason": "",
}

async def record_success(*, now=None) -> None:
    """Called by poller after successful Tronscan fetch.

    Resets failure counter; if alert had been sent, fires a recovery message.
    Writes the textfile metric snapshot.
    """

async def record_failure(reason: str, *, now=None) -> None:
    """Called by poller on Trc20ClientError.

    Increments counter; at threshold, calls send_message() once.
    Subsequent failures are silent (debounced) until record_success resets.
    Writes the textfile metric snapshot.
    """

def _write_metrics_file(now: datetime) -> None:
    """Emit prom-textfile-format snapshot, atomic write (tmp + rename).

    Only writes if BILLING_TRC20_METRICS_DIR is set (opt-in for ops who
    haven't wired node_exporter yet).
    """

def _reset_for_tests() -> None:  # test hook
```

**Metric format**（textfile collector spec）:
```
# HELP trc20_poller_last_success_timestamp Unix epoch of last successful Tronscan fetch.
# TYPE trc20_poller_last_success_timestamp gauge
trc20_poller_last_success_timestamp 1746950400.0
# HELP trc20_poller_lag_seconds Seconds since last successful poll.
# TYPE trc20_poller_lag_seconds gauge
trc20_poller_lag_seconds 95.0
# HELP trc20_poller_consecutive_failures Number of consecutive Tronscan failures.
# TYPE trc20_poller_consecutive_failures gauge
trc20_poller_consecutive_failures 3
```

### 4.2 修改 `trc20_poller.py`

仅 `run_poll_trc20_invoices` 改动（~15 行），`_poll_trc20_invoices_inner` **不动**（保持纯函数 / 易测）：

```python
async def run_poll_trc20_invoices() -> int:
    ...
    if not BILLING_TRC20_ENABLED:
        return 0

    transfers: list[Trc20Transfer] = []
    try:
        async with TronscanClient.from_env() as client:
            transfers = await client.list_recent_transfers(...)
    except Trc20ClientError as exc:
        logger.warning(...)
        await record_failure(reason=str(exc))   # NEW
        return 0
    await record_success()                       # NEW
    ...
```

### 4.3 新配置项 `trc20_config.py`

```python
BILLING_TRC20_ALERT_THRESHOLD: int = int(
    config("BILLING_TRC20_ALERT_THRESHOLD", default=3)
)
BILLING_TRC20_METRICS_DIR: str = config(
    "BILLING_TRC20_METRICS_DIR", default=""
)
```

### 4.4 测试 `tests/test_billing_trc20_health.py`

| 用例 | 验证 |
|---|---|
| `test_first_two_failures_no_alert` | failure×2 → `send_message` not called |
| `test_third_failure_fires_alert` | failure×3 → `send_message` called exactly once |
| `test_fourth_failure_debounced` | failure×4 → `send_message` still called only once (no re-alert) |
| `test_success_after_failure_clears_state` | failure×3 + success → recovery message + counter reset |
| `test_success_without_prior_alert_no_recovery_msg` | failure×1 + success → no msg (only counter reset) |
| `test_metrics_file_written_when_dir_set` | tmp dir → `.prom` file exists with expected gauges |
| `test_metrics_file_skipped_when_dir_empty` | dir="" → no file written, no error |
| `test_lag_seconds_increases_on_failure` | failure × 3 → lag_seconds reflects time since last success |
| `test_concurrent_calls_safe` | asyncio.gather record_failure × 3 → exactly 1 alert (lock protects) |

外加 `test_billing_trc20_poller.py` 新增：
- `test_run_poll_calls_record_success_on_clean_tick`（mock TronscanClient）
- `test_run_poll_calls_record_failure_on_client_error`

### 4.5 OPS runbook 更新

[OPS-trc20-runbook.md](./OPS-trc20-runbook.md) §5 增加新小节：
- §5.4 — 告警 / textfile collector 配置
- §6.1 mitigation 流程改为"等告警触发后操作"而非靠 grep 日志

---

## 5. Risks

| 风险 | 缓解 |
|---|---|
| Telegram bot 自身宕机 → 告警丢失 | `send_message` 已有 try/except + logger.error，不会让 poller crash |
| 多 worker 部署（蓝绿）→ 双告警 | scheduler max_instances=1 + 模块级 state 单进程内；多进程时 alert 频次 ≤ worker 数（可接受）|
| 关 `BILLING_TRC20_ENABLED` 后 state 卡在 3 | F1 不会触发（已 return 0 在前），但模块级 state 会保留旧值 → 重启清除；不视为 bug |
| textfile 落盘失败（权限 / 磁盘满）| `_write_metrics_file` 内 try/except + log，绝不让 poller crash |
| 单测污染（模块级 state）| `_reset_for_tests` + autouse fixture |

---

## 6. Acceptance Criteria

- [x] SPEC + PLAN + TASKS（本文件，本节完成）
- [ ] `ops/billing/trc20_health.py` 新模块（≤ 150 行）
- [ ] `ops/billing/trc20_poller.py` 改动 ≤ 5 行（仅 `run_poll_trc20_invoices`）
- [ ] `ops/billing/trc20_config.py` 增加 2 个 env var
- [ ] `tests/test_billing_trc20_health.py` 9 个用例全 pass
- [ ] `tests/test_billing_trc20_poller.py` 新增 2 个用例 pass
- [ ] mutation gate ≥ 80%（健康模块新增代码）— 用 hand-checked surviving-mutant list 替代（项目无 mutmut CI）
- [ ] OPS-trc20-runbook.md §5.4 新章节
- [ ] PR 标签：`requires-double-review`、`reliability`、`forbidden-path`
- [ ] CI 全绿（pytest tests/test_billing_trc20_*.py）

---

## 7. PLAN（拆分依赖图）

```
T1 trc20_health.py（独立模块） ─┐
T2 trc20_config.py（2 env vars）─┼─→ T4 wire into run_poll_trc20_invoices
T3 test_billing_trc20_health.py ─┘
                                  ↓
                            T5 test additions to test_billing_trc20_poller.py
                                  ↓
                            T6 OPS runbook §5.4 update
                                  ↓
                            T7 commit + PR
```

## 8. TASKS（atomic）

| ID | 内容 | 文件 | 预计 LoC |
|---|---|---|---|
| T1 | trc20_health 模块 + send_message 集成 + textfile writer | `ops/billing/trc20_health.py`（新）| ~130 |
| T2 | 2 个 env vars | `ops/billing/trc20_config.py` | +6 |
| T3 | 健康模块 9 个测试用例 | `tests/test_billing_trc20_health.py`（新）| ~200 |
| T4 | `run_poll_trc20_invoices` 接入 record_success / record_failure | `ops/billing/trc20_poller.py` | +5 |
| T5 | 2 个 poller 集成测试 | `tests/test_billing_trc20_poller.py` | +60 |
| T6 | OPS-trc20-runbook §5.4 | `docs/ai-cto/OPS-trc20-runbook.md` | +40 |
| T7 | git commit + PR + 标签 | — | — |
