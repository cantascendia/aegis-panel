# SPEC — Billing Scheduler Silent-Failure Parity (P0 Reliability Fix #2)

> **Status**: DRAFT — 2026-05-11，by CTO（Opus 4.7 1M）
> **Trigger**: reliability-auditor 2026-05-11 wave-14 R2（score 71/100，TRC20 修复后暴露同构兄弟问题）
> **Sibling**: [SPEC-trc20-poller-alerting.md](./SPEC-trc20-poller-alerting.md)（PR #256，已 ship 等待双签）
> **Forbidden path**: `**/billing/**` → `requires-double-review` 标签 + 双签
> **Constitution**: §43 reliability + §A.5 scheduler 契约

---

## 1. Context

**问题**：[ops/billing/scheduler.py:253-263](../../ops/billing/scheduler.py) 的 `_apply_paid_invoices_inner` 三个 except 分支与 TRC20 poller R1 缺陷同构：

```python
except InvoiceStateError as exc:
    db.rollback()
    logger.info(...)
except ApplierSkip as exc:
    db.rollback()
    logger.warning("applier: invoice %s skipped (%s): %s", ...)
except Exception:  # pragma: no cover — defensive
    db.rollback()
    logger.exception("applier: invoice %s failed to apply", invoice.id)
```

**影响面比 TRC20 R1 缺陷更大**：
- `_apply_paid_invoices_inner` 是**三通道共用**（EPay webhook → paid → applier；TRC20 poller → paid → applier；admin manual → paid → applier）
- 一个 `ApplierSkip(user_missing/plan_missing/invalid_cart)` 永远卡 invoice 在 `paid` 状态，operator 不会被告警
- `bare Exception` 分支同样静默

**业务窗口**：与 PR #256 同节奏 — Phase B 商业化几天内。MoR 通道（Paddle/LS/Stripe）一旦审批通过即 ship，应用层错误若不被告警 = 用户付款成功但 grant 永远未发。

**复用模板**：PR #256 引入的 `ops/billing/trc20_health.py` 模式（模块级 state + asyncio.Lock + 去抖 Telegram + 原子 textfile 落盘）100% 适用。本 SPEC 抽出通用基础设施 `ops/billing/poller_health.py`，TRC20 + applier 都接入。

---

## 2. What

| # | 功能 | 验收 |
|---|---|---|
| F1 | 抽通用 `PollerHealth` 基类，参数化 metric 名前缀 / 告警 emoji / runbook 链接 | `trc20_health` + `applier_health` 都通过基类构造 |
| F2 | `_apply_paid_invoices_inner` 每个失败分支调用 `applier_health.record_failure(reason)` | `ApplierSkip` / `bare Exception` 触发 |
| F3 | 连续 N 次失败（默认 3）→ Telegram 告警 + textfile metric `applier_failures_total{reason}` 增量 | Phase B-aggressive 阈值 |
| F4 | applier 成功 commit 时 `record_success`，去抖标志清零 | 与 TRC20 一致语义 |
| F5 | Per-reason 计数（`user_missing` / `plan_missing` / `invalid_cart` / `internal`）暴露在 textfile，便于 Prometheus 多维聚合 | label 设计 |

**Out of scope**：
- EPay webhook 失败告警 — 该路径走 webhook handler，已有 4xx/5xx 上游告警面，本 SPEC 不重复
- `_reap_expired_invoices_inner` 告警 — 失败 ≠ 钱卡住，优先级 P2，留下个 PR
- Admin manual apply 失败 — 同步 HTTP 调用，admin 直接看 4xx，无需异步告警

---

## 3. Why（设计取舍）

| 选择 | 取舍 | 拒绝的替代 |
|---|---|---|
| **抽 `PollerHealth` 基类**（在 trc20_health 之上 refactor）| 减少 ~60% 重复代码；两个监控点行为对齐 | 复制粘贴：维护双份逻辑（fix bug 要改两地） |
| **per-reason label**（`user_missing` / `plan_missing` / `invalid_cart`）| Prometheus 多维聚合，operator 一眼看到根因 | 单一计数：盲点 |
| **不告警 InvoiceStateError** | 与 TRC20 一致，state race 是 idempotency 防线 | 噪声炸营 |
| **告警阈值复用 BILLING_TRC20_ALERT_THRESHOLD** | 减少 env vars 蔓延 | 独立 var：增加运维认知负载 |
| **textfile 路径独立**（`scheduler_apply.prom`）| node_exporter 单一目录扫多文件 | 同一文件多 metric：文件锁竞争 |

