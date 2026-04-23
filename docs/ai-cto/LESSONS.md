# 会话级教训(LESSONS)

> 记录每轮次里**以小代价换来的 CI / 工具 / 流程教训**,防止同一个坑走两次。
>
> 格式:编号 + 发现轮次 + 现象 + 根因 + 落地防线(rule / config / habit)
>
> 凡沉淀成硬规则(`.agents/rules/*.md`)的,标注 ✓ 并指向文件。未沉淀的先在这里留痕,下轮开始前批量转 rule。

---

## L-018 | Round 3 多会话并行 | 同一工作目录并发跑多个 Claude session → branch / stash / PR 全面撞车

**现象**: 2026-04-23 日下午,为了平行推进 S-D(部署)+ S-R(Reality 审计)+ S-F(本会话,前端测试)三线,用户在同一个 `C:/projects/Marzban` 工作目录里并发开了 3 个 Claude Code session。连续发生:

1. S-F 在 `test/billing-user-money-critical` 分支写完 cart-summary / plan-card 测试 + commit,准备 push。再跑 `git status` 发现**已经不在原分支了** —— 被切到 `feat/spec-deploy`(S-D session 的分支),而且我的 commit 还在,但分支名对不上
2. S-F 的 `git push origin test/billing-user-money-critical` 推上去的内容**包含了 S-D 的 commit**(6377c4e 文档)—— 一个 PR 混了两个 session 的无关工作
3. 恢复分支时,发现 S-D 还有更新版 `6604d0f` 在另一个本地分支 `feat/spec-deploy-clean`,内容互不兼容
4. 再跑 `git status` 发现自己在 `docs/spec-reality-audit`(S-R session 的分支),且有一个**别人的** `DECISIONS.md` 未提交改动
5. 开 PR 时,`gh pr create` 因为"当前分支有未提交改动"失败,不得不用 `--head <branch>` 显式指定

最终结果:S-F 花了 ~20 分钟 git surgery 把三条线切开,期间一度有多个 remote 分支指向同一 SHA 但命名混乱(feat/spec-deploy / feat/spec-deploy-clean / test/billing-user-money-critical)。

**根因**: Claude Code session 对 `git` 状态没有 isolation —— 切分支、stash、commit 都直接作用于 working tree。多个 session 共享同一 `.git` 和 working tree 时:

- session A `git checkout feat-A` → session B `git checkout feat-B` → session A 的下一个 `git commit` 落到 B 分支
- session A `git stash` → session B 的未提交修改被 stash 进 A 的 stash list → session A `git stash pop` 把 B 的东西 apply 到 A 的 working tree
- session A 正在 merge PR → session B 的 `git pull` fast-forward 到 A 的 merge commit,但 B 的当前分支可能因此偏离预期

Git 的设计前提是"一个 working tree = 一个 actor",不是并发安全的。

