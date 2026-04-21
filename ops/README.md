# ops/ — 商业化运营层(自研)

**职责**: 让项目**能变现 + 能审计 + 能分权**。运营相关的数据模型、任务、
UI 扩展,全部放这里,与 `app/`(upstream 同步区)解耦。

**License**: 默认 AGPL-3.0(涉及数据模型与 `app/db/` 衍生)。

---

## 子模块规划

| 子目录 | 状态 | 职责 | 阶段 |
|---|---|---|---|
| `billing/` | ⏳ 待建 | `Subscription` / `Payment` / `Invoice` 模型 + 手动激活/续费 API | v0.2 计费 MVP |
| `audit/` | ⏳ 待建 | `AuditLog` 表 + 中间件自动记录管理员操作 + dashboard 查询页 | v0.2 |
| `alerting/` | ⏳ 待建 | 超额 / 临期 / 异常登录告警(email + Telegram + Webhook) | v0.2 |
| `rbac/` | ⏳ 待建 | `Role` + `Permission` 表,默认角色 sudo/ops/finance/support | v0.3 |

## 与 `app/db/models.py` 的关系

**新表定义放本目录**(例如 `ops/billing/models.py`),由主 `app/db/base.py`
统一 `import` 进元数据,但**不修改 upstream models.py**。Alembic 迁移统一到
根 `alembic/versions/`。

## 关键决策

- **审计日志 append-only**:只 INSERT,永不 UPDATE / DELETE;运维人员无删改权限
- **订阅状态机状态有限**:`pending / active / expired / cancelled`,禁止裸字符串
- **金额统一存最小单位**(分/satoshi),数据库字段 `Numeric(18, 0)`,避免浮点

## 暂无实现。
