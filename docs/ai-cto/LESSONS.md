# 会话级教训(LESSONS)

> 记录每轮次里**以小代价换来的 CI / 工具 / 流程教训**,防止同一个坑走两次。
>
> 格式:编号 + 发现轮次 + 现象 + 根因 + 落地防线(rule / config / habit)
>
> 凡沉淀成硬规则(`.agents/rules/*.md`)的,标注 ✓ 并指向文件。未沉淀的先在这里留痕,下轮开始前批量转 rule。

---

## L-008 | Round 1 tail | PR 标题 scope **必填**,不仅 type 要合法

**现象**: PR #9 第一次标题 `chore: promote LESSONS to .agents/rules + drop [tool.black]`,`Conventional Commit Title` 校验失败。合并前 user 改成 `chore(rules): promote ...` 才过。

**根因**: 本仓 `amannn/action-semantic-pull-request` workflow 配了 `requireScope: true`。type 合法只是必要条件,scope 段也必须出现。上一条 L-007 只讲了 type 白名单,没讲 scope 必填,措辞模糊。

**防线**: PR 标题**永远**写成 `<type>(<scope>): <description>`,不省 `(scope)`。首选 scope 词典:`security / hardening / infra / cache / cd / memory / rules / spec / deps`。新领域的 scope 首次出现时记一下,下次沿用同名。

**沉淀**: ✅ 已更新 `.agents/rules/git-conventions.md`,把"scope 可自定义"改为"**必填**",并给了常用 scope 词典。

---

## L-007 | Round 1 | PR 标题 conventional types 白名单很窄

**现象**: PR #2 初始 title `hardening(p0): JWT secret + CORS + bcrypt + auth deps` 被 `amannn/action-semantic-pull-request` 拒绝,CI 红。

**根因**: upstream 配置的 conventional commit types 白名单是 `build / chore / ci / docs / feat / improve / fix / merge / perf / refactor / refact / revert / style / test / wip`。`hardening` 不在列表。

**防线**: 未来命名 PR 标题,**type 段只能选白名单值**。scope 可以任意,所以 `fix(security): ...` / `feat(hardening): ...` 都合法,但 `hardening(...)` / `security(...)` / `harden(...)` 都会炸。

**沉淀**: ✅ 已转 `.agents/rules/git-conventions.md`。

---

## L-006 | Round 1 | Docker Compose `${VAR:?err}` 在 profile 过滤**之前**展开

**现象**: PR #4 合并前 docker-compose.yml 的 `POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"` 让 `docker compose up` 对所有人 fail(包括完全没启 postgres profile 的 SQLite-only 部署)。

**根因**: Docker Compose 的变量替换发生在 **parse 阶段**,profile 过滤发生在 **execution 阶段**。`:?err` 在 parse 时触发 fail,根本走不到 profile 判断。

**防线**: 对可选 profile 服务里 "真的需要" 的 env,用 `${VAR:-}` 空默认 + 容器启动时 fail(比如 postgres 没密码会自己退出),把 fail 点正确转移到运行时。**永远不要** 在可选 profile 的服务里用 `:?` 语法。

**沉淀**: ✅ 已转 `.agents/rules/ci-workflows.md`("Docker Compose" 段落)。

---

## L-005 | Round 1 | ASCII hyphen,不是 em-dash

**现象**: 部分 CI workflow 在 YAML label / comment 里用 em-dash `—` 会让读者 UI 或终端显示糟糕;在 PR check name 里用会让过滤器失配。

**根因**: GitHub UI 渲染 em-dash 正常,但在 `gh pr checks` 的 tab-separated 输出、某些通知 bot、日志转发管道里不稳定。Windows 终端某些字体会显示 `?`。

**防线**: YAML / 工作流文件 / CI step name / comment **只用 ASCII hyphen `-`**。文档正文(README / markdown)可以 em-dash,读者用的是 markdown 渲染器不会有问题。

**沉淀**: ✅ 已转 `.agents/rules/ci-workflows.md`("ASCII hyphen" 段落)。

---

## L-004 | Round 1 | `continue-on-error` 放 step 级,不是 job 级

**现象**: PR #1 设了 `jobs.security.continue-on-error: true` 以为 "pip-audit 失败不阻塞"。结果 job 还是报 fail,PR checks UI 满屏红,强迫症受不了。

**根因**: job 级 `continue-on-error` 只影响 workflow 的整体 status(不让它因为这个 job 失败而 fail),**不影响 job 自己的报告 status**。Step 级 `continue-on-error: true` 则让 step 失败后 step 视为成功,job 整体也报 success。

