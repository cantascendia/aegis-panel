---
name: python
description: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic 编码规范(Marzneshin fork 后端)
activation: glob
globs:
  - "**/*.py"
  - "requirements.txt"
  - "pyproject.toml"
  - "alembic.ini"
---

# Python 编码规范(Marzneshin Reality 2026 fork)

## 类型标注(强制)

- 所有 public function / method 必须有完整 type hints(参数 + 返回)
- SQLAlchemy 2.0 用 typed mappings:`Mapped[str]` / `Mapped[int | None]`,不用旧式 Column
- Pydantic 2.x:BaseModel 字段必须 typed,用 `Field(...)` 加约束
- FastAPI 路由参数必须标注类型以启用自动验证

```python
# ✅ 好
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    traffic_limit: Mapped[int | None] = mapped_column(nullable=True)

# ❌ 不好
class User(Base):
    id = Column(Integer, primary_key=True)
```

## 异步优先

- FastAPI 路由默认 `async def`,除非函数确实是纯 CPU 计算
- 数据库用 async sqlalchemy(`AsyncSession`)调用
- HTTP 调用用 `aiohttp`,不用阻塞的 `requests`(上游已有 `requests==2.32.2` 仅限 CLI/脚本使用,路由里禁用)
- 不要在 async 函数里调用阻塞 I/O;必要时用 `asyncio.to_thread`

## 错误处理

- 禁止 `except: pass` 和 `except Exception as e: pass`
- 捕获必须明确异常类型,处理必须 log 或 re-raise 或 fallback
- 路由层统一返回结构化错误(HTTPException with detail),不泄露 stack trace

```python
# ✅ 好
try:
    node = await marznode_client.get_node(node_id)
except NodeUnreachableError as e:
    logger.warning("marznode %s unreachable: %s", node_id, e)
    raise HTTPException(503, detail="node_temporarily_unavailable")

# ❌ 不好
try:
    node = await marznode_client.get_node(node_id)
except:
    pass
```

## 密钥与配置

- 禁止硬编码 token / password / secret / UUID
- 通过 `python-decouple` 的 `config()` 读 `.env`
- JWT secret、DB 密码、CF 凭据、Xray UUID 必须走 `.env`,**禁止存 DB 作为唯一 source of truth**(审核 AUDIT.md 第 4 维第 2 条)
- 不要 commit `.env` 或任何 `.secret.*` 文件

## 日志

- 用 Marzneshin 已有的 `from app.utils.logger import get_logger`(或 app 内统一 logger),不 `print`
- 日志级别:DEBUG(开发)/ INFO(关键事件)/ WARNING(降级)/ ERROR(失败但可恢复)/ CRITICAL(需人介入)
- 不要 log 敏感数据(JWT、密码、完整 Xray UUID)

## 数据库

- 所有 DB 访问通过 repository / service 层,不在路由中直接写 ORM 查询
- `>200 用户` 场景敏感:任何涉及用户列表/订阅/流量的查询,先 explain analyze,加索引
- N+1 嫌疑点:用 `selectinload` / `joinedload` 预加载关系
- 事务边界明确:每个业务动作一个事务,不跨动作
- Alembic 迁移必须幂等:`op.execute("IF NOT EXISTS ...")` 或等价语法

## Alembic migrations(硬规则)

### 1. 已 merge 的 revision 不可 mutate

**一条 Alembic revision 一旦 commit 到 main,它的 `upgrade()` / `downgrade()` / `revision` / `down_revision` 四个字段永不修改**。文件的 docstring / 注释可以改,schema 操作不能动。

**理由**: Alembic 只按 revision id 判 at-most-once —— `alembic_version` 表不比对内容。任何已跑过该 revision 的环境(开发机 / staging / 生产)**永远不会重跑被修改的 `upgrade()`**,导致 DB schema 与代码永久脱钩。CI 的 fresh-DB 跑从零到 head 看不到这个 bug(见 LESSONS L-016 的 stepped-upgrade CI job)。

**需要给已 merge 的 migration 增加 schema 操作时**:

- ✅ 新建下游 revision,`down_revision = <上一个 head>`
- ✅ 如果补救的是"已部署环境 schema 缺失",用幂等 safety-net 模式:
  ```python
  from sqlalchemy import inspect
  def upgrade() -> None:
      bind = op.get_bind()
      if "my_table" in inspect(bind).get_table_names():
          return  # clean env already has it
      op.create_table("my_table", ...)
  ```
- ✅ safety-net 的 downgrade 一般设为 no-op,避免与被 mutated 的老 revision 的 drop 冲突(参见 `20260423_44c0b755e487_iplimit_disabled_state_safety_net.py`)
- ❌ 不要回去改原 revision 文件里的 `op.create_table` / `op.add_column` 等
- ❌ 不要修改已发布 revision 的 `revision` 或 `down_revision` 字段(会让整个 chain 错乱)

**Code review checklist**: 看 migration PR 时必看 `git log <filename>` —— 只有 "新文件"(第一次出现)允许修 `upgrade()` body,已存在的 migration 只允许改文档/注释。