---

## 4. How

### 4.1 Refactor：抽 `PollerHealth` 基类

新文件 `ops/billing/poller_health.py`，保留 `trc20_health.py` 作为薄包装（向后兼容 imports）：

```python
class PollerHealth:
    def __init__(
        self,
        *,
        component: str,                # "trc20_poller" | "applier"
        metric_filename: str,          # "trc20_poller.prom" | "applier.prom"
        runbook_section: str,          # "§6.1" | "§A.5"
        emoji_degraded: str = "🔴",
        emoji_recovered: str = "🟢",
    ):
        self.component = component
        ...
        self._state = _HealthState()
        self._lock = asyncio.Lock()

    async def record_success(self, *, now=None): ...
    async def record_failure(self, reason: str, *, now=None): ...
```

`trc20_health.py` 改为：

```python
from ops.billing.poller_health import PollerHealth

_health = PollerHealth(
    component="trc20_poller",
    metric_filename="trc20_poller.prom",
    runbook_section="§6.1",
)

# 保持原 module 级函数签名（PR #256 测试不动）
async def record_success(*, now=None):
    await _health.record_success(now=now)

async def record_failure(reason, *, now=None):
    await _health.record_failure(reason, now=now)

def _reset_for_tests():
    global _health
    _health = PollerHealth(...)
```

### 4.2 新模块 `ops/billing/applier_health.py`

```python
from ops.billing.poller_health import PollerHealth

_health = PollerHealth(
    component="applier",
    metric_filename="applier.prom",
    runbook_section="§A.5",
)

async def record_success(*, now=None): ...
async def record_failure(reason: str, *, now=None): ...
def _reset_for_tests(): ...
```

### 4.3 wire-in `scheduler.py`

```python
for (invoice_id,) in candidate_ids:
    ...
    try:
        apply_invoice_grant(db, invoice, now=now)
        db.commit()
        applied_count += 1
        await applier_health.record_success()   # NEW
    except InvoiceStateError as exc:
        db.rollback()
        logger.info(...)
        # state race — NOT alert-worthy
    except ApplierSkip as exc:
        db.rollback()
        logger.warning(...)
        await applier_health.record_failure(reason=exc.reason)  # NEW
    except Exception as exc:
        db.rollback()
        logger.exception(...)
        await applier_health.record_failure(reason="internal")  # NEW
```

⚠️ **难点**：当前 `_apply_paid_invoices_inner` 是**同步函数**（`def`），但 `record_*` 是 async。两条路径：

| 选项 | 实现 | 代价 |
|---|---|---|
| A. 全改 async | `def _apply_paid_invoices_inner` → `async def`；调用方 `run_apply_paid_invoices` 已 async,直接 await | ~5 处 call site，测试需加 async 装饰；最干净 |
| B. fire-and-forget | `asyncio.create_task(record_failure(...))` | 当前 thread 不 await，可能丢；reject ❌ |
| C. 同步落盘 + 异步 Telegram | 抽 `record_failure_sync()` 只更新 state + 文件；Telegram 在外层 wrap | 复杂，违反 trc20_health 模板对称性 ❌ |

**选 A** — 改 `async def`，传染面只到 `run_apply_paid_invoices`（已 async），测试改造可控。

### 4.4 测试

新增 `tests/test_billing_applier_health.py`（15 个用例，复用 `trc20_health` 测试结构 — sed 替换 `trc20_health` → `applier_health`，自适应 reason 维度）。

`tests/test_billing_scheduler.py` 补：
- `test_applier_records_success_on_clean_apply`
- `test_applier_records_failure_on_applier_skip`
- `test_applier_records_failure_on_bare_exception`
- `test_applier_does_not_record_failure_on_state_race`

### 4.5 OPS runbook

新增 `docs/ai-cto/OPS-billing-scheduler-runbook.md` §3（applier 告警节）— 与 OPS-trc20-runbook §5.3 同构。

