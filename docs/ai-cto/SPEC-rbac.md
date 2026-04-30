---
title: SPEC — RBAC + 管理员分层(S-RB session)
created: 2026-04-28
status: SEALED
sealed: 2026-04-30
sealed_by: CTO(用户授权 auto mode 自动决策,issue #104 3 TBDs 全拍板)
priority: P2(v0.3 第二块,等 S-AL 完工后启动)
owner: CTO(可启 S-RB session)
depends_on:
  - SPEC-audit-log(并行草拟中,**先落** —— actor 维度需要 role 才有意义)
related:
  - ROADMAP.md v0.3 必做 #4(RBAC + 管理员分层,2 周)
  - VISION.md §商业化运营层 / §差异化 #2
  - DECISIONS.md D-003(法律合规留痕)
  - BRIEF-billing-user-auth-blocker.md(明确 user-side auth 不在本 SPEC 范围)
session_charter: S-RB(独占 `app/rbac/**` + `dashboard/src/modules/rbac/**` + 本 SPEC)
---

# SPEC — RBAC + 管理员分层(v0.3 差异化 #4)

> 本 SPEC 是 **S-RB session 的交付契约**。SPEC 合并后,后续 PR 按本 spec 落地
> `app/rbac/**`、`dashboard/src/modules/rbac/**`、Alembic 迁移、以及对现有
> `Depends(sudo_admin)` 的逐步替换。任何 RBAC 相关代码改动必须能引用到本 SPEC
> 的某条 Acceptance criterion,否则 scope creep。
>
> 参考 CTO handbook §7 Spec-Driven、SPEC-postgres-redis.md(D-005 模板)、
> SPEC-billing-mvp.md(中等复杂度范例)、SPEC-deploy.md(差异化 SPEC 范例)。

---

## 1. What

### 1.1 默认 4 角色

| Role key | 中文名 | 职责 | 典型权限片段 |
|---|---|---|---|
| `sudo` | 超管 | 拥有所有权限,系统设置、节点管理、密钥轮换 | `*:*:*`(内置 superset) |
| `ops` | 运维 | 节点 CRUD、Reality 加固、订阅审计、日常用户管理 | `nodes:*`、`users:*`、`reality:*`、`hardening:*` |
| `finance` | 财务 | billing 只读、对账、导出报表;**不能改 plan 价格、不能改用户配额** | `billing:read:*`、`billing:export:report`、`users:read:summary` |
| `support` | 客服 | user 只读 + 临时 unblock + 重发订阅链接;**不能改套餐、不能看支付密钥** | `users:read:*`、`users:write:enable`、`users:write:reset_subscription`、`billing:read:invoice_user_view` |

> ✅ **TBD-1 SEALED(2026-04-30)**:**选项 A — 默认 4 角色(sudo/ops/finance/support)+ custom role 机制**
> - **不补 auditor**:auditor = "ops + 只读" 子集,运营方可通过 RBAC 自带 custom role 创建,不需要硬编码默认
> - **不补 reseller**:二级代理 = multi-tenant 独立产品方向,不在 v0.3 scope(VISION 边界)
> - **custom role 机制**:Phase 3 UI 必须支持运营方创建 custom role + 分配 permission_key 子集
> - **revisit 信号**:运营方实战数据点 ≥ 3 次"现有 4 角色不够用"

### 1.2 角色可组合(matrix permission)

**核心约束**:角色不是 "互斥单选",一个 admin 可以同时持有 `ops + finance`(小机场常态:1-2 人身兼数职)。生效权限 = 所持角色权限的并集。

> 举例:Bob 持有 `ops + finance`,他能做 ops 全集 + finance 全集;但**没有** `sudo:*` 中独有的"删除 admin / 旋转 JWT secret",因为那是 sudo 专属。

### 1.3 边界(明确划出去)

- ❌ **不引入 user-side 角色** — VPN 用户没有 panel auth(见 `BRIEF-billing-user-auth-blocker.md`),引入 user 角色等于先解 user-auth blocker,出本 SPEC 范围。
- ❌ **不引入跨 panel 角色** — 单 panel 实例,不做 SSO / federation。如果运营 2 个独立机场,各自独立 admin 表。
- ❌ **不实现 ABAC**(基于属性的访问控制)— 当前 admin 数 < 20,RBAC 矩阵足够;ABAC 在 v0.4+ 视实际矛盾再提。
- ❌ **不做权限的 time-bound 自动撤销** — "今晚只给客服 unblock 权限,明早自动收回" 是 v0.4 演进。MVP 是 sudo 手工授予/撤销。
- ❌ **不动 Marzneshin upstream `Admin.is_sudo` 字段** — 保留向后兼容,sudo 视为"内置 role 拥有所有 permission"。
- ❌ **不动 Marzneshin upstream `Admin.modify_users_access` / `all_services_access`** — 这两个布尔字段是 upstream 的窄域权限标志,RBAC 上线后 deprecate 走逐步迁移,不在 MVP 内一刀切删除。

---

## 2. Why

引自 `VISION.md`:

> **商业化运营层** ⏳ 待建(差异化 #2)— 订阅计费 / 流量告警 / 到期续费 /
> **管理员 RBAC**

引自 `ROADMAP.md` v0.3 必做 #4:

> **RBAC + 管理员分层**(2 周)
> - `Role` + `Permission` 表
> - 默认角色:sudo / ops / finance / support
> - UI 管理角色 + 权限矩阵

引自 `DECISIONS.md` D-003(法律合规留痕):

> 商业化机场法律合规 —— 用户已知,CTO 留痕。CTO 的职责是提示和加固防御。

### 2.1 业务驱动力(为什么 v0.3 必须做)

1. **>200 用户运营 = 不可能 1 sudo 1 admin 二分法**。当前面板的权限模型只有
   `is_sudo` 布尔位 + 两个 upstream 窄域字段(`modify_users_access` /
   `all_services_access`),共 8 种组合,无法表达"财务能查账但不能改套餐"
   "客服能解封但不能看支付密钥"。运营 >200 用户必然分工(见 VISION 目标
   用户画像:操作者多人协作),分工必须有权限隔离。

2. **财务 / 客服两个角色与现有职责天然冲突**:
   - 财务对账时**不该看到客户支付密钥 / TRC20 私钥 / EPay merchant_key**
     (这些是运营级机密,泄露 = 资损)。
   - 客服解封用户时**不该能修改 plans 价格 / 旋转 Reality 私钥**
     (这是越权,也是社工攻击面)。
   - 当前模型下,只能"全开放"(全员 sudo)或"全关闭"(只 sudo 能做),
     两者都不可接受。

3. **与 audit log 联动 = 追责依据**。`docs/ai-cto/SPEC-audit-log.md`
   (并行草拟中)将记录 "谁 / 什么时候 / 做了什么"。但 "谁" 维度只是
   admin_id 远不够 —— 必须记录 **当时该 admin 持有的 role 集合**,因为:
   - 角色随时间变化(Bob 上周还是 finance,这周临时给了 ops)。
   - 出事追责要回答 "当时这个操作是 finance 角色合法做的,还是越权?"
   - 因此 audit log 的 `actor_role_at_time` 字段必须**快照**当时的 role,
     不能 lazy-join 现在的 role 表。
   - 这意味着 RBAC 的 role assignment 表要被 audit log 引用,RBAC 的
     模型必须先于 audit log 落地(或同 PR 一并落)。

4. **AGPL §13 合规与 D-003 留痕**:商业化运营场景下,operator 可能被司法
   要求"提供操作记录"。RBAC + audit log 是该要求下唯一的可信证据链 ——
   "这个删除操作是支持人员越权,不是 sudo 授权" 这样的说法只在有 RBAC
   之前的世界没有意义。

### 2.2 不做 RBAC 的代价(用作 trade-off)

如果 v0.3 不做 RBAC:
- 任何分工运营都得给员工 sudo,**单点失误 = 全局事故**(误删用户 / 误旋转
  JWT secret / 误改 SNI 配置)。
- 财务对账只能由 sudo 亲手做,**每月对账成 sudo 瓶颈**。
- audit log 没有 actor role 维度,**追责弱化** —— 只能查到 "admin 张三做了 X",
  没法快速判定 "X 是不是张三应当做的"。

---

## 3. How

### 3.1 数据模型(核心)

新增 3 张表(prefix `aegis_admin_` 与 billing 模块约定一致),**保留**
upstream `admins.is_sudo` 字段不动。

```python
# app/rbac/db.py — SQLAlchemy 2.0 typed mappings

class AdminRole(Base):
    """角色定义。系统内置 4 个(sudo/ops/finance/support)+ sudo 可创建自定义角色。"""
    __tablename__ = "aegis_admin_roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str] = mapped_column(String(32), unique=True)
    # "sudo" | "ops" | "finance" | "support" | "<custom_key>"
    display_name_en: Mapped[str] = mapped_column(String(64))
    display_name_i18n: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(String(256), default="")
    is_builtin: Mapped[bool] = mapped_column(default=False)
    # 内置角色不可删,可改 description 但 role_key 锁
    is_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime]


class AdminRoleAssignment(Base):
    """admin <-> role 多对多。一个 admin 可有多个 role。"""
    __tablename__ = "aegis_admin_role_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("aegis_admin_roles.id", ondelete="RESTRICT"), index=True
    )
    granted_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL")
    )
    granted_at: Mapped[datetime]
    # 唯一约束 (admin_id, role_id)


class RolePermission(Base):
    """角色 -> permission_key 多对一(每行一个 permission)。
    sudo role 不写明细行,运行时硬编码视为 superset。"""
    __tablename__ = "aegis_role_permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("aegis_admin_roles.id", ondelete="CASCADE"), index=True
    )
    permission_key: Mapped[str] = mapped_column(String(96))
    # 唯一约束 (role_id, permission_key)
```

复合索引:
- `(admin_id)` on `aegis_admin_role_assignments` —— 解析当前 admin 权限的主路径。
- `(role_id, permission_key)` UNIQUE on `aegis_role_permissions` —— 防重复授权。

**保留 `admins.is_sudo` 不动的理由**:
1. 向后兼容 —— upstream 同步区代码还在用,删掉等于 fork 永久 diverge。
2. 简化 bootstrap —— 数据库刚创建时还没有 RBAC 表,但要有第一个 sudo 进 panel 跑迁移。
3. 双保险 —— RBAC 表损坏 / migration 失败时,is_sudo 仍能保住 sudo 紧急访问。

运行时 `require_permission()` 决策顺序:
1. `admin.is_sudo == True` → ALLOW(superset short-circuit)
2. 否则查 `aegis_admin_role_assignments` × `aegis_role_permissions`,匹配 permission_key → ALLOW/DENY。

### 3.2 permission_key 命名

格式:`<scope>:<verb>:<target>`,**全部小写,segment 用 `:` 分,不含其他符号**。

| 例子 | 含义 |
|---|---|
| `users:read:list` | 列用户(隐藏支付密钥列) |
| `users:read:full` | 列用户(含支付密钥列,只 sudo 默认) |
| `users:write:expire_date` | 改用户到期时间 |
| `users:write:enable` | 启用/解封用户(临时 unblock) |
| `users:write:data_limit` | 改用户流量配额 |
| `users:write:reset_subscription` | 重发订阅 URL(客服常用) |
| `users:delete:any` | 删除用户(高危) |
| `nodes:read:*` | 节点列表 / 详情 / 状态 |
| `nodes:write:*` | 节点 CRUD |
| `billing:read:plan` | 看套餐定义 |
| `billing:write:plan` | 改套餐 / 价格(财务 ❌,sudo ✅) |
| `billing:read:invoice` | 看 invoice 列表 |
| `billing:read:invoice_user_view` | 客服角度看 invoice(屏蔽 EPay merchant_key / TRC20 私钥) |
| `billing:export:report` | 导出对账报表 |
| `reality:read:audit` | 调 `/api/reality/audit` |
| `reality:write:rotate_keys` | 旋转 Reality keypair(高危,sudo only) |
| `hardening:read:health` | 调 `/api/aegis/health/extended` |
| `system:write:settings` | 改 SubscriptionSettings / TelegramSettings |
| `rbac:read:roles` | 看 role 定义 |
| `rbac:write:assign` | 给 admin 授/撤角色 |
| `audit:read:log` | 看审计日志 |

**通配支持**:
- 角色权限行可以写 `users:read:*` 表示 "所有 users:read:* 系列"。
- 不支持 `users:*:*`(避免误授);要全开就直接给 sudo。
- 不支持 prefix 之外的通配(`*:read:list` 不合法)。

> ✅ **TBD-2 SEALED(2026-04-30)**:**选项 A — `<scope>:<verb>:<target>` 锁定**(维持 SPEC 默认)
> - **理由**:OAuth / Casbin / Keycloak / AWS IAM / GCP IAM 主流标准,scope-first 易 group / 易 SQL prefix 查
> - **不选 `<resource>.<action>` (dot-separated)**:dot 是正则特殊字符,IDE/SQL filter 难精确匹配
> - **不选 snake_case (`users_read_list`)**:无层次结构,group 难
> - **S-RB 第一周仍要做 PoC**:用 1 个 admin endpoint 验证 grep 噪声(不是改风格,而是验证编码 hygiene)

### 3.3 中间件 / FastAPI Depends 替换

新增 `app/rbac/deps.py`:

```python
def require_permission(permission_key: str):
    """生成一个 FastAPI Depends 工厂。用法:

        @router.get("/api/billing/admin/invoices",
                    dependencies=[Depends(require_permission("billing:read:invoice"))])
        async def list_invoices(...): ...

    实现伪代码:
        admin = await get_current_admin(...)
        if admin.is_sudo:
            return admin                                        # superset
        if has_permission(db, admin.id, permission_key):        # 含通配解析
            return admin
        raise HTTPException(403, detail="permission denied: ...")
    """
```

新增 `RBACAdminDep = Annotated[Admin, Depends(get_current_admin)]` —— 与现有
`AdminDep` 等价,但语义上声明"该接口走 RBAC"。

**性能**:每请求 1 次 join 查询(`role_assignments × role_permissions WHERE
admin_id = X AND permission_key MATCHES Y`),走 `(admin_id)` 索引;预期
< 1ms(SQLite < 20 admin 数量级)。可选优化(MVP 不做):
- Redis 缓存 `admin_id -> permission_set`,TTL 30s,role 变更时主动 invalidate。
- 进程内 LRU(<200ms TTL)防短时风暴(login 后短时多 endpoint 调用)。

### 3.4 Migration 策略(保留 is_sudo,逐步替换)

**Phase 1 — RBAC 表落地(本 SPEC 第 1 个 PR,RB.1)**:
- Alembic migration 加 3 张表 + 内置 4 角色种子(sudo / ops / finance / support)。
- 内置 4 角色默认 enabled。`sudo` role 不写权限明细行(superset 短路)。
- 其他 3 角色按 §3.2 默认 permission_key 集合预填。
- **不**触碰任何现有 endpoint Depends 链 —— 新表是死表,数据写但运行时不读。
- AC:`alembic upgrade head` 在 SQLite + PG 16 双 CI 通过;现有所有测试不变。

**Phase 2 — Depends 替换(RB.2)**:
- 新增 `require_permission()` 工厂。
- 给所有 `/api/billing/admin/*`、`/api/reality/*`、`/api/aegis/health/extended`、
  `/api/admins/*`、`/api/system/*`、`/api/nodes/*` endpoints 同时挂上
  `Depends(sudo_admin)` **和** `Depends(require_permission(...))`(双保险)。
- 在测试模式下加 metric:每次 RBAC check 命中 sudo short-circuit 计数 vs
  permission lookup 计数,跑一周观察是否有真实需求 endpoint 漏挂。

**Phase 3 — 给非 sudo admin 授角色(RB.3)**:
- Dashboard 加 "角色管理" 页(只 sudo 可见)。
- CLI / API 提供 `marzneshin-cli rbac assign <admin> <role>`。
- 文档列举:运营首次怎么把现有 5-10 个 admin 分配到 ops / finance / support。
- 这一步开始,非 sudo admin 真正按 RBAC 走。

**Phase 4 — 移除 `Depends(sudo_admin)` 双保险(v0.3 末或 v0.4 初)**:
- 跑 N 周观察 metric,无未覆盖 endpoint。
- 删掉旧 Depends,只留 RBAC。
- `is_sudo` 字段保留,语义降级为 "拥有所有 permission 的内置 role 标志位"。

> ✅ **TBD-3 SEALED(2026-04-30)**:**选项 A — 6 周 4-Phase 总长**(维持 SPEC 默认)
> - **Phase 1 schema**(1 周)/ **Phase 2 dual-gate**(2 周)/ **Phase 3 UI**(2 周)/ **Phase 4 deprecation**(1 周)
> - **不选 3 周快版**:dual-gate 缩到 1 周不够运营方做角色映射,漏权限风险高
> - **不选 12 周慢版**:over-cautious;以每周 20-30h 节奏,4-Phase = 6 周已能容纳 PoC + 漏覆盖修复
> - **S-RB 启动时仍要做 endpoint 数量统计**:若 endpoint > 80 → Phase 2 延长到 3 周,总长 7 周(单一调整变量)

### 3.5 Dashboard UI(`dashboard/src/modules/rbac/`)

只在 sudo 视图下出现一个 "RBAC" 顶栏入口,内含:

| 页面 | 路径 | 功能 |
|---|---|---|
| 角色管理 | `/dashboard/rbac/roles` | 列内置 + 自定义 role,看每个 role 的 permission 矩阵;改 description / 增删自定义 role permission 行(内置 role 的 permission 不可改,只读)|
| 管理员列表 | `/dashboard/rbac/admins` | 列所有 admin,显示当前持有 role 标签;sudo 可点 "授角色" / "撤角色" |
| 切换角色测试视图(可选)| `/dashboard/rbac/preview-as` | sudo 临时模拟 "如果我是 ops,看到的 dashboard 是什么样"。**只读模拟**,不真的改 session;用于 sudo 验证 role 配置不漏不溢 |
| 审计日志(深链)| `/dashboard/audit?actor=...` | RBAC 改动也走 audit log,role 管理页 → audit log 反查链 |

i18n:8 语言 key 走 `rbac.roles.*` / `rbac.admins.*` namespace,en + zh-cn 全译,
其他 6 语言英文 placeholder(对齐 SPEC-billing-mvp.md i18n 策略)。

**MVP 范围**:RBAC backend + CLI 配置必须先落,dashboard UI 可以滞后 1 个
sub-PR。换言之 RB.1 + RB.2 不阻塞于 dashboard。

### 3.6 与 audit log 联动(关键!)

audit log SPEC 并行草拟中,但 RBAC 必须**预留** integration 点:

1. **role assign / revoke 操作 → audit log 单独事件**:
   - event_type: `rbac.role_assigned` / `rbac.role_revoked`
   - payload: `{admin_id, role_id, role_key, granted_by, reason?}`
   - 这是 D-003 留痕的强需求 —— "谁给谁授权,后果谁担"。

2. **audit log 的 actor 维度记录 `actor_role_at_time`**:
   - 每条 audit 行写当时 admin 持有的 `role_keys: list[str]` 快照。
   - **快照**而非 lazy-join,因为 role 会变,但当时的合法性判定要看当时的 role。
   - 因此 audit log 表的 `actor_role_keys_snapshot` 字段在 audit log SPEC
     中必须存在 —— 跨 SPEC 合约,在 audit log SPEC 草拟时同步落入。

3. **RBAC 自身管理变更走 audit log**:
   - 创建/删除自定义 role → audit
   - 改 role permission → audit
   - assign / revoke → audit(同 #1)
   - 内置 role 的 description i18n 改动 → audit(轻量但留痕)

> 因此 SPEC-audit-log 与本 SPEC 的依赖方向:**audit log 表先落**,但 audit log
> 的 `actor_role_keys_snapshot` 字段格式由本 SPEC 锁定。两个 SPEC 必须 cross-link
> review 确保字段对齐。

### 3.7 配置 / `.env`(可选,基本零新增)

| Var | Default | 用途 |
|---|---|---|
| `RBAC_ENFORCE_MODE` | `enforce` | `enforce` 严格 / `audit_only` 仅打 metric 不拦截(Phase 2 灰度用)/ `disabled` 完全旁路(紧急 break-glass)|
| `RBAC_PERMISSION_CACHE_TTL_SECONDS` | `0` | 0 = 关缓存(MVP 默认);>0 = 进程内 LRU TTL |

`disabled` 模式仅用于紧急(RBAC 表损坏导致全员 403),要写在 `OPS-rbac-runbook.md`,默认值不能动。

---

## 4. Risks 矩阵

| 等级 | 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|---|
| **高** | **迁移期 admin 锁死** —— 写错 permission key / role 没绑对 admin,导致全员 403 | 中 | 极高 | (a) Phase 2 双保险:`sudo_admin` + `require_permission` 并行,任一通过即放;(b) `RBAC_ENFORCE_MODE=audit_only` 灰度模式,1 周观察 metric;(c) `RBAC_ENFORCE_MODE=disabled` break-glass 一键回退到旧 sudo 模型;(d) seed migration 的 4 个内置角色权限明细必须在测试中显式断言(测试列举每个 endpoint 期望的 role 集合) |
| **高** | **角色组合不当 → 越权** —— ops + support 组合刚好凑齐 sudo-only 操作面 | 中 | 高 | (a) 默认 4 角色权限定义在 PR review 时按"最小权限原则"逐 endpoint 列表对照;(b) `users:delete:any` / `reality:write:rotate_keys` / `system:write:settings` 等高危操作只给 sudo,不进任何非 sudo 角色;(c) 新增自定义 role 时,sudo UI 警告"包含高危 permission";(d) e2e 测试矩阵覆盖所有 4×3 = 6 种 2-角色组合 + 单角色 4 种 |
| 中 | **性能开销** —— 每请求 join roles + permissions | 高 | 低 | (a) `(admin_id)` 索引;(b) sudo short-circuit 路径无 join;(c) 监控 P95 lookup 时间,>5ms 启用 §3.3 进程内 LRU;(d) PG 16 + Redis 7 已是 Round 1 基础设施,缓存基础设施现成 |
| 中 | **与 audit log 双写** —— role assign 同时写 RBAC 表 + audit log,部分失败 | 中 | 中 | (a) 同事务写两表(SQLAlchemy session 内);(b) audit log 写失败 → 整个 role assign 操作回滚(audit-first 强约束);(c) 单元测试 mock audit log 失败场景断言回滚 |
| 中 | **upstream `is_sudo` 与 RBAC 双轨歧义** —— 哪个是真相 | 中 | 中 | (a) `is_sudo == True` 永远是 superset 短路,文档明示;(b) RBAC 不能"撤销 sudo 的权限";(c) 想降级 sudo,直接改 `is_sudo` 字段,而不是通过 RBAC role |
| 中 | **内置 role 命名碰撞** —— 用户已有 admin username 是 "ops" 等,UI 显示混淆 | 低 | 低 | role_key 与 admin username namespace 完全分离,UI 上 role 标签用配色 + 前缀图标区别 |
| 低 | **角色定义膨胀** —— 用户狂建自定义 role,后期维护噩梦 | 低 | 低 | (a) UI 限制 ≤ 50 自定义 role(硬上限);(b) 文档建议 "先用 4 个内置,2 周后再考虑自定义";(c) audit log 可查 role 创建历史,后悔时可清理 |
| 低 | **i18n 漂移** —— role description 多语言不同步 | 中 | 低 | 复用 `tools/check_translations.sh` 的 diff-based 漂移门(billing 已落),`rbac.*` namespace 入门槛与 billing 一致 |
| 低 | **CLI 工具被滥用作 break-glass** —— `marzneshin-cli rbac assign` 绕过 dashboard audit | 低 | 中 | CLI 工具内部强制走 RBAC service 层,该层无条件写 audit log;CLI 不能 "off the record" |

---

## 5. Acceptance criteria

> 按 PR 拆分,每个 PR body 必须勾选自己的 AC。

### RB.0 — 本 SPEC 落地

- [ ] **AC-RB.0.1** `docs/ai-cto/SPEC-rbac.md`(本文件)merged
- [ ] **AC-RB.0.2** `docs/ai-cto/SPEC-audit-log.md` cross-link review,
      `actor_role_keys_snapshot` 字段对齐(并行 SPEC 合并 ±3 天)
- [ ] **AC-RB.0.3** `docs/ai-cto/DECISIONS.md` 追加 D-XXX RBAC 决策记录
      (默认 4 角色 + matrix permission + 保留 is_sudo 三个选择的依据)

### RB.1 — 数据模型 + seed

- [ ] **AC-RB.1.1** Alembic migration `<date>_rbac_init.py` 加 3 张表 + 索引,
      SQLite + PG 16 双 CI 通过
- [ ] **AC-RB.1.2** Migration seed 4 内置 role(sudo/ops/finance/support);
      `is_builtin=True` 锁定;ops/finance/support 的 permission 明细按 §3.2 预填
- [ ] **AC-RB.1.3** 单元测试覆盖:`compute_admin_permissions(admin_id)`
      正确返回 superset(sudo)/ 单 role 集合 / 多 role 并集 / 通配展开
- [ ] **AC-RB.1.4** 单元测试覆盖:删除/禁用 role 时 cascade 行为符合预期
      (不级联删 admin;级联删 permission rows;阻止删除内置 role)

### RB.2 — Depends + endpoint 替换(双保险)

- [ ] **AC-RB.2.1** `app/rbac/deps.py::require_permission(key)` 实现;sudo
      short-circuit + 通配解析 + DB lookup
- [ ] **AC-RB.2.2** 所有 `Depends(sudo_admin)` 的 endpoint 同时挂
      `Depends(require_permission(...))`,key 与 §3.2 一致
- [ ] **AC-RB.2.3** `RBAC_ENFORCE_MODE=enforce|audit_only|disabled` 三模式
      行为正确(enforce 拦截 / audit_only 仅 metric / disabled 旁路)
- [ ] **AC-RB.2.4** 性能基线:1000 req/s 压力下,RBAC permission lookup
      P95 < 5ms(无缓存,纯 DB)
- [ ] **AC-RB.2.5** Audit log integration:每次 RBAC permission DENY 写一条
      `audit.permission_denied` event,含 admin_id / endpoint / required_key

### RB.3 — UI + CLI

- [ ] **AC-RB.3.1** Dashboard `/dashboard/rbac/roles` 页可看 4 内置角色 +
      permission 矩阵(只读)
- [ ] **AC-RB.3.2** Dashboard `/dashboard/rbac/admins` 页 sudo 可授/撤角色,
      授/撤动作触发 audit log 写入
- [ ] **AC-RB.3.3** `marzneshin-cli rbac {list-roles, list-admins, assign,
      revoke}` 4 个子命令全功能,与 dashboard 等价
- [ ] **AC-RB.3.4** i18n en + zh-cn 完整;其他 6 语言英文 placeholder
- [ ] **AC-RB.3.5** "切换角色测试视图"(可选)若实现,sudo 模拟 ops 视角时
      只读不可写

### RB.4 — 移除双保险(v0.3 末)

- [ ] **AC-RB.4.1** Metric 显示连续 4 周无 sudo_admin 通过但 require_permission 拒绝的 case
- [ ] **AC-RB.4.2** `Depends(sudo_admin)` 全面替换为 `Depends(require_permission(...))`
- [ ] **AC-RB.4.3** `is_sudo` 字段语义降级文档化(NOTICE.md / DEVELOPMENT.md)

---

## 6. 依赖与顺序

### 6.1 强依赖

- **被 audit log 解锁**:`SPEC-audit-log.md` 必须先落到 `audit_logs` 表能写
  数据;RBAC 的所有变更(role assign / permission deny)依赖 audit log 写入
  通道。换言之 audit log SPEC 是 RBAC 实现的前置。
- **不依赖 user-side auth**:本 SPEC 完全不涉及 VPN 用户认证(见
  `BRIEF-billing-user-auth-blocker.md`)。RBAC 是 admin-only。
- **不依赖 RBAC dashboard UI**:MVP 可先 backend + CLI 跑通(RB.1 + RB.2),
  dashboard UI(RB.3)可顺延 1 个 sub-PR。运营若紧急上线,CLI 可 first-class
  支撑。

### 6.2 推荐落地顺序

```
SPEC-audit-log.md draft         → docs PR
SPEC-rbac.md draft (本文件)      → docs PR(可与 audit log SPEC 并行)
                ↓
RB.0 本 SPEC merged
                ↓
audit log RB-A.1 表 + 中间件   ← 强依赖
                ↓
RB.1 RBAC 表 + seed
                ↓
RB.2 require_permission + endpoint 替换(双保险并行)
                ↓
RB.3 dashboard + CLI
                ↓
观察 4 周 metric
                ↓
RB.4 移除双保险
```

### 6.3 可选并行

- audit log RB-A.2(audit log dashboard 页)与 RB.3(RBAC dashboard 页)可
  同期实现,共享 `dashboard/src/modules/{audit,rbac}/` 模块化骨架。
- 性能优化(Redis 缓存 permission set)v0.4 视监控数据再启动,不阻塞 v0.3。

---

## 7. Kickoff prompt(给未来 S-RB session 启动)

```
/cto-resume

你是 Aegis Panel 项目 S-RB session(RBAC + 管理员分层,ROADMAP v0.3 必做 #4)。

读这三份文件作为上下文:
- docs/ai-cto/SESSIONS.md(§S-RB Charter,若已写)
- docs/ai-cto/SPEC-rbac.md(本 SPEC)
- docs/ai-cto/SPEC-audit-log.md(强依赖,先理解 actor_role_keys_snapshot 字段约定)

你的地盘独占:
  app/rbac/**
  dashboard/src/modules/rbac/**
  alembic/versions/<date>_rbac_*.py
  docs/ai-cto/SPEC-rbac.md
  docs/ai-cto/OPS-rbac-runbook.md(待建)

禁动:
  app/dependencies.py 的 sudo_admin / get_admin —— 上游同步区,只**新增**
    `require_permission`,**保留**双保险,不删旧 dep
  app/db/models.py 的 Admin 模型 —— 不删 is_sudo,不改 modify_users_access /
    all_services_access 字段
  ops/billing/** —— S-F session 地盘,RBAC 替换 endpoint Depends 时必须
    与 S-F 协调
  hardening/** —— S-R session 地盘,reality:* / hardening:* permission key
    具体内容由 S-R 决定

共享冲突点:
  app/routes/*.py(各 endpoint)—— 替换 Depends 必须每个 PR 列清触碰 endpoint
    清单,通过 SESSIONS.md 协调

第一步(RB.0 已完成,你接 RB.1):
  1. 拉分支 `feat/rbac/RB.1-models`
  2. 写 Alembic migration,3 张表 + 4 内置 role seed
  3. 写 `app/rbac/db.py` SQLAlchemy 模型 + `app/rbac/permissions.py` permission
     key 常量与解析
  4. 单元测试至少 12 case 覆盖 AC-RB.1.3 + AC-RB.1.4
  5. PR body 引用 AC-RB.1.* 编号

铁规则:
  - 不动 is_sudo 字段语义(superset short-circuit 永远生效)
  - 内置 4 role 的 permission 明细在 RB.1 seed 时**必须有测试断言**列出来,
    review 时一行行人眼对照,不能 "差不多就行"
  - i18n 走 rbac.* namespace,en + zh-cn 必填,其他英文 placeholder
  - 严格 Spec-Driven:本 SPEC 没说的不做,SPEC 该改先改 SPEC

3 个 TBD 已在 D-019 SEALED(2026-04-30,见 DECISIONS.md#D-019,issue #104):
  - TBD-1 默认角色集 → **4 角色(sudo/ops/finance/support)+ custom role 机制**
    (不内置 auditor / reseller,需要时由 sudo 用 custom role 创建)
  - TBD-2 permission_key 风格 → **`<scope>:<verb>:<target>` 锁定**(维持 SPEC 默认)
  - TBD-3 Phase 2 → Phase 3 双保险并行长度 → **6 周 4-Phase 总长**(维持 SPEC 默认)

无需再走 CTO 确认 — D-019 已是先决定下的最终决策,直接按 SPEC §1.1 / §3.2 / §3.4
落实现。
```

---

## 变更日志

- **2026-04-28** — DRAFT 创建。S-RB session 尚未启动;本 SPEC 为 docs-only PR。
  6 段结构按任务规范定稿,3 个 TBD 标注待 S-RB 第一周 PoC 验证。Cross-link
  audit log SPEC(并行草拟中),约定 `actor_role_keys_snapshot` 字段格式由
  本 SPEC 锁定。
- **2026-04-30** — frontmatter `status: DRAFT → SEALED`,3 个 TBD 全部由 CTO
  (auto mode)在 issue #104 拍板,记录于 D-019。§7 Kickoff prompt 同步更新,
  移除"待 sudo 拍板 / 第一周内必须确认"语,直接引用 D-019 决策结果。