**CI 门禁**: `.github/workflows/api-ci.yml` 的 `test-alembic-stepped` job 模拟"环境卡在 base head"的场景,mutated revision 过不了 metadata-vs-DDL 校验,merge 前被拦下。

参见 LESSONS L-015(规则) + L-016(CI 防线)。

### 2. 自研模块 SQLAlchemy model 必须注册到 aggregator

**所有 `hardening/*/db.py` / `ops/*/db.py` 里定义的 `class Foo(Base)` 必须通过 `app/db/extra_models.py` 统一注册**,**不要**直接改 `app/db/migrations/env.py`。

```python
# ✅ 好 —— 注册到 aggregator
# app/db/extra_models.py
import hardening.iplimit.db  # noqa: F401
import hardening.sni.db      # noqa: F401   ← 新模块加这里
import ops.billing.db        # noqa: F401

# app/db/migrations/env.py 保持单行:
import app.db.extra_models  # noqa: F401


# ❌ 不好 —— 在 env.py 里散装加 import
# app/db/migrations/env.py
import hardening.iplimit.db  # noqa: F401
import hardening.sni.db      # noqa: F401
import ops.billing.db        # noqa: F401
```

**理由**:
- `env.py` 是 upstream 同步区文件,每次 `git fetch marzneshin-upstream` rebase,多一行 import 多一次人工冲突 reconcile
- 模型散装在 env.py 读者难发现 "这个 fork 到底加了哪些自研表",aggregator 提供单一 grep 入口
- SQLAlchemy 的 `Base.metadata` 是**副作用注册**机制 —— `class Foo(Base)` 必须被执行过才进 metadata;aggregator 保证 Alembic `target_metadata = Base.metadata` 看到完整视图

**强制 review checklist**: 新 PR 如果包含 `hardening/*/db.py` 或 `ops/*/db.py` 的 `class Foo(Base)`,必须同时:
1. 把该文件 import 加到 `app/db/extra_models.py`
2. **禁止**再修 `app/db/migrations/env.py`(aggregator 已在那里 import)
3. 配套 Alembic migration 走新 revision(见上一条规则)

参见 LESSONS L-014。

## 测试

- `pytest tests/` 是 CI 必跑项
- 新功能必须配测试:至少 1 个 happy path + 1 个 error path
- 测试用独立 SQLite / PG test container,不跑在生产 DB
- Mock 外部服务(marznode gRPC、Telegram、CF API),不连真服务

## 依赖管理

- 引入新依赖前检查 license 与 AGPL-3.0 兼容性
- 固定版本:`==X.Y.Z`,不用 `>=`
- 依赖数每次 review,移除不再使用的
- 避免深度嵌套依赖(审计 `pip list --format=freeze | wc -l`,增长异常要问理由)

## 格式化与 lint

**Ruff** 是本项目唯一的 Python lint/format 工具(Round 1 起,`[tool.ruff]` 在 `pyproject.toml`)。

- **line-length=79**(对齐 upstream 历史 black 配置,不擅自加宽 —— 会引爆 upstream-sync diff)
- **`target-version = "py312"`**,项目 Python 严格 3.12
- 命令:`ruff check hardening deploy ops tests`(lint)/ `ruff format hardening deploy ops tests`(format)

**硬规则:CI 的 `ruff check` / `ruff format --check` 只扫自研目录**(`hardening` `deploy` `ops` `tests`),**不扫 upstream `app/` 和 `dashboard/`**。
- 理由:对 upstream 强推 ruff 风格会让每次 `git fetch upstream` 的合并冲突爆炸
- 新增自研目录(未来 `ops/billing/` 等)同规则加到 CI 里
- 真的要接管 upstream 风格,单独开 "format sweep" PR 一次性做完,且要评估 upstream 是否还活跃

**import 顺序**:stdlib / third-party / app(ruff `I` 规则已强制)。`from __future__ import annotations` 在所有自研模块顶部统一开启。

**模块顶部没有 `__all__` 就不导出私有函数**。

## 测试基础设施(pytest)

- **`pyproject.toml` 的 `[tool.pytest.ini_options]` 必设 `pythonpath = ["."]`**。否则直调 `pytest`(非 `python -m pytest`)时 CWD 不入 sys.path,测试能否 import `app.*` 取决于字母序(alembic 先 init 会副作用修正,不先就炸)—— 参见 `docs/ai-cto/LESSONS.md#L-003`
- `asyncio_mode = "auto"`,async test 不需要每个加 `@pytest.mark.asyncio`
- warnings-as-errors 当前**关**,等 upstream 依赖的 deprecation 清干净后再开
- 测 "模块级 raise" 时**不要用 `importlib.reload`** —— 重建 class 让 `pytest.raises` 身份失配,改 monkeypatch 模块常量 + 调内部函数(`_build_xxx`) —— `LESSONS.md#L-002`

## Marzneshin 特定

- `app/marznode/` 下的 gRPC 客户端要考虑节点不可达 / 超时 / 响应异常,不要假设 happy path
- `app/tasks/` 下 APScheduler 任务必须幂等且能处理失败重试
- `app/routes/` 下每个路由必须有 dependency-injected 权限校验(见 `app/dependencies.py`)
