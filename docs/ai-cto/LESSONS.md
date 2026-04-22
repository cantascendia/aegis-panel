# 会话级教训(LESSONS)

> 记录每轮次里**以小代价换来的 CI / 工具 / 流程教训**,防止同一个坑走两次。
>
> 格式:编号 + 发现轮次 + 现象 + 根因 + 落地防线(rule / config / habit)
>
> 凡沉淀成硬规则(`.agents/rules/*.md`)的,标注 ✓ 并指向文件。未沉淀的先在这里留痕,下轮开始前批量转 rule。

---

## L-013 | Round 2 UI 集成 | Chromatic job 无 token 必 fail —— 不是代码问题,是 infra 债

**现象**: PR #18 触碰 `dashboard/` 任何文件 → `Visual tests / Chromatic` job 运行 → `Error: ✖ Missing project token` 导致 fail。核心三门禁(Lint/Test/pip-audit)全绿,`mergeStateStatus=UNSTABLE` 但非 required → GH 仍允许 merge。

**根因**: repo secrets 里没配 `CHROMATIC_PROJECT_TOKEN`,但 `.github/workflows/chromatic.yml` 没做"token 缺失时跳过"的保护,每次都跑 + 每次都红。历史上 dashboard PR 不多,这个红一直被忽略。

**防线**:
1. 合 PR 前看清 **mergeStateStatus=UNSTABLE** 的原因是"非 required failing check"还是"required failing check"。前者允许 merge,后者不允许
2. dashboard 有变更的 PR 正常推进,Chromatic 红可忽略(不要因为它就 revert 或 hotfix)
3. **清 infra 债时** 修:要么去 chromatic.com 注册项目 + 把 token 加 repo secret,要么改 workflow `if: secrets.CHROMATIC_PROJECT_TOKEN != ''` 条件跳过

**沉淀**: 未转 rule(infra 配置债,解决了就没后续)。记入 STATUS.md "Round 2 后半" B 项的 CI 清债清单。

---

## L-012 | Round 2 UI 集成 | `tools/check_translations.sh` 严格 parity + pre-existing drift = 新 PR 踩坑

**现象**: PR #18 第一版向 8 个 locale JSON 加了 `page.nodes.sni-suggest.*` 子树。CI 的 `run-script (dashboard/public/locales/*.json)` matrix 8 个 job 全 fail —— 但报的错几乎全是 **pre-existing drift**(例如 en.json 缺 `Mode` / `Noise` / `page.hosts.padding` / `remark` / `sni` / `split_http` / `wireguard`,zh-cn 缺几十条,kur 缺 400+ 条)。我的 28 新 key 只是触发了严格检查,真正该修的是 main 上长期未维护的 parity debt。

**根因**: `tools/check_translations.sh` 对每个被 PR 修改的 locale 文件执行双向 strict 检查(源码 `t()` keys ↔ locale JSON paths)。Path-filter 让 "未被 PR 修改的 locale" 不跑这个检查,所以历史累积的 drift 一直隐藏。第一次动 locale 的 PR 就整个暴露。这是 **渐进式腐烂的 CI**:只在 "有人终于动这块" 时爆炸,平时无声。

**防线**:
1. **feature PR 不要碰 locale 文件**。新 `t()` 调用全部配 `defaultValue` 第二参数,走 i18next native fallback 路径(`t("key", "English default", { interpolationOpts })`)。零 locale 改动 → path-filter matrix 空 → run-script 不跑 → CI 清洁
2. 真正的 locale 翻译应该单独开一个 **"locale parity cleanup" PR**:先跑 `check_translations.sh` 一次,拿到各 locale 的 drift 清单,批量修齐,然后才能再做增量添加
3. 作为中期债:考虑软化 CI gate —— 例如从 "drift > 0 就 fail" 改成 "drift 增加就 fail" —— 这样增量 PR 不被历史拖累。不是本 PR 的事

**沉淀**: 半转 rule。`GEMINI.md` 的 "通用代码质量" 段落应该加一条 "新增 i18n 字符串时配 defaultValue,不要仅靠 locale 文件";下轮批量转 rule 时做。

---

## L-011 | Round 2 中段 | 本地 ruff 与 `requirements-dev.txt` pinned 版本必须一致

