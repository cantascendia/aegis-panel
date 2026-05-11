# SPEC — TRC20 Client Resilience (Cost Guard + Trongrid Fallback)

> **Status**: DRAFT — 2026-05-11，by CTO（Opus 4.7 1M）
> **Trigger**: reliability-auditor wave-14 R2，P1 改进 #3（cost guard）+ #5（real fallback）
> **Forbidden path**: ❌ NO — `ops/billing/trc20_client.py` 是只读外部 API 客户端，不触 `**/billing/**` 业务态、不改 schema、无支付状态机
> **依赖**: 独立于 PR #256 / SPEC-billing-scheduler-alerting，不需 stack

---

## 1. Context

reliability-auditor 2026-05-11 R2 报告两个 trc20_client 缺口：

### 缺口 1：Cost Guard 0 实现

[trc20_client.py:60](../../ops/billing/trc20_client.py) 注释承诺 "30s poll → 1 req/30s 远低于 100/s 公开配额"，但**没有任何代码护栏**。一旦：
- 调度器 misconfig（POLL_INTERVAL=1s）
- 测试代码遗忘 mock，实际 hit 公网
- 未来 multi-process 部署 N 倍调用

→ 触发 Tronscan IP 封禁，全 operator 链路瘫痪。

### 缺口 2：Trongrid Fallback 仅是文档承诺

模块 docstring L-21-23 写：
> *"Fallback exists: same shape on Trongrid public-node JSON-RPC, so if Tronscan degrades we override `BILLING_TRC20_TRONSCAN_API_BASE` + tweak the parsing in this file."*

**但代码里没有 fallback 切换逻辑**。当前依赖 operator 在 OPS-trc20-runbook §6.1 手动 `sed` `.env` 重启容器。中国大陆出口被墙时（runbook §6.1 case 4），用户付款延迟分钟级。

---

## 2. What

| # | 功能 | 验收 |
|---|---|---|
| F1 | **Per-process 调用计数器** — 每次 `list_recent_transfers` 自增计数，按滑动窗口分桶（1h / 1d）| 暴露 `trc20_tronscan_calls_total{window="1h"}` 在 textfile metric |
| F2 | **软限速 cost cap** — 默认 200 calls/hour（30s 双轮 + 缓冲）；超阈值时下一次 `list_recent_transfers` 直接 `Trc20ClientError` + Telegram 告警 | 复用 PR #256 `trc20_health.record_failure` 出口 |
| F3 | **Fallback URL list** — 配置项 `BILLING_TRC20_FALLBACK_API_BASES`（CSV）；主 base 5 次失败后自动切换 | `from_env` 改造，state 记录"当前活动 base" |
| F4 | **Fallback 切换告警** — 切换瞬间 Telegram"已切到 fallback X"；恢复主 base 告警"已切回主 base" | 同 PR #256 去抖语义 |
| F5 | **Trongrid 兼容 parser** — `_parse_transfers` 加 Trongrid 响应 schema 适配（不强求 100%，能解析就解析）| 新 fixture 验证 |

**Out of scope**：
- Tronscan API key — 公共端点目前无 key，引入 paid key 是商业决策非可靠性
- 自建 indexer — 工作量大，留 Phase C
- 链上 RPC 直连（不走 indexer）— 体积大，不必要

---

## 3. Why（设计取舍）

| 选择 | 取舍 | 拒绝的替代 |
|---|---|---|
| **滑动窗口分桶**（1h / 1d）| 简单 deque-based，无新依赖 | 真 token bucket：过度工程 |
| **软 cap = 200/h**（vs 公共 100/s = 360000/h）| 留 1800× 余量，但抓 misconfig（POLL=1s 会刷 3600/h）| 硬 100/s：cap 太松，misconfig 跑半小时才触发 |
| **Fallback list = CSV env** | 与现有 `BILLING_TRC20_TRONSCAN_API_BASE` 同构 | 单 fallback：缺一道防线 |
| **5 次失败切换**（不是 3 次告警）| 切换比告警更激进的成本，需要更高确信 | 3 次：可能把单次 Tronscan 抖动当永久故障 |
| **不持久化 active base** | 重启 = 重新选 = 回主 base 试一次 | 持久化：状态 leak 越过部署边界 |
| **复用 trc20_health** | 告警出口对齐 | 新告警通道：分裂 operator 注意力 |

---

## 4. How

### 4.1 新模块 `ops/billing/trc20_cost_guard.py`

```python
class TronscanCostGuard:
    """Per-process call counter + sliding window."""
    def __init__(self, *, max_calls_per_hour: int = 200):
        self._max = max_calls_per_hour
        self._calls = collections.deque()  # timestamps
        self._lock = asyncio.Lock()

    async def record_call(self, *, now=None) -> None:
        """Record one outbound call; raise Trc20ClientError if over cap."""

    def calls_in_window(self, window: timedelta, *, now=None) -> int:
        ...

    def emit_metrics(self, now: datetime) -> dict[str, int]:
        ...
```

Wire into `TronscanClient.list_recent_transfers` 第一行：

```python
async def list_recent_transfers(self, *, to_address, limit=50):
    await self._cost_guard.record_call()
    ...
```

### 4.2 Fallback chain 改造 `TronscanClient`