**防线**(已固化到 `docs/ai-cto/SESSIONS.md` 铁规则 #7):

1. **硬规则**:每个并发 Claude session 必须有独立 **git worktree** 或独立 **repo 克隆**。主 repo 目录只留给 session 0(审阅 + merge 裁判)。
2. 推荐的 worktree 布局:
   ```bash
   cd C:/projects/Marzban          # session 0,裁判
   git worktree add ../aegis-B feat/billing-backend
   git worktree add ../aegis-D docs/spec-deploy
   git worktree add ../aegis-R docs/spec-reality
   # 每个 session 起手:cd ../aegis-X
   ```
3. **Session kickoff prompt 必须明确工作目录**。SPEC-deploy.md / SPEC-reality-audit.md / SPEC-dashboard-tests.md 里的 Kickoff prompt 需要加一段:
   > 你的工作目录:`C:/projects/aegis-<session-letter>`。**不要** `cd` 到别的目录;**不要** 在主 repo `C:/projects/Marzban` 操作。
4. **Preflight check**(每个 session 首条命令):`pwd && git branch --show-current && git status --porcelain` —— 如果 `git status` 显示**不属于本 session 的未提交文件**,立刻停手问用户,而不是 stash / commit。
5. **跨 session PR 开 PR**:用 `gh pr create --head <branch>` 显式指定,不要信当前分支。

**沉淀**: ✅ 已升级到 `SESSIONS.md` 铁规则 #7(本 PR)。后续 kickoff prompt 更新是下次 S-O session 的清单项。

---

## L-017 | Round 3 A.1.4.c | 注释里不能出现匹配 i18n 抽取正则的字面 —— drift-gate 会把它当 source key

**现象**: A.1.4.c(PR #35)第一次 CI 失败:`run-script (en.json)` 报 `PR increases locale drift by 1 for dashboard/public/locales/en.json`,`missing=24` 比 base 的 `missing=23` 多 1,但我的所有 `page.billing.invoices.*` key 在 locale JSON 里都存在。

**根因**: 为解决 biome 把 JSX 里的 `t("…")` 包裹到多行导致 `tools/check_translations.sh` 的行级正则抽不到 key,我把调用提到一个 `const notePlaceholder = t("…")`,并在上方写注释解释"让抽取正则能看到单行 t(\"...\") 调用"。抽取正则 `\Wt\(["']\K[\w.-]+(?=["'])` 完全不分代码 vs 注释,把注释里的 `t("...")` 抽成一个 "source key" 叫 `...`,而 locale JSON 自然没有这个 key → drift +1。

**防线**:
1. **写关于 i18n 抽取正则的注释时,别在注释里放能被正则匹配的示例**。要么改述("extraction regex sees a single-line call" / "sees the key with the quote right after paren"),要么把示例用 `// t` + 换行打断正则。
2. 抽取脚本本身可以收紧,但收紧会增加别的假阳性。当前方案成本更低、更可靠,留作习惯即可
3. 本地 drift preflight 现已能抓到这个 bug:`bash tools/check_translations.sh --base-source <base-worktree> --base-json <base>/dashboard/public/locales/en.json dashboard/public/locales/en.json` 出现 `::error::PR increases locale drift by N` 就是这类问题。在 push 前跑一次 diff-mode 可省一轮 CI 迭代

---

## L-016 | Round 3 IP limiter follow-up | Fresh-DB CI 掩盖"已合并 migration 被 mutate" —— 绿灯是 false negative

**现象**: PR #26 的 PG16 pytest job 全绿,以为 `aegis_iplimit_disabled_state` 表创建逻辑工作正常。实际上 CI 使用的是**每次 run 全新 DB**,从 revision `20faa9f18c0a` 开始跑完整 migration chain 一次性到 head,自然会执行 `4f7b7c8e9d10` 的 mutated `upgrade()` 并创建 3 张表。但**任何在 PR #24 merge 后、PR #26 merge 前跑过 `alembic upgrade head` 的环境**(本地 dev DB、staging、生产),`alembic_version.version_num` 已卡在 `4f7b7c8e9d10`,Alembic 不重跑已标记完成的 revision,**新表永远不被创建** → 运行时 `upsert_disabled_state` 抛 `relation does not exist`。CI 这种 "全流程 happy path" 根本触发不到这个分支。

**根因**: Alembic 的增量迁移语义是 "revision id 级别的 at-most-once",`alembic_version` 表只记 revision id 不记内容。fresh-DB CI 永远走 "从零一次性到 head" 的路径,**天然无法发现** "已 merge 的 revision 被修改后还能跑" 这类事故。要测出 bug 必须构造 "卡在旧 head 的 DB + 拉新代码" 的场景。

**防线**:
1. **API CI 增加一个 "upgrade-then-upgrade" job**:先用 base commit(main 的上一个提交)的代码跑 `alembic upgrade head`,再切到 PR 代码跑 `alembic upgrade head`,同时跑 metadata-vs-DDL 校验(`pytest-alembic --test=model-definitions-match-ddl`)。这能把"已 merge revision 被 mutate"的 bug 抓到 CI 上
2. **本地 smoke** 至少手工模拟一次:`git checkout main~1 && alembic upgrade head && git checkout PR-branch && alembic upgrade head`,有问题的 PR 第二次 upgrade 会 no-op,metadata 校验会抓到 DDL 缺失
3. 补救 migration 要写成 **幂等 safety net**:用 `sqlalchemy.inspect(bind).get_table_names()` 先查,已存在就 return。参见 `20260423_44c0b755e487_iplimit_disabled_state_safety_net.py` 的实现

**沉淀**: 未转硬 rule(需要实际加 CI job 才算落地)。转 `.agents/rules/ci-workflows.md` 的 action item:加一条 "Alembic migration PR 必须有 stepped-upgrade job"。Round 3 infra 清债时做。

---

## L-015 | Round 3 IP limiter follow-up | 已 merge 的 Alembic revision 不可 mutate —— 必须新建下游 revision

**现象**: PR #26 为补 C-2 review blocker 新增 `aegis_iplimit_disabled_state` 表时,直接把 `op.create_table(...)` 追加到**已随 PR #24 合并进 main 的** revision `4f7b7c8e9d10` 的 `upgrade()` body 里。Alembic 不会检测到内容变化(它只按 revision id 判 at-most-once),已跑过 `4f7b7c8e9d10` 的环境永远不会创建新表。CI 绿灯是假象(见 L-016)。

**根因**: Alembic 的 "revision 已应用即冻结" 是硬语义,不是约定。migration 文件在 merge 到 main 的瞬间就应视为 **append-only 历史记录**,任何对已应用 revision 的内容修改等同于创造一个**幽灵改动**:新环境看得到,老环境看不到,DB schema 和代码永久脱钩。这是所有 schema-migration 工具(Alembic / Flyway / Rails migrations)的通病。

**防线**:
1. **硬规则**:一旦一个 Alembic revision commit 到 main,**它的 `upgrade()` / `downgrade()` / `revision` / `down_revision` 四个字段永不修改**。文件里的 docstring / 注释可以改,schema 操作不能动
2. **Code review checklist**:看 migration PR 时必看 `git log <filename>`,只有 "新文件"(第一次出现)才允许修 `upgrade()` body。已存在的 migration 只允许改文档
3. **修复已 mutate 的 migration**:用**幂等 safety net** 作为新下游 revision,用 `inspect(bind).get_table_names()` 判存在再 `create_table`。不要回去改原文件。参见本仓 `20260423_44c0b755e487_iplimit_disabled_state_safety_net.py`
4. **命名惯例建议**:补救 migration 文件名带 `_safety_net` / `_backfill` / `_repair` 后缀,docstring 第一段说明为什么存在,链接到原事故的 PR / revision id

**沉淀**: ✅ 已沉淀到本仓的补救 migration 代码里(docstring 解释完整上下文)。转 `.agents/rules/python.md` "Marzneshin 特定" 段 **必做**:加硬条 "Alembic migration merge 后不改 schema 操作,补救走新 revision"。这是 Round 3 开始前最高优先级的 rule 沉淀,比其他条都重要(跟 DB 一致性挂钩)。

---

## L-014 | Round 3 IP limiter | `hardening/*` 自有 SQLAlchemy model 不被 Alembic metadata 感知 —— 需在 env.py 显式 import

**现象**: PR #24 `hardening/iplimit/db.py` 定义 `IPLimitPolicy` / `IPLimitOverride` / `IPLimitEvent` 三张表并有对应 Alembic revision `7b12085`,但 `app/db/migrations/env.py` 的 `target_metadata = Base.metadata` 不会自动发现它们 —— 模块没被任何 production 代码路径 import,`Base` 注册表里就没它们的 mapping。pytest-alembic 的 "model vs DDL" 校验或 `autogenerate` 会出现 false positive(DB 有表但 metadata 里没、或反过来)。

**根因**: SQLAlchemy 的 declarative `Base` 注册表是**副作用**机制 —— 只有在 Python 解释器执行过 `class Foo(Base)` 语句之后,`Base.metadata.tables` 里才有 `foo` 表。Alembic `env.py` 只 `from app.db.base import Base`,如果自研模块(`hardening/` / `ops/`)的 model 定义文件**没被任何代码路径 import**,Alembic 就看不见它们。upstream 的 `app/models/*.py` 会被业务代码主动 import 所以自动注册,自研模块放在 `app/` 之外必须手工 wire。

**严重度升级 (2026-04-23)**: cross-review(PR #24)的 sub-agent 独立判定为 🟠 Major,理由:
- `env.py` 是 upstream 同步区文件,每次 `git fetch marzneshin-upstream` rebase 都可能冲突,多加一行多一次人工 reconcile
- 模块 #3 (`ops/billing/` 已 land,`hardening/sni/` / `hardening/reality/` 在后面)会让 env.py 积累 4-5 行散装 import,隐式耦合 Alembic 启动顺序 vs hardening/ops 包导入
- `ops/billing/db.py` **已经**在 env.py 多加了一行 import(PR #28),事实证明这是重复出现的模式 → 规则必须立即沉淀

**防线**(升级版):
1. **短期(已应用)**:新增 `hardening/<module>/db.py` / `ops/<module>/db.py` 时,同步在 [env.py](app/db/migrations/env.py) 加 `import <module>  # noqa: F401`
2. **强制 review checklist**:新 Alembic revision 里有 `create_table` 时,PR 必须同时包含 env.py 的 import 增补。metadata 与 DDL 不匹配 = merge blocker
3. **中期目标(下一个 non-rush PR)**:建 aggregator `app/db/extra_models.py`:
   ```python
   # app/db/extra_models.py — Aegis self-owned model registry.
   # env.py imports only this file; add new model modules here.
   from hardening.iplimit import db as _iplimit  # noqa: F401
   from ops.billing import db as _billing  # noqa: F401
   # Future: hardening.sni, hardening.reality, ops.audit ...
   ```
   env.py 改成 `import app.db.extra_models  # noqa: F401`。单一 upstream 冲突面,self-owned 注册表在本 fork 目录
4. **长期(可选)**:自动发现 —— `pkgutil.walk_packages(hardening.__path__)` 扫所有 `*/db.py` 自动 import。更干净但增加 import 时反射开销,规模 >10 个模块后考虑

**沉淀**: 🟠 **必做**转 rule。`.agents/rules/python.md` 的 "Marzneshin 特定" 段加:"自研模块新增 SQLAlchemy model 必须注册到 `app/db/extra_models.py` aggregator;env.py 保持只 import aggregator 一个文件"。Round 3 开始前优先级仅次于 L-015。

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

**沉淀**: ✅ 已转硬规则(2026-04-23 S-O 触发)。`.agents/rules/python.md` "Marzneshin 特定" 段 → "slowapi `@limiter.limit` 禁套 async def 路由"(三条替代路径 + 三条配套防线 + 解除条件)。

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