**现象**: PR #16 第一次 CI 挂掉在 `ruff format --check`,说 `tests/test_sni_endpoint.py` 需要 reformat。本地先用的是系统装的 ruff 0.15.6,而项目 `requirements-dev.txt` 固定 `ruff==0.7.3`。两者的 formatter 输出不一致(长函数参数的括号换行策略变了),我基于 0.15.6 看到的 "already formatted" 在 0.7.3 下立刻失效。

**根因**: Ruff 这种快迭代的工具在小版本之间 formatter 输出会变。CI 使用 pinned 版本,本地没有对齐。

**防线**: 编辑 `hardening/ deploy/ ops/ tests/` 任何 `.py` 前,跑一次 `pip install 'ruff==0.7.3' && python -m ruff --version` 确认。或者用项目的 `requirements-dev.txt` 装 venv,别用系统/全局 Python 的 ruff。

**沉淀**: 未转 rule(单次出现),如果 Round 3 再跌一次 → 转 `.agents/rules/python.md` "格式化与 lint" 段。暂存为 LESSONS,加到 `DEVELOPMENT.md` "代码风格" 段一句话提醒。

---

## L-010 | Round 2 中段 | slowapi `@limiter.limit` on `async def` 破坏 FastAPI signature introspection

**现象**: PR #16 一路 8/10 测试返回 422,body + `Annotated[..., Depends(sudo_admin)]` 均被 FastAPI 误判为 query 参数(`{"loc": ["query", "body"], "msg": "Field required"}`)。只有 `request: Request` 被识别。加 `Annotated[..., Body()]` 显式标注**没有修好**。

**根因**: slowapi 的 `@limiter.limit(...)` 装饰器对 `async def` 路由函数的签名保留(`__wrapped__` / `inspect.signature(follow_wrapped=True)`)在当前版本 + fastapi 0.121 的组合下不完整。FastAPI 看到的 annotations 只剩 `(request,)`,其余参数按 query 查不到 → 422。同项目里 `/api/admins/token`(`def`, 同步)用相同装饰器是 OK 的,所以只有 async 路由命中这个坑。

**防线**:
1. 新增 `async def` FastAPI 路由时,**不要**直接用 `@limiter.limit()` 装饰。验证一下或走变通
2. 变通方案(未实施,follow-up 确认):尝试 `limiter.shared_limit` 或在函数体内手工调用 rate-limit 检查 API
3. 至少保留这些防线:auth 门 + `asyncio.wait_for()` 全局 timeout + `Semaphore(N)` 外调并发封顶 —— 这三条即使无 rate limit 也能顶住单次滥用
4. 真正的 rate limit 必须等 slowapi+async 行为确认后再加

**沉淀**: 🟡 半沉淀。`.agents/rules/python.md` "Marzneshin 特定" 段应加一条 "新增 async 路由不要直接套 slowapi 装饰器,先看 LESSONS.md L-010"。下轮开始前补上。

---

## L-009 | Round 2 开场 | "`foo` deprecated in favour of `foo_utc`" 改名不可全局套用 —— 读 vs 写可能是两个对象

**现象**: PR #11 第一次 commit 把 `CertificateBuilder.not_valid_before()` / `.not_valid_after()` 改成 `*_utc` 版本,CI 30 秒抓到 `AttributeError: 'CertificateBuilder' object has no attribute 'not_valid_before_utc'`。

**根因**: cryptography 42 changelog 写着 "`not_valid_before` deprecated in favour of `not_valid_before_utc`" —— 我看到一行就批量改。真相是这个 deprecation **只针对 `Certificate` 对象的只读 property**(给出一个现成的证书,读它的生效时间),不针对 `CertificateBuilder` 的 **setter 方法**(构建证书时设置生效时间)。两个不同对象共享同一个属性名,官方从没给 builder 加 `_utc` 的 setter。

**防线**:
1. 遇到 "API X deprecated in favour of X_new" 之前,先问:**X 属于哪个类/对象?是 read-side(property / attribute)还是 write-side(setter / builder method)?**
2. 正式改之前,去**该类的官方文档页**(不是 changelog)确认新 API 确实存在于那个类上
3. 改动带单测覆盖(本项目的 `app/utils/crypto.py` 没单测,只有 migration 测试偶然 exercise —— 这也是为什么错误 surface 在 migration 测试里而不是直接测试;值得后补一条 `test_generate_certificate` 测试)

**沉淀**: 不转硬规则(不是 CI/工具坑,是"读 API 文档要细"级别的 judgment)。LESSONS 作为 historical 留痕。未来若再栽同样坑 → 就说明要升为规则。

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
