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