```python
@classmethod
def from_env(cls) -> TronscanClient:
    bases = [BILLING_TRC20_TRONSCAN_API_BASE]
    if BILLING_TRC20_FALLBACK_API_BASES:
        bases += [b.strip() for b in BILLING_TRC20_FALLBACK_API_BASES.split(",") if b.strip()]
    return cls(
        api_bases=bases,
        contract_address=BILLING_TRC20_USDT_CONTRACT,
    )

async def list_recent_transfers(...):
    last_exc = None
    for idx, base in enumerate(self._api_bases):
        try:
            return await self._fetch_from(base, to_address=to_address, limit=limit)
        except Trc20ClientError as exc:
            self._failure_counts[idx] += 1
            last_exc = exc
            continue
    raise last_exc
```

**Active-base tracking**: 模块级状态 `_active_base_idx`，达 5 次失败切换到下一个，发告警 via `trc20_health.record_failure(reason="fallback_switch:trongrid")` — 复用 `applier_health`-style per-reason label。

### 4.3 配置项

`ops/billing/trc20_config.py` 加：

```python
BILLING_TRC20_FALLBACK_API_BASES: str = config(
    "BILLING_TRC20_FALLBACK_API_BASES", default=""
)
BILLING_TRC20_MAX_CALLS_PER_HOUR: int = int(
    config("BILLING_TRC20_MAX_CALLS_PER_HOUR", default=200)
)
BILLING_TRC20_FALLBACK_THRESHOLD: int = int(
    config("BILLING_TRC20_FALLBACK_THRESHOLD", default=5)
)
```

### 4.4 测试

`tests/test_billing_trc20_cost_guard.py`（新，~150 LoC）：
- `test_under_cap_no_error`
- `test_over_cap_raises_immediately`
- `test_sliding_window_drops_old_calls`
- `test_window_buckets_independent`
- `test_concurrent_record_call_lock_safe`
- `test_emit_metrics_shape`

`tests/test_billing_trc20_client.py` +5 cases：
- `test_fallback_kicks_in_after_threshold_failures`
- `test_fallback_returns_to_primary_on_success`
- `test_fallback_switch_emits_health_failure`
- `test_no_fallback_configured_raises_normal`
- `test_trongrid_response_schema_parsed`

### 4.5 OPS 文档

`docs/ai-cto/OPS-trc20-runbook.md` §6.1 mitigation 段落改写：

```diff
-**Mitigation**(15 分钟内不能恢复时):
-
-```bash
-# 切到备用 base
-echo 'BILLING_TRC20_TRONSCAN_API_BASE=https://api.trongrid.io' >> .env
-docker compose restart marzneshin
-```
+**自动 mitigation**(已实现,2026-05-11 SPEC-trc20-client-resilience):
+
+配置 `BILLING_TRC20_FALLBACK_API_BASES=https://api.trongrid.io` 即可,
+连续 5 次主 base 失败后自动切换,Telegram 告警。
+
+**手动 mitigation**(仍保留作 escape hatch):...
```

---

## 5. Risks

| 风险 | 缓解 |
|---|---|
| Cost cap 误触发卡死合法流量 | 默认 200/h vs 实际 ~120/h，留 67% 余量；env 可调 |
| Fallback schema 差异引爆 parser | `_parse_one` 已 try/except + warning + skip-不-crash |
| Module-level state 多进程不一致 | Per-process 独立计数器，cap 不严格全局 — 可接受 |
| 切换告警风暴（主备反复抖）| 复用去抖 — 一次切换一条告警 |
| Trongrid 也宕 | 配置可加 N 个 fallback，最后一个失败正常 raise |

---

## 6. Acceptance Criteria

- [x] SPEC + PLAN + TASKS
- [ ] `ops/billing/trc20_cost_guard.py`（≤ 130 LoC）
- [ ] `ops/billing/trc20_client.py` fallback chain（+30 LoC）
- [ ] `ops/billing/trc20_config.py` 3 个 env vars
- [ ] `tests/test_billing_trc20_cost_guard.py` 6 cases
- [ ] `tests/test_billing_trc20_client.py` +5 cases
- [ ] `docs/ai-cto/OPS-trc20-runbook.md` §6.1 改写
- [ ] CI all green
- [ ] **NO forbidden-path 标签**（trc20_client.py 是外部 API 客户端，不触业务状态机）

---

## 7. PLAN

```
T1 trc20_cost_guard.py（独立模块）
T2 3 个 env vars
T3 trc20_client.py fallback chain
T4 cost_guard 测试
T5 client fallback 测试
T6 OPS runbook §6.1 改写
T7 commit + PR（无需双签）
```

## 8. TASKS（atomic）

| ID | 文件 | LoC | 依赖 |
|---|---|---|---|
| T1 | `ops/billing/trc20_cost_guard.py`（新）| ~130 | — |
| T2 | `ops/billing/trc20_config.py` | +12 | — |
| T3 | `ops/billing/trc20_client.py` | +30 -10 | T1, T2 |
| T4 | `tests/test_billing_trc20_cost_guard.py`（新）| ~150 | T1 |
| T5 | `tests/test_billing_trc20_client.py` | +120 | T3 |
| T6 | `docs/ai-cto/OPS-trc20-runbook.md` | +30 -15 | T3 |
| T7 | commit + PR | — | T1-T6 |
