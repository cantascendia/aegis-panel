---
created: 2026-04-28
status: SEALED
sealed: 2026-04-30
sealed_by: CTO(用户授权 auto mode 自动决策,issue #103 4 TBDs 全拍板)
priority: P1(v0.3 第一块,RBAC 前置)
session: S-AL(可启)
unlocks: RBAC(SPEC-rbac 同步 SEALED)
template: D-005
---

# SPEC — 审计日志系统(Audit Log)

> Round 4(v0.3 路线图 #4)候选 SPEC,docs-only。
>
> 本 SPEC 是 S-AL(Audit Log)session 的交付契约。任何 `ops/audit/**` 代码改动
> 必须能引用本 SPEC 的某条 Acceptance criterion,否则 scope creep。
>
> 对接:`docs/ai-cto/VISION.md` §商业化运营层、`docs/ai-cto/ROADMAP.md` v0.2 #4 +
> v0.3 #4、`docs/ai-cto/DECISIONS.md#D-003`(法律风险张力)、`ops/billing/db.py`
> `aegis_billing_payment_events`(窄域审计先例)、SPEC-rbac(草稿中)。

---

## What

记录**控制面所有管理员侧 mutate 操作**的"who + when + what + target + before/after +
result + ip/UA",形成**append-only**审计 trail,服务运营复盘 + RBAC 联动 + 商业化合规
追溯。

### 范围(MVP scope)

- ✅ 拦截 sudo-admin / admin 的所有 `POST` / `PATCH` / `PUT` / `DELETE` 调用
- ✅ 自动捕获 `actor_id` / `actor_type` / `action`(=路由名)/ `target_type` /
  `target_id` / `before_state`(diff 前)/ `after_state`(diff 后)/ `ip` / `ua` /
  `result`(success/failure)/ `ts`
- ✅ 敏感字段(JWT / 密码 / `merchant_key` / TRC20 私钥等)**白名单 redact**,
  不入审计
- ✅ Dashboard `/dashboard/audit` 页(sudo-admin only),支持 actor / action /
  target / 时间筛选 + CSV 导出
- ✅ 与 `aegis_billing_payment_events` **共存**:billing 内部状态机仍写窄域
  payment_events,billing 相关 admin action(如 `apply_manual` / `cancel`)**双写**
  audit_events
- ✅ Retention 默认 90 天,`AUDIT_RETENTION_DAYS=0` 关闭审计(对应 D-003 风险张力)
- ✅ 加密落盘:`before_state` / `after_state` 的 JSON payload 用 Fernet 加密,
  加密 key 与 `BILLING_SECRET_KEY` 同一管理路径

### 边界(明确不做)

- ❌ **不审计普通 user 的操作**(订阅获取 / 流量统计 / 自助续费),那是用户行为
  日志,归属未来 `ops/user-events/`(若有需要),不在本 SPEC
- ❌ **不审计 read-only**(GET 请求),信噪比太低,且会让审计表 100x 膨胀
- ❌ **不审计 background scheduler**(`apply_paid_invoices` / `reap_expired_invoices`
  / `expiry_enforcer` 等自动化任务),那是 ops 系统日志,可独立建 `ops_events` 表
  (留给 v0.4)
- ❌ **不在本 PR 改 `ops/billing/payment_events`**(已稳定,改动等于动 Round 3
  落地 SPEC,scope 失控)
- ❌ **不实现实时告警**(异常检测 / 暴力破解告警 / Slack/TG 推送),v0.4 由
  S-O 评估后单开 SPEC
- ❌ **不实现跨节点审计**(marznode 数据面操作),数据面无 admin mutate 路径,
  不需要

### 用户画像

- **Sudo-admin**(运营方本人):每日复盘 / 故障排查 / 财务对账 / RBAC 准备
- **Admin**(运营方信任的二级管理员):**自身行为被审计**,可看自己历史(read-only),
  不能看其他 admin 历史
- **End user**:**完全不可见**审计层

---

## Why

### 引文清单

`docs/ai-cto/VISION.md` §商业化运营层:

> 商业化运营层 ⏳ 待建(差异化 #2) — 订阅计费 / 流量告警 / 到期续费 /
> **管理员 RBAC**

`docs/ai-cto/ROADMAP.md` v0.2 #4:

> #4 审计日志系统(1 周,可与计费合并)

`docs/ai-cto/ROADMAP.md` v0.3 #4:

> #4 RBAC + 管理员分层

`docs/ai-cto/DECISIONS.md#D-003`(法律风险):

> CTO 对用户明确提示了运营付费机场(>200 用户)在中国大陆/伊朗/俄罗斯的刑事
> 风险,用户接受风险并继续。

### 三条触发动机

1. **商业化合规追溯**:订单退款 / 用户开通 / SNI 切换 / Plan 改价 / 流量充值
   全是真金白银操作。Round 3 上线 billing MVP 后,运营方第一次发现"我昨晚改的
   plan 价格被另一个 admin 改回去了"——窄域 payment_events 不够用,需要广域 actor
   维度。
2. **RBAC 联动**:管理员分层(SPEC-rbac 草稿中)的语义是"admin A 不能动
   admin B 创建的资源"——**没有审计的 RBAC 是空话**,因为权限边界本身就要靠
   audit trail 验证(谁试图越权 / 谁绕过被拦截)。审计 SPEC **必须先于 RBAC**
   落地,否则 RBAC 上线后无 forensic 能力。
3. **故障复盘 + 合规自证**:>200 用户场景下,任何"用户投诉账号被禁"或"plan
   价格异常"事件,运营方需要在 5 分钟内说清楚"是哪个 admin 在哪个时间做了什么"。
   现在没数据,等于盲飞。

### 法律风险张力(D-003 必须明示)

**审计日志 = 留指纹**。在中国大陆司法环境下,这把双刃剑切两面:

| 角度 | 利 | 弊 |
|---|---|---|
| 内部治理 | 多 admin 协作可追责 | 留下"运营方明知用户在翻墙"的证据链 |
| 司法配合 | 自证清白(如争议交易) | 设备扣押后审计表直接暴露用户活动 + 操作轨迹 |
| 商业纠纷 | refund / chargeback 取证 | 第三方诉讼的对方律师可申请调取 |

**SPEC 的应对**(写入 H-3 隐私章节):

- **默认开启 + 可关闭**:`AUDIT_RETENTION_DAYS=0` = 完全禁用,中间件 noop
- **加密落盘**:`before_state` / `after_state` 的 payload 用 Fernet 加密,
  key 仅 `.env`/HSM,设备扣押 ≠ 数据可读
- **N 天自动 wipe**:默认 90 天,scheduler 每日 sweep,过期硬删除(不是软标记)
- **不存用户身份**:不记录 end user 的行为(只记 admin 操作),减少"协助
  XX"的物证密度
- **运营方手册写明**:`OPS-audit-log-runbook.md`(D.5 交付)第一段必须是
  "如何在 30 秒内全表 wipe + 关闭审计"的应急流程

> 这条张力在中国大陆/伊朗/俄罗斯司法管辖区是**真实风险**。SPEC 不替运营方
> 决策"留还是不留",只确保**两种选择都能干净落地**。运营方按自己法域评估。

---

## How

### 1. 数据模型(`ops/audit/db.py`)

单表 `aegis_audit_events`,SQLAlchemy 2.0 typed mappings,单 Alembic 迁移
(SQLite + PG 16 双跑):

```python
class AuditEvent(Base):
    """Append-only audit row. One per admin mutate action.

    Intentionally **no UPDATE and no DELETE paths** from application
    code. TTL sweep is the only legitimate delete path (hard delete,
    via dedicated scheduler task)."""

    __tablename__ = "aegis_audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # — Actor —
    actor_id: Mapped[int | None]  # NULL = anonymous (e.g. failed pre-auth)
    actor_type: Mapped[str]       # "sudo_admin" | "admin" | "anonymous"
    actor_username: Mapped[str | None]  # snapshot,防 admin 改名后历史丢
    # — Action —
    action: Mapped[str]           # 路由名,e.g. "billing.plan.update"
    method: Mapped[str]           # POST | PATCH | PUT | DELETE
    path: Mapped[str]             # /api/billing/admin/plans/42
    # — Target —
    target_type: Mapped[str | None]   # "billing.plan" | "user" | "node"
    target_id: Mapped[str | None]     # 字符串,兼容 UUID / int / composite
    # — State diff (Fernet 加密) —
    before_state_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    after_state_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    # — Result —
    result: Mapped[str]           # "success" | "failure" | "denied"
    status_code: Mapped[int]      # HTTP 状态码 snapshot
    error_message: Mapped[str | None]  # 失败时的简短错误
    # — Context —
    ip: Mapped[str]               # 客户端 IP,trusted-proxy gate 后(D-012)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    request_id: Mapped[str | None]  # FastAPI middleware 注入,贯穿日志关联
    ts: Mapped[datetime]

    __table_args__ = (
        Index("ix_audit_actor_ts", "actor_id", "ts"),
        Index("ix_audit_action_ts", "action", "ts"),
        Index("ix_audit_target_ts", "target_type", "target_id", "ts"),
        Index("ix_audit_ts", "ts"),  # for retention sweep
    )
```

**估算膨胀面**(>200 用户场景):

| 操作类型 | 频次 / 日 | 备注 |
|---|---|---|
| user CRUD(开/续/禁) | ~50 | 客户提单 + 续费 + 自动到期处理 |
| plan / channel 配置改 | ~5 | 运营方调价 / 切码商 |
| invoice manual_apply / cancel | ~10 | VIP / 客诉处理 |
| node 配置改(SNI / Reality) | ~3 | 偶发,加固调整 |
| 登录尝试(成功 + 失败) | ~30 | sudo + admin 两人轮班 |
| **合计 / 日** | **~100** | |
| **90 天累计行数** | **~9000** | 极小,索引开销可忽略 |
| **单行平均字节(含密文)** | ~2KB | before/after 加密后 ~1.5KB + 元数据 |
| **90 天总体积** | **~18MB** | PG 16 完全无压力 |

结论:90 天 retention 在 >200 用户规模下**单表 < 20MB**,无需分区 / 分表。
若运营方扩到 >2000 用户(v1.0 后)再评估按月分区。

### 2. 中间件(`ops/audit/middleware.py`)

FastAPI middleware,挂载顺序:**rate-limit → trusted-proxy → audit → router**。

```python
class AuditMiddleware(BaseHTTPMiddleware):
    """Capture admin mutate actions into aegis_audit_events.

    - Skips if AUDIT_RETENTION_DAYS == 0 (operator opted out).
    - Skips read-only methods (GET / HEAD / OPTIONS).
    - Skips non-admin paths (端点必须挂在 /api/.../admin/* 或带
      sudo dependency 才进入审计;走 path matcher + dependency
      tag 双重判定)。
    - Captures before_state by re-fetching target via the same
      session BEFORE handler runs (one extra SELECT; cost ≈ 1ms).
    - Captures after_state by inspecting handler return value or
      re-fetching after handler (whichever is cheaper per route).
    - Redacts sensitive fields via REDACT_FIELDS allowlist (TBD-2)
      before encrypting + writing.
    - Failures (handler raised / 4xx / 5xx) write a row with
      result=failure + error_message (truncated to 512 chars).
    - Audit write itself is fire-and-forget within the same DB
      transaction as the handler — if handler rolls back, audit
      row goes with it; if audit write fails, handler succeeds
      (audit failure does NOT block business action; logged to
      stderr for ops to spot).
    """
```

**关键设计点**:

- **before-state 捕获**:在 handler 执行前 SELECT 一次目标资源的 dict
  representation。增 1 次 SELECT,>200 用户场景下日均 100 次 = 100 次额外
  SELECT,< 1ms each = 总开销 ~100ms/day,可忽略
- **after-state 捕获**:优先从 handler return value 取(免一次 SELECT),
  否则 re-fetch
- **失败 redact**:加密前必走 `redact_payload()`,黑名单字段直接置
  `"<REDACTED>"`,不是 hash(hash 让审计员误以为可比对相等性,反而泄露
  "两个 redacted 字段是否相同")
- **不阻塞业务**:audit 写失败 → stderr log + skip,不让审计 bug 把 panel
  打挂(L-018 教训)

### 3. 隐私 / 加密(`ops/audit/crypto.py`)

**复用 Fernet 加密路径**(billing `BILLING_SECRET_KEY` 已建,L-014 同款):

- `AUDIT_SECRET_KEY` env(`.env.example` 加),Fernet 32 字节 base64 key
- 与 `BILLING_SECRET_KEY` **可同 key 也可异 key**,操作员决定
- 缺 key 且 `AUDIT_RETENTION_DAYS > 0` → panel 启动 fail-loud(D-006 同款契约)
- payload 加密前先 redact,加密后写 LargeBinary 列

**REDACT_FIELDS 默认黑名单**(`ops/audit/redact.py`,模块常量):

```python
REDACT_FIELDS = frozenset({
    # 凭据类
    "password", "password_hash", "jwt_secret", "secret_key",
    "merchant_key", "merchant_key_encrypted", "api_key", "api_token",
    # 链上私钥(防 trc20 私钥误入审计)
    "trc20_private_key", "private_key", "mnemonic",
    # 用户敏感(GDPR 预留)
    "email", "phone", "real_name", "id_card",
    # 订阅 token(等同账号密码)
    "subscription_token", "sub_token",
})
```

**TBD-2(下文)**:运营方是否要可配置(env override)?目前先硬编码黑名单,
未来若有新字段,通过加新字段 → PR 走 review。

### 4. Retention sweep(`ops/audit/scheduler.py`)

APScheduler 任务,接入 `apply_panel_hardening(app)` → `start_audit_scheduler`:

| Task | Interval | 操作 |
|---|---|---|
| `audit_retention_sweep` | 1 天 03:00 UTC | `DELETE FROM aegis_audit_events WHERE ts < now() - AUDIT_RETENTION_DAYS days`(若 0 则直接 return) |

**幂等性**:DELETE WHERE 语句天然幂等。两个 worker 撞车 = 两个都跑空,无副作用。

**操作员紧急 wipe**(对应 D-003 应急流程):

- `OPS-audit-log-runbook.md` 写明 SQL:`TRUNCATE aegis_audit_events`(< 1s)
- Dashboard 不暴露 wipe 按钮(防误操作 / 防被胁迫一键销毁证据)
- 若运营方需要"一键关闭+wipe"按钮,**TBD-1**(下文)

### 5. Dashboard 页面(`dashboard/src/modules/audit/`)

**Sudo-admin only**(后端 dependency 拦截 + 前端 sidebar 隐藏):

```
dashboard/src/modules/audit/
├── api/
│   └── client.ts              # GET /api/audit/events?actor=&action=&...
├── pages/
│   ├── AuditEventsPage.tsx    # 表格 + 筛选侧边栏
│   └── AuditEventDetailPage.tsx  # 单条详情(decrypt before/after,展示 diff)
└── components/
    ├── AuditFilterBar.tsx     # actor / action / target / 时间窗
    ├── AuditEventRow.tsx
    └── BeforeAfterDiff.tsx    # JSON diff 高亮
```

**功能边界**:

- ✅ 列表 / 筛选 / 分页(默认 50/页,游标分页)
- ✅ 单条 detail 查看 before/after diff(后端解密返回 JSON)
- ✅ CSV 导出(< 10000 行;> 10000 行报错让用户加筛选条件)
- ❌ 不能删除单条(append-only,只能等 retention sweep 或 TRUNCATE)
- ❌ 不能编辑(append-only)
- ❌ 不在审计页里"重放某操作"(超出审计职责)

**i18n**:en + zh-cn 完整,其他 6 locale 英文 seed(对齐 SPEC-billing-mvp 政策)。

### 6. REST API(`ops/audit/endpoint.py`)

挂载 `/api/audit/*`,通过 `apply_panel_hardening` 注册。

**Sudo-admin only**:

```
GET   /api/audit/events                    → 列表 + 筛选 + 分页
GET   /api/audit/events/{id}               → 单条详情(payload decrypt)
GET   /api/audit/events/export.csv         → CSV 导出(限 10000 行)
GET   /api/audit/stats                     → 按 action / actor 聚合的 7d 统计
```

**Admin only**(自助查阅自己历史):

```
GET   /api/audit/me/events                 → 仅本 actor 的历史,无 decrypt 权限
                                              (返回 elided "<encrypted>" payload)
```

### 7. 与 `aegis_billing_payment_events` 的关系

**双轨 + 双写**:

| 维度 | `aegis_billing_payment_events` | `aegis_audit_events` |
|---|---|---|
| 范围 | billing 内部状态机 | 全控制面 admin 操作 |
| Actor | 系统 / scheduler / webhook / admin | admin only(scheduler 不审计) |
| 数据 | invoice 状态变化、tx_hash、webhook payload | actor 行为 + before/after |
| 加密 | 不加密(链上 tx_hash 公开数据) | Fernet 加密 |
| Retention | 永不删除(财务追溯) | 默认 90 天 |
| Read 权限 | 所有 admin(对账需要) | sudo-admin only(actor 维度敏感) |

**双写规则**(billing-related admin actions):

- `apply_manual` / `cancel` / `plan create/update` / `channel create/update`
  → **同时写两表**,通过 `audit_event_id` 字段(可 NULL)在 payment_events 里
  反向关联(可选,本 SPEC 默认不加,留 TBD-3)
- 双写失败处理:audit 写失败不阻塞 payment_events 写(后者是状态机不可缺失);
  payment_events 写失败 = handler 失败,audit 跟随 rollback

---

## Risks 矩阵

| Risk | 概率 | 影响 | Mitigation |
|---|---|---|---|
| **法律风险**:审计表被司法机关扣押,反向证明运营方"明知" | 中 | **极高** | (1) `AUDIT_RETENTION_DAYS=0` 一键关;(2) Fernet 加密(key 不在设备);(3) 默认 90 天自动 wipe;(4) Runbook 第一段写"30 秒应急 TRUNCATE";(5) 不审计 user 行为只审计 admin。**最终决策权在运营方**,SPEC 不替选 |
| **数据膨胀**:>200 用户 + 90 天 = 单表多大 | 低 | 中 | 估算 ~9000 行 / 18MB,完全可控。> 2000 用户(v1.0 后)再评估分区 |
| **中间件性能开销**:每个 mutate 多一次 SELECT(before-state) | 低 | 低 | 100 次/日 × 1ms = 100ms/day。可忽略。若未来某高频路由(暂无)成瓶颈 → 该路由白名单跳过 before-fetch 改用 handler return value |
| **加密 key 管理**:`AUDIT_SECRET_KEY` 丢失 → 历史审计永久不可读 | 中 | 中 | (1) 与 `BILLING_SECRET_KEY` 同管理路径(操作员已熟);(2) Runbook 写 key 备份建议(GPG 加密存运营方个人云盘);(3) `OPS-audit-log-runbook.md` "key 轮换" 流程 |
| **GDPR / 类合规**:若开欧洲市场,actor 历史数据请求 | 低 | 中 | 当前不开欧洲市场(D-003 已限定中国为主)。预留 `actor_id` 软删除字段,未来 GDPR PR 单独处理 |
| **误审计**:scheduler 自动操作被错误打成 admin action | 低 | 低 | 中间件挂载点严格限定 `/api/*/admin/*`,scheduler 不经 HTTP,天然不进中间件 |
| **隐私失守 redact 不全**:某新功能加新敏感字段忘记加 REDACT_FIELDS | 中 | 高 | (1) `REDACT_FIELDS` 在 `ops/audit/redact.py` 单一来源,有 docstring 说明加字段流程;(2) PR review checklist 强制审计字段评估;(3) 单测 `test_redact_blocks_known_secret_fields` 锁死 |
| **审计自身失败**:audit 写挂导致 handler 也回滚 | 低 | 高 | audit 写失败 = stderr log + skip,**不**阻塞 handler。L-018 教训。事故场景:DB 磁盘满,handler 也得跟着失败,但这是 DB 系统级问题,不是审计设计问题 |
| **数据格式变更**:after-state schema 升级后历史 row 解 JSON 出错 | 中 | 低 | payload 内带 `schema_version` 字段(decrypt 后 JSON 顶层),前端 detail 页对未知 version 走 raw JSON 展示而非 diff |
| **时序竞态**:before-fetch 与 handler-write 之间被另一 admin 改 | 低 | 低 | 接受。审计反映"该 actor 看到的 before",并非"全局真值"。如果两个 admin 同秒撞,两条 audit 都留,事后人工对账即可 |
| **CSV 导出大数据 OOM** | 低 | 低 | 硬上限 10000 行,流式生成(不一次 load 全表) |
| **i18n 字符串爆炸**:审计页有大量 action 名(动态) | 中 | 低 | action 名走 i18n key 但 fallback 到英文路由名,用户看到的最差是英文,不会断 |

---

## Acceptance criteria

### AL.0(本 SPEC PR,docs-only)

- [ ] **AC-AL.0.1** `docs/ai-cto/SPEC-audit-log.md` 合入,frontmatter `status:
      DRAFT`
- [ ] **AC-AL.0.2** SPEC 含 6 段(What / Why / How / Risks / AC / Kickoff)
      + 1 段 TBD,中文为主
- [ ] **AC-AL.0.3** 与 `aegis_billing_payment_events` 关系在 H-7 段落明确写清
- [ ] **AC-AL.0.4** 法律风险张力(D-003)在 Why + Risks + How.3 三处贯穿,不只
      点一笔

### AL.1 — 数据 + 中间件 + 加密(预计 1 周)

- [ ] **AC-AL.1.1** Alembic 迁移 `<date>_audit_events.py` 在 SQLite + PG 16 双跑绿
- [ ] **AC-AL.1.2** `ops/audit/db.py` AuditEvent 模型注册到 `Base.metadata`
      (L-014 套路,加 `import ops.audit.db  # noqa` 到 env.py)
- [ ] **AC-AL.1.3** `AuditMiddleware` 中间件挂载顺序正确(rate-limit → proxy →
      audit → router)
- [ ] **AC-AL.1.4** `AUDIT_RETENTION_DAYS=0` 时中间件 noop(verify by unit test:
      `assert AuditEvent.count == 0` after admin POST)
- [ ] **AC-AL.1.5** REDACT_FIELDS 单测覆盖所有 known secret 字段;新增字段必须
      改 test
- [ ] **AC-AL.1.6** 缺 `AUDIT_SECRET_KEY` 且 `AUDIT_RETENTION_DAYS > 0` → panel
      启动 fail-loud(对齐 D-006)
- [ ] **AC-AL.1.7** 审计写失败 → stderr log + handler 继续(单测模拟 DB write
      raise,handler 仍返回 200)

### AL.2 — Retention sweep + Endpoint(预计 0.5 周)

- [ ] **AC-AL.2.1** `audit_retention_sweep` 任务每日 03:00 UTC 跑,> N 天行被硬删
- [ ] **AC-AL.2.2** `AUDIT_RETENTION_DAYS=0` 时 sweep 任务直接 return
- [ ] **AC-AL.2.3** `/api/audit/events` sudo-admin 200 / admin 403 / user 403 /
      anonymous 401
- [ ] **AC-AL.2.4** `/api/audit/me/events` admin 200 但 payload 字段为
      `"<encrypted>"`(无 decrypt 权限)
- [ ] **AC-AL.2.5** 筛选参数 actor / action / target / 时间窗 单元测试覆盖
- [ ] **AC-AL.2.6** CSV 导出 ≤ 10000 行;> 10000 行 422 + 提示加筛选

### AL.3 — Dashboard(预计 0.5 周)

- [ ] **AC-AL.3.1** `/dashboard/audit` 仅 sudo-admin 看见 sidebar 入口
- [ ] **AC-AL.3.2** 表格 + 筛选 + 分页跑通,游标分页 ≥ 1000 行场景顺畅
- [ ] **AC-AL.3.3** Detail 页 BeforeAfterDiff 渲染 JSON diff,redacted 字段显示
      `"<REDACTED>"` 而非空
- [ ] **AC-AL.3.4** i18n en + zh-cn 完整,其他 6 locale 英文 seed
- [ ] **AC-AL.3.5** Sidebar 项走 append-only(D-011 冲突地带规则)

### AL.4 — 双写 + Runbook(预计 0.3 周)

- [ ] **AC-AL.4.1** `apply_manual` / `cancel` / plan-update / channel-update 4 个
      billing-admin action 触发后,`payment_events` + `audit_events` **双写**,
      tx 同生命周期(rollback 同步)
- [ ] **AC-AL.4.2** `OPS-audit-log-runbook.md` 第一段写"30 秒应急 wipe + 关闭"
      流程,后续段覆盖:key 轮换 / retention 调整 / 故障排查 / GDPR-类请求模板
- [ ] **AC-AL.4.3** `OPS-audit-log-runbook.md` 每个应急场景含:检测命令 / 判定
      条件 / 处置步骤 / 验证命令(对齐 SPEC-deploy AC-D.5.2)

---

## TBD 决策(SEALED 2026-04-30)

> **历史**:本段原为 4 个 open TBD,2026-04-30 由 CTO(用户授权 auto mode)在 issue #103 拍板,
> SPEC 状态从 DRAFT 转 SEALED。以下保留原 trade-off 描述,在每条末尾追加 ✅ **SEALED** 决策段。

### TBD-1 | Dashboard 是否暴露"一键 wipe"按钮

- **支持**:运营方应急场景下,SSH 不便时可在 dashboard 直接 nuke 历史
- **反对**:被胁迫场景下按钮一键销毁证据 = 反向风险;且增加误操作面
- **当前默认**:**不暴露**,wipe 走 SQL TRUNCATE(Runbook 写命令)
- ✅ **SEALED 决策(2026-04-30)**:**不暴露 dashboard wipe 按钮**(维持 SPEC 默认)
  - **理由**:D-003 法律张力(中/伊/俄被胁迫风险)+ 单点社工攻击面 + sudo 是最高权限不应再加销毁键
  - **psql/SSH 摩擦合理**:wipe 是高破坏性操作,必须高门槛(攻击者要拿到 DB / shell 才能销毁)
  - **revisit 信号**:运营方实战 ≥ 3 次"应急 wipe 但 SSH 不便"的真实数据点

### TBD-2 | REDACT_FIELDS 是否运营方可配置

- **支持**:不同运营方有不同隐私偏好(欧洲市场要 redact email,中国可不)
- **反对**:配置面扩大 = bug 面扩大;一个错误的 env override 可让密码入审计
- **当前默认**:**硬编码**,改字段 = 改代码 = 走 PR review
- ✅ **SEALED 决策(2026-04-30)**:**混合方案 — base list 硬编码 + `.env` AUDIT_EXTRA_REDACT_FIELDS 追加(只允许 union,不允许 override)**
  - **base list 硬编码**:`{"jwt", "password", "passwd", "merchant_key", "trc20_private_key", "cf_token", "secret_key", "api_key", "private_key"}`(任何运营方都不应能解除这些 redact)
  - **`.env` AUDIT_EXTRA_REDACT_FIELDS**:逗号分隔追加(如 `email,phone` for 欧洲),实现走 set union(`base | extras`)
  - **理由**:base list 防 misconfig 漏 redact 关键安全字段;extras 给运营方按市场扩展自由(GDPR / 中国合规张力)
  - **实施约束**:extras 字段只能追加,不能用 `.env` 删除 base list 项;实施代码用 `frozenset()` 锁 base list

### TBD-3 | `payment_events` 是否反向关联 `audit_event_id`

- **支持**:billing 对账时直接跳到 audit 行,UX 顺
- **反对**:增加一个 nullable 外键 + 迁移触碰 Round 3 已稳定的 payment_events
  表(scope creep);且双写顺序保证 payment_events 写时 audit 可能未提交
- **当前默认**:**不加**,billing UI 通过 `(invoice_id, ts)` 范围查询 audit_events
  即可
- ✅ **SEALED 决策(2026-04-30)**:**不加 FK**(维持 SPEC 默认)
  - **理由**:D-014 billing 自治原则(`pricing.py` 与 `grants.py` 互不 import,scheduler 是唯一胶水);加 FK = 双表耦合 + scope creep + 触碰已稳定的 Round 3 表
  - **billing UI 通过 `(invoice_id, ts)` 范围查询 audit_events 即可**
  - **revisit 信号**:运营方实战 ≥ 3 次"对账时跳 audit 不顺"反馈

### TBD-4 | 审计层 vs `ops_events`(scheduler 行为日志)合一还是分开

- **支持合一**:省一张表,所有"系统行为"在一处
- **反对合一**:scheduler 高频(`apply_paid_invoices` 每 30s 1 次 = 单日 2880 行)
  会淹没 admin 行为信号;且 scheduler 不需要 actor / before-after 字段
- **当前默认**:**分开**,本 SPEC 只做 admin audit,scheduler 行为日志留
  v0.4 单独 SPEC
- ✅ **SEALED 决策(2026-04-30)**:**分开**(维持 SPEC 默认)
  - **理由**:audit log 是"运营追责 + 客诉举证"工具,服务对象是 admin/operator 行为镜像;scheduler 自动化事件每天上千条会把 admin 信号淹没,运营 query 体验崩
  - **`ops_events` 走单独 SPEC,留 v0.4**;v0.3 期间 scheduler 行为可在 `app.log` / Sentry / structured log 看,不需要 DB 表

---

## 依赖与解锁顺序

### 依赖

- ✅ Round 1 完成(rate-limit + Redis,中间件挂载链已建)
- ✅ Round 2 完成(billing payment_events 先例,加密路径已建,L-014)
- ✅ D-012(per-feature `*_TRUSTED_PROXIES`):AuditMiddleware 取 IP 时直接复用
  `_peer_is_trusted_proxy` helper

### 解锁

- 🔓 **RBAC**(SPEC-rbac 草稿中):RBAC 上线后第一时间需要 audit 验证权限边界,
  本 SPEC 必须**先于 RBAC PR 合入** otherwise RBAC 上线即盲飞
- 🔓 **多 admin 协作模式**(v0.4):没有审计 = 二级管理员不可信任
- 🔓 **客诉 / 故障复盘 SOP**(v0.4):runbook 强依赖审计可查

### 不依赖(可并行)

- ⏸ EPay / TRC20 已落地,本 SPEC 双写不阻塞二者
- ⏸ Deploy / SNI / Reality 各自独立 session

### 启动顺序

1. ~~**本 PR**(AL.0):docs-only,SPEC 合入~~ ✅ done(PR #101)
2. ~~用户决策 TBD-1~4~~ ✅ done(2026-04-30 CTO auto mode 拍板,issue #103 closed)
3. **AL.1 + AL.2 + AL.3 + AL.4** 串行落,**不拆并行**(共享 `ops/audit/`
   目录,session 内部不能并行)— **可立即启动 S-AL session**
4. RBAC SPEC(SPEC-rbac)在 AL.4 合入后启动 implementation

### 触发条件

本 SPEC **优先级 = P1**(SEALED 2026-04-30),已满足触发条件:

- 🔔 运营方提"我无法追责另一个 admin 的操作"
- 🔔 SPEC-rbac 草稿完成,准备 implementation 前置
- 🔔 客诉量 ≥ 3 / 周,需复盘工具
- 🔔 用户主动 push v0.3 路线图

---

## Kickoff prompt(粘贴到新 Claude Code 会话第一条消息)

```
/cto-resume

你是 Aegis Panel 项目 S-AL session(审计日志,ROADMAP v0.2 #4 + v0.3 #4 解锁
RBAC)。

读这五份文件作为上下文:
- docs/ai-cto/SESSIONS.md(查看 §S-AL Charter,若没有则按 D-011 流程登记)
- docs/ai-cto/SPEC-audit-log.md(本 SPEC,字段级合约)
- docs/ai-cto/DECISIONS.md#D-003(法律风险张力,落地必走的政策约束)
- docs/ai-cto/DECISIONS.md#D-012(trusted-proxy per-feature 模式)
- ops/billing/db.py(payment_events 先例 + Fernet 加密路径)

你的地盘独占:
  ops/audit/** + dashboard/src/modules/audit/** + tests/test_audit_*.py +
  docs/ai-cto/OPS-audit-log-runbook.md
禁动:
  app/** / hardening/** / dashboard/src/{auth,users,nodes,billing}/** /
  ops/billing/** / ops/iplimit/**
共享冲突点(append-only):
  hardening/panel/middleware.py 的 include_router 行
  app/db/extra_models.py 的 import 行
  dashboard/src/features/sidebar/items.tsx 的 sidebar 组(新增 audit 项)
  dashboard/src/i18n/{en,zh-cn}.json 的 audit 段(新增 key)

第一步:
  读完 5 份文件后,先确认 SPEC 中的 4 个 TBD 用户已决策(若未决策,在
  本 session 第一轮 stop 等用户拍板,不要擅自走默认值)。

第二步(TBD 决策后):
  按 SPEC §AL.1 ~ AL.4 顺序串行 PR,每个 PR ≤ 500 LOC,引用 AC-AL.x.y
  编号验收。严格 Spec-Driven。

铁律提醒:
  - audit 写失败不阻塞 handler(L-018);
  - REDACT_FIELDS 改动必须改 test;
  - 不删 payment_events 表;
  - 中间件挂载顺序 rate-limit → proxy → audit → router;
  - 加密 key 缺失 + 启用 → fail-loud(D-006)。
```

---

## 变更日志

- **2026-04-28** — 初稿。S-AL session 待用户启动。docs-only,无代码改动。
  4 个 TBD 段留给用户决策。法律风险张力(D-003)贯穿 Why / How.3 / Risks
  三处。