---

## 5. Risks

| 风险 | 缓解 |
|---|---|
| Refactor `trc20_health` 破坏 PR #256 测试 | 保留 module-level 函数签名 + `_reset_for_tests`，run PR #256 测试套件验证 |
| `_apply_paid_invoices_inner` async 化引发 5+ call site 改造 | Grep 全引用，统一 await。`run_apply_paid_invoices` / 测试都已是 async |
| Per-reason label 在 textfile 引入字符串拼接攻击面 | `ApplierSkip.reason` 是代码内常量集，不接受用户输入 |
| 同时改两个 poller_health → 双告警风暴 | 各自独立 state + lock，互不干扰；阈值默认值复用 |
| PR #256 还没合入主分支 | 本 SPEC 在 PR #256 之上 stack，或等其 merge 再 ship |

---

## 6. Acceptance Criteria

- [x] SPEC + PLAN + TASKS（本文件）
- [ ] `ops/billing/poller_health.py` 基类（≤ 250 LoC）
- [ ] `ops/billing/trc20_health.py` 改为薄包装（向后兼容）
- [ ] `ops/billing/applier_health.py` 新模块（≤ 50 LoC，纯 delegation）
- [ ] `ops/billing/scheduler.py` `_apply_paid_invoices_inner` → async（+ 3 行 record_* 调用）
- [ ] `tests/test_billing_poller_health.py` 共享 fixture
- [ ] `tests/test_billing_applier_health.py` 15 cases
- [ ] `tests/test_billing_trc20_health.py` 15 cases（保持 pass）
- [ ] `tests/test_billing_scheduler.py` +4 cases
- [ ] mutation gate ≥ 80%（hand-checked surviving-mutant list）
- [ ] OPS runbook 新文件 + cross-link from CONSTITUTION §43
- [ ] PR 标签：`requires-double-review`
- [ ] PR 描述明确依赖关系：**stack on PR #256** 或 **wait merge**

---

## 7. PLAN

```
T1 poller_health.py 基类抽取
T2 trc20_health.py 薄包装改造 (保 PR #256 测试 green)
T3 applier_health.py 新模块 (delegation)
T4 scheduler.py async 化 + wire-in
T5 test_billing_poller_health.py 共享 fixture
T6 test_billing_applier_health.py 15 cases
T7 test_billing_scheduler.py +4 integration cases
T8 OPS-billing-scheduler-runbook.md
T9 commit + PR (stack OR wait)
```

## 8. TASKS（atomic）

| ID | 内容 | 文件 | LoC | 依赖 |
|---|---|---|---|---|
| T1 | 抽 `PollerHealth` 基类 | `ops/billing/poller_health.py`（新）| ~230 | — |
| T2 | trc20_health → 薄包装 | `ops/billing/trc20_health.py`（重写）| ~50 | T1 |
| T3 | applier_health 新模块 | `ops/billing/applier_health.py`（新）| ~40 | T1 |
| T4 | scheduler.py async 化 | `ops/billing/scheduler.py` | +10 -3 | T3 |
| T5 | 共享 fixture | `tests/test_billing_poller_health.py`（新）| ~80 | T1 |
| T6 | applier_health 测试 | `tests/test_billing_applier_health.py`（新）| ~200 | T3, T5 |
| T7 | scheduler 集成测试 | `tests/test_billing_scheduler.py` | +120 | T4 |
| T8 | OPS runbook | `docs/ai-cto/OPS-billing-scheduler-runbook.md`（新）| ~120 | — |
| T9 | commit + PR | — | — | T1-T8 |

---

## 9. 决策点（用户审核）

1. **stack on PR #256 OR wait merge?**
   - Stack：快，但若 #256 review 反对某设计点会牵连本 PR
   - Wait：稳，但延 1-3 天
   - **建议**：等 PR #256 通过双签后再 ship 本 PR，避免 review 摩擦
2. **是否同时把 `_reap_expired_invoices_inner` 也接入？**
   - 失败 ≠ 钱卡住（reap 是清扫废弃 invoice），告警 ROI 低
   - **建议**：留 Phase C，本 PR 不做