**防线**: 要让一个检查"可见但非阻塞",把 `continue-on-error: true` 放到 **执行真实命令的那个 step 上**,不是 job 顶层。

**沉淀**: ✅ 已转 `.agents/rules/ci-workflows.md`("continue-on-error 放 step 级" 段落)。

---

## L-003 | Round 1 | `pytest`(console script)不把 CWD 放 sys.path

**现象**: PR #4 第一轮 CI 跑 `tests/test_cache_redis.py::test_package_import_never_touches_network`,`import app.cache` 抛 `ModuleNotFoundError: No module named 'app'`。而 **同一 run 里** `test_smoke.py::test_app_package_imports` 过了,做的事情几乎一样。

**根因**: 直接调用 `pytest`(不是 `python -m pytest`)时,Python 解释器用 pytest 的 console script 入口,**CWD 不自动加入 sys.path**。pytest 自己只加测试文件的 parent(`tests/`),不加 repo root。所以 `app` 找不到。

`test_smoke` 过了是**副作用巧合**:`test_migrations.py`(字母序在 smoke 前)里 `pytest_alembic` 的 fixture 初始化 alembic,**alembic 的 Config 以副作用形式** 把 repo root 加进 sys.path。字母序在 alembic init 之前的测试文件就中招。

**防线**: `pyproject.toml` 的 `[tool.pytest.ini_options]` 必设 `pythonpath = ["."]`,让 pytest 启动前就把 repo root 放进 sys.path,与测试顺序无关。

**沉淀**: ✅ 已转 `.agents/rules/python.md`("测试基础设施(pytest)" 段落)。

---

## L-002 | Round 1 | `importlib.reload` 让 class 对象身份失配,`pytest.raises` 漏抓

**现象**: PR #7 第一轮 CI 里 `test_enabled_without_redis_raises_misconfigured` 明明 `importlib.reload(rl)` 抛了 `RateLimitMisconfigured`,`pytest.raises(rl.RateLimitMisconfigured)` 却没捕获,异常泄漏到测试结果。

**根因**: `importlib.reload` 重新执行模块,`class RateLimitMisconfigured(RuntimeError)` 语句产生**新的 class 对象**。测试 body 里 `rl.RateLimitMisconfigured` 捕获的是 reload 之前的**旧** class 引用。reload 期间抛的异常是**新** class 的 instance。`isinstance(exc, OldClass)` 返回 False,`pytest.raises` 不命中。

**防线**: 测"特定条件下模块级代码 raise"时,**不要用 `importlib.reload`**。改用 `monkeypatch.setattr(module, "CONST", value)` + 调用模块内的 build 函数(比如 `_build_limiter()`)。class 身份保持稳定,`pytest.raises` 正常工作。

**沉淀**: ✅ 已转 `.agents/rules/python.md`("测试基础设施(pytest)" 段落最后一条)。

---

## L-001 | Round 1 | 别在 `app/` 运行 `ruff check .` —— 会扫 upstream,churn 战争

**现象**: PR #1 第一轮 CI 里 `ruff check .` 在 upstream `app/` 刷出 218 个错误,瞬间不可合。

**根因**: `ruff check .` 默认扫当前目录递归。我们不想给 upstream 代码 impose 自己的 lint 标准(每次 upstream sync 合并冲突会爆炸)。

**防线**: CI 里 `ruff check` / `ruff format --check` **只扫自研目录**:`hardening/`、`deploy/`、`ops/`、`tests/`。upstream 同步区(`app/`、`dashboard/`)走上游自己的风格。makefile 的 `format-backend` target 也按此原则限定。

**沉淀**: ✅ 已在 `.github/workflows/api-ci.yml` 里固化 + 代码注释。记一条到 `.agents/rules/python.md` 里作为硬规则。

---

## 模板(新教训追加到顶部)

```
## L-NNN | Round N | <一句话现象>

**现象**: <CI / 运行 / 工具输出的具体表现>

**根因**: <为什么会这样>

**防线**: <今后怎么一次性避免>

**沉淀**: <是否已进 rule 文件;未进则标"未转 rule"并说明计划>

---
```

## 转 rule 的节奏

每轮结束时,集中看一次 LESSONS.md:

- 同一类教训出现过 ≥2 次 → 必须转 rule
- 影响 > 5 分钟调试时间的 → 必须转 rule
- 跨团队(未来接手的贡献者会踩) → 必须转 rule

单纯"下次小心"级别的(比如某次手滑)不进 rule,留在 LESSONS 作历史记录。
