# 会话级教训(LESSONS)

> 记录每轮次里**以小代价换来的 CI / 工具 / 流程教训**,防止同一个坑走两次。
>
> 格式:编号 + 发现轮次 + 现象 + 根因 + 落地防线(rule / config / habit)
>
> 凡沉淀成硬规则(`.agents/rules/*.md`)的,标注 ✓ 并指向文件。未沉淀的先在这里留痕,下轮开始前批量转 rule。

---

## L-027 | Round 3 mid late-7 wave-3 | Sub-agent 临时 worktree 并行模式经 7 波验证稳定,可转硬规则

**现象**: 本会话(2026-04-28 ~ 04-29)单 session 内通过 16 次 sub-agent 调度,分 7 波并行(每波 2-5 个 sub-agent),完成 9 PR merge + 3 issue + harness 健康分 78→94。其中 4 波(#3 / #4 / #6 / #8)用临时 worktree(`../aegis-tmp-{slug}`)隔离 git-heavy 操作,主 worktree 0 撞车,sub-agent 之间 0 交叉污染。

**根因**: SESSIONS.md 铁规则 #7 worktree 隔离原本为多 Claude session 设计,但**单 session 内的 sub-agent 也适用**。把 git commit/push/branch-switch 隔离到独立 worktree,主 session 0 的 working tree 不被任何 sub-agent 污染,sub-agent 之间也不撞车(各自的 working tree)。

经 7 波验证(20+ 个临时 worktree create/cleanup):
- 0 次 branch switch race
- 0 次 stash 污染
- 0 次 PR commit 挂错分支
- L-018 全套事故零复发

**防线**(从 L-026 候选升级为硬规则):

1. 主会话需要并行多 sub-agent 跑 git-heavy 工作时,**先**:
   `git worktree add ../aegis-tmp-<task> -b <branch>`
2. Sub-agent prompt 必须**硬编码 cd 到该 worktree**,严禁回主 repo
3. Sub-agent 完成后,主会话:
   - merge PR(主 repo 操作)
   - `git worktree remove ../aegis-tmp-<task>`
   - `git branch -D <branch>` (远端已 --delete-branch)
4. 临时 worktree 命名 `aegis-tmp-<slug>`,与 fixed session worktree `aegis-{B,D,F,O,R,X}` 区分(避免误删 fixed session)
5. 单波并行 sub-agent ≤ 5 个(超过 5 个 token 消耗暴涨,且 main session context 难以同时 review 所有报告)

**沉淀**: ✅ 升级为硬规则,加到 `.agents/rules/git-conventions.md` 或新建 `.agents/rules/sub-agent-worktree.md`(下次 .agents/rules 改动 PR 时落)。SESSIONS.md 铁规则 #7 段已补一段:"sub-agent 内部并行 git-heavy 工作沿用 worktree 隔离原则,临时 worktree 命名带 `aegis-tmp-` 前缀"(本 batch 已落)。

---

## L-026 | Round 3 mid late-7 wave post-merge | Sub-agent 并行 + 临时 worktree 让 1 session 触发 6 PR + 3 issue 自动收口

**现象**: late-7 wave-2 post-merge batch (本 PR) 中,session 0 在单个会话内通过 5 个 sub-agent 串/并行(2 review + 2 SPEC + 1 调研)+ 后续临时 worktree 隔离的 docs sub-agent + 3 个 gh-only sub-agent,完成: PR #99/#100/#101 (3 个) merge + issue #102/#103/#104 (3 个) 创建 + 后续 batch refresh PR + handbook 路径修复 PR,**用户介入 ≤ 3 次**。

**根因**: SESSIONS.md 铁规则 #7 worktree 隔离原本是为多 Claude session 设计,但**单 session 内的 sub-agent 也适用** — 把 destructive git 操作(commit/push/branch switch)隔离到独立 worktree,主 session 0 的 working tree 永不被污染,sub-agent 之间不撞车。

**防线**: 任何需要并行多 sub-agent 跑 git-heavy 工作时,主会话先 `git worktree add` 临时 worktree(`../aegis-tmp-<task>`),sub-agent prompt 里硬编码 cd 到该 worktree 不去主 repo;完成后主会话清理(`git worktree remove`)。临时 worktree 配独立 branch 名,不复用 fixed session 的 aegis-{B,D,F,O,R,X}。

**沉淀**: 未转 rule(单次 pattern,模式还要再观察 1-2 次)。下一次 multi-sub-agent batch 沿用此模式,如果稳定再转硬规则。

---

## L-025 | Round 3 mid late-7 | drive-by S-O 触发会和正式 S-O batch 抢占同一文件,要先看 git log 再动手

**现象**:2026-04-28 late-7 wave 5 PR 合入(#86-#90)后,session 0 起了一个 drive-by S-O(分支 `docs/status-refresh-late-7-wave`)只刷 STATUS.md,顺手把 wave-7 块加到底部。当天稍后启动正式 S-O batch session(本 PR),开 worktree 后 `git pull origin main` 拿到的 STATUS.md **已经包含 drive-by 的内容**。如果不先看 `git log docs/ai-cto/STATUS.md` 评估"近期已经被改过没",会直接重写一遍 + 重新加 wave-7 块,造成 commit 内容与已 merge 内容重复 / 冲突 / 丢字。本次幸运是先扫了 git log 才发现 #91 已合入。

**根因**:S-O 文档的"我是 single writer"假设只在没 drive-by 时成立。一旦 session 0 / 其他 worker 在 batch S-O 之间做单文件刷新(典型场景:wave 后立刻刷 STATUS 让团队看到最新数字),batch S-O 启动时的工作目录已不是 batch 启动设计当时的状态。如果 batch S-O 直接照"上次 batch 后的 mental model"全文重写,会覆盖 drive-by 的合理增量。

**防线**:

1. **每次 S-O session 起手三步**(顺序固定,不能跳):
   ```bash
   git log --oneline -20                             # 看近 20 条提交
   git log --oneline docs/ai-cto/STATUS.md | head -10  # 专看 STATUS 改动
   gh pr list --state all --limit 15 --json number,title,mergedAt  # 看近 15 PR
   ```
   如果 STATUS.md 在最近 24h 被改过,**默认是 incremental refresh** 而不是 full rewrite,否则会撞 drive-by 的成果。
2. **drive-by S-O 自身的契约**(防引爆下游 batch):drive-by 必须在 commit message / STATUS metadata 里**明确标记**"留给下次 batch S-O 整合"(本次 #91 已有这条),且**只动 STATUS.md 一个文件**,不顺手碰 LESSONS / DECISIONS / ROADMAP / SESSIONS(那会让 batch 难以判断哪些已经更新)。
3. **batch S-O 接手时的 incremental 处理动作**:把 drive-by 块作为"已合入数据"读进来,不做 full rewrite;只在 batch S-O 该做的事(L/D 新条目、ROADMAP 升级、SESSIONS 状态切换、STATUS 结构压缩)上做增量。drive-by 的 wave 块会被压缩进"历史 wave 索引"表,自然消化。
4. **跨 session 共识**:STATUS.md 的最后更新时间戳 + "本批次"段是 fingerprint,batch S-O 见到不属于自己的 fingerprint 时就**知道有 drive-by**。

**沉淀**:本 entry。drive-by S-O 与 batch S-O 的交接路径明确化;`SESSIONS.md` 铁规则不变(S-O 仍是 part-time),只是触发时机要分类。未来如果 drive-by S-O 被滥用(频次 > 1 / 周或动多文件),升级为 `.agents/rules/*.md` 硬规则强制 "drive-by S-O 只能改 STATUS.md 一个文件"。

---

## L-024 | Round 3 mid late-6 | 链上支付 = 拉模型,不是没装好的推模型 — TRC20 必须 poll 而不是想着搞 webhook

**现象**:实现 A.3 TRC20 时第一直觉是 "EPay 都有 webhook,TRC20 应该也搞个 webhook 路径,统一接口"。停下来想了 30 秒后明确:**Tron 协议本身不会向任何 endpoint 推送**。Tronscan / Trongrid / 自建节点都是 "我读"。所谓的"TRC20 webhook" 只能是:第三方 indexer 读链 → 推到我们这。等于在我们和链之间加了一个新 trust boundary。

**根因**:支付通道有两种 trust 模型:
- **推模型**(EPay / Stripe / NOWPayments / 微信支付):中介向我们推回调。我们必须验签防伪,但中介会主动告诉我们"用户付了"。
- **拉模型**(任何区块链直收):没有中介,我们必须主动观察链。延迟 = 我们的 poll interval;trust boundary = "这个 RPC 节点说的是真的链状态"。

把这两类强行套进同一个抽象(都搞 webhook)= 给自己增加一个不必要的 trust boundary,而且要为 indexer 的 stability / 跑路 / 数据延迟单独写预案。**直接 poll 反而更简单**:30s 一次 HTTP GET,任何 indexer 给同样的数据就行,出问题切个 base URL 即可(`BILLING_TRC20_TRONSCAN_API_BASE` 改下值)。

**防线**(下次接新支付通道时的判断流程):
1. **该协议本身有没有原生 push 机制?** 区块链 = 几乎全部没有(以太坊有 eth_subscribe websocket,但要求自建 archive 节点,不实用);第三方网关 = 几乎全部有
2. **如果没原生 push,中介推 ≠ 协议推**。中介推就是另一种"我们读" + 中介内部缓存,把 trust boundary 移到中介的可靠性上。能直接读链就直接读
3. **延迟可接受?** Poll interval 决定 SLA。30s 对支付场景够用(用户从付款到看到 "已确认" 等 30s 不是问题);< 5s 才需要考虑 websocket / 长轮询
4. **API 切换成本?** 直接 poll 公共 indexer 切换成本低(改 base URL);依赖某中介推送,切换是大手术

**沉淀**: ✅ 本 entry。`ops/billing/providers/trc20.py` 模块 docstring "Why polling over webhook" 段记录设计决策上下文;`Trc20Provider.handle_webhook` 主动 raise `UnhandledEventType` 防止有人后来又想加 webhook 路由。

---

## L-023 | Round 3 mid late-6 | `asyncio.run()` 在 FastAPI 已运行 loop 内会炸,用 `asyncio.to_thread` 包装现有 sync 实现

**现象**:Reality R.3 endpoint 测试 `test_audit_source_config_perfect_returns_green` 失败,日志显示 `RuntimeError: asyncio.run() cannot be called from a running event loop`,同时 pytest 警告 `coroutine '_fake' was never awaited`。错误来自 `hardening/reality/checks/asn_match.py` 内的 `info = asyncio.run(lookup_asn(sni_ip))` —— 这个 helper 是 sync 的,从 CLI / 普通脚本调用没问题,但 FastAPI endpoint 里上层已经在跑 event loop。

**根因**:`asyncio.run` 文档明确写 "cannot be called when another asyncio event loop is running in the same thread"。CLI 和 endpoint 都需要这套 ASN match 逻辑,但 CLI 是 sync 入口(无 loop)、endpoint 是 async 入口(有 loop)。两个调用点对 sync/async 的期望不同。

**防线**:**`asyncio.to_thread(sync_func, *args)` 把 sync helper 推到线程池,该线程没有 loop,`asyncio.run` 在那里能跑**。一行代码包装解决问题,不必把 `check_asn_match` 改写成 async 二态版本(那会引入两份代码或 sync_to_async/async_to_sync 适配复杂度)。

**模板**:

```python
# 在 async 端(FastAPI endpoint / 异步任务):
return await asyncio.to_thread(sync_helper_using_asyncio_run, arg1, arg2)

# 在 sync 端(CLI / pytest sync test):
return sync_helper_using_asyncio_run(arg1, arg2)  # 直接调用
```

**适用边界**:这是"同一逻辑两个调用环境"的快速胶水。**长期最佳设计** 是把底层逻辑做成 `async def`,sync 入口用 `asyncio.run` 收尾;但当底层已经 ship、改动面太大时,`to_thread` 是合理的妥协。本 PR 的 ASN match 满足 "已 ship + 多处 import" → 选 to_thread。

**沉淀**: ✅ 本 entry。`hardening/reality/endpoint.py:_maybe_asn_check_async` 是模板代码。下次遇到 sync helper 在 async endpoint 里炸,先看是不是同一情况,直接 `asyncio.to_thread` 包装。

---

## L-022 | Round 3 mid late-5 | 何时打破"session 0 不改 upstream 文件"的 Round 1 默认规则

**现象**: PR #70 是 session 0 第一次**主动**修改 upstream `app/*` 11 个文件(26 callsite 替换 + 1 新建 `app/utils/_aegis_clocks.py`)。Round 1 默认是 "self-owned 优先,upstream 慎动"(D-009 的 lint 范围决策也是这哲学)。本 PR 显式打破默认,要在记忆里写清楚什么情况可以打破。

**根因**: Round 1 默认规则不是教条,是 cost-benefit 估算的速记。改 upstream 的 cost = 每次 `git fetch marzneshin-upstream` 的 merge 冲突可能性;benefit 视场景。当 benefit 显著大于 cost 时,默认规则应让位。

**防线**(打破规则的硬条件,**三条同时满足**):

1. **改动是 must-fix**,不是 stylistic / 偏好性 / 优化性。例如:Python 3.12+ 强制 deprecation(`datetime.utcnow` / `datetime.utcfromtimestamp`)、CVE 修补、运行时 hard-error 路径。**反例**:rename 变量风格、code style 偏好、early return 优化 —— 这些不是 must-fix,upstream 还会自己用别的做法,改了纯增加 conflict
2. **行为字节级保持**:改完前后语义无差。例如 `datetime.utcnow() ↔ datetime.now(UTC).replace(tzinfo=None)` 输出完全相同。**反例**:column type 变更、API contract 变更、错误处理路径变更 —— 即使你认为更好,upstream 不一定接受
3. **上游早晚必须做**:这条最关键。Python 3.12 deprecation,upstream Marzneshin 早晚要清,我们先做了等于把作业写在前面;upstream 真做时找到我们已修(diff identical or close),merge 自然解。**反例**:我们的偏好(比如把 SQLAlchemy 1.x 写法升 2.0),upstream 可能不动这层,就一直冲突

满足上述三条 = 改;**缺一条 = 不改**(继续走 self-owned 路径或开 upstream issue / PR 等)。

**触面控制原则**:即使三条满足,也尽量**bounded**:

- 11 文件 / ≤ 100 行 = 可接受
- 把 fork-local helpers 集中到一个文件(本 PR 的 `app/utils/_aegis_clocks.py`),且文件名带 `_aegis_` 前缀和 `_` 私有标记,upstream-merge 时一眼能识别 "fork-only"
- 改动到的每个文件**只换 deprecated 调用**,**不顺手做其他清理**。"扫一片" 的诱惑要忍住,否则违反第 2 条(行为保持)

**沉淀**: ✅ 本 entry + STATUS late-5 块。未来类似边界判断:回到这条核对三个条件再动。

---

## L-021 | Round 3 mid late-4 跨 session review | reviewer 推 commit 到他 session 的 PR 前必须同时跑 `ruff check` + `ruff format --check` 全自有目录

**现象**: PR #65 是 S-B 开的,CI 在合入前一直绿。session 0 reviewer (本会话) 推 `de23f5f` 加安全修复后 CI 突然挂 `Lint (ruff)` —— 但失败的不是我新写的文件,是 PR #65 早就在的 `hardening/panel/middleware.py`(I001:`from ops.billing.checkout_endpoint import checkout_router as billing_checkout_router` 一行 85 字符超 79 限)。后又一轮挂在 `ops/billing/endpoint.py`(format ternary)。两轮 CI 失败都是 PR #65 原代码的潜伏问题。

**根因**: CI 的 `ruff check hardening deploy ops tests` + `ruff format --check ...` 跑全自有目录,不只跑 diff 文件。如果 PR 原作者只跑了 `ruff check` 没跑 `ruff format --check`(或反之),issue 留在 PR 直到下一个 reviewer push 触发完整 CI 才暴露。"前几轮 CI 绿"是因为之前没人 push 过新 commit ——但不代表代码干净,只代表 CI **流水线刚好被原作者最后一次 push 之前的状态过了一次**。push 重启 CI,latent 问题就 surface。

**防线**:
1. **跨 session 推 commit 前的 pre-push checklist(本地一次性跑全自有目录,不只看自己文件)**:
   ```bash
   ruff check hardening deploy ops tests
   ruff format --check hardening deploy ops tests
   pytest tests/  # 至少跑改动模块的子集
   ```
   两条 ruff 命令必须**同时**跑,不要只跑 check —— format 漂移单独失败的次数比 check 多
2. PR-author 自己提交时同样应该这样做,但 reviewer 不能假设 author 跑过
3. 当 reviewer push 触发 latent failure,**默认修复后再 push**(像本会话做的),不要把 "先 push 看 CI 怎么说" 当工作流 —— 浪费 CI minutes 和 review attention

**沉淀**: ✅ 已加到 `.agents/rules/ci-workflows.md` 的 "本地 pre-push 流水线" 段(本 PR);未来跨 session push 自动激活。

---

## L-020 | Round 3 mid late-4 cross-session review | FastAPI `TestClient` 默认 peer 是 `"testclient"` 字符串而非 IP

**现象**: 给 PR #65 加 IP-allowlist + trusted-proxy 测试时,`request.client.host` 在 TestClient 下返回 `"testclient"`,**不是 `127.0.0.1`**。我设的 `BILLING_TRUSTED_PROXIES="127.0.0.1/32,::1/128"` 因此匹配不到 → trusted-proxy 路径走不到 → X-Forwarded-For 测试全 403,白调一个小时。

**根因**: FastAPI/Starlette 的 TestClient 是 ASGI in-process 调用,没有真实 TCP 连接,**Starlette 把 `scope["client"]` 写成 `("testclient", 50000)`**(literal hostname,不是 IP)。许多 IP-aware 中间件在这种环境下行为不同,但通常不被注意到(rate limit / CORS 都不解析 client.host 为 IP)。

**防线**:
- **TestClient 测试涉及 IP 解析时**,初始化时显式传 `client=("127.0.0.1", 51234)`:
   ```python
   from fastapi.testclient import TestClient
   client = TestClient(app, client=("127.0.0.1", 51234))
   ```
- 反过来,生产代码里 `_resolve_client_ip` 接收 `request.client.host` 必须用 `try: ipaddress.ip_address(...) except ValueError: ...` 围一圈,否则 `"testclient"` 之类异常输入会抛
- 任何 "XFF + peer 信任" 类 logic 的测试用例必须**双向**:peer trusted XFF honored / peer untrusted XFF ignored,后者已是 PR #65 `test_webhook_ip_allowlist_ignores_spoofed_xff_when_peer_untrusted` 的模板

**沉淀**: 不转硬规则(单次坑,judgment 类)。LESSONS 留痕。如未来又因 TestClient peer 默认值踩坑,升级到 `.agents/rules/python.md` 测试基础设施段。

---

## L-019 | Round 3 mid late-4 cross-session review | X-Forwarded-For 信任要 per-feature CIDR env,不能"总是信任"或"总是忽略"

**现象**: PR #65(EPay webhook)第一轮代码 `_resolve_client_ip` 见 `X-Forwarded-For` 就直接用,把它定位为 IP 白名单的 "double 防线"。但端点是 HTTP-unauthenticated,任何能直连 panel 的人都能 spoof XFF 绕过 `allowed_ips` —— 文档 + OPS-guide 把 IP 白名单宣传为 "double 防线" 但实际只在 panel 处于受信反代后才成立。direct-on-internet 部署下变成 **security theatre**(误导性安全)。

**根因**: 反代 vs 直连是 **per-deploy** 决策,不是 panel-wide。同一个 panel 进程可能:
- billing webhook 走 Nginx-on-same-host(只信 `127.0.0.1`)
- iplimit allowlist 边缘用例走 CF Tunnel(只信 CF egress 段)
- admin login rate-limit 走双层(CF 在前 + Nginx 在后,信两段)

写一个 panel-wide `TrustedProxyMiddleware` 注入 `request.scope["client"]` 看似"中央化",但**强行让每个 feature 共享同一信任假设**,反而比 per-feature env 更脆弱 —— 一旦 Nginx 配置漂移,全站 IP-aware 行为静默错误。

**防线**:
- **每个 IP-aware feature 各自挂一个 `<FEATURE>_TRUSTED_PROXIES` env**(CIDR 列表 string),feature 内部解析、feature 内部使用。本 PR 的 `BILLING_TRUSTED_PROXIES` 是模板:
   ```python
   def _peer_is_trusted_proxy(peer_ip: str) -> bool:
       if not peer_ip: return False
       if not config.BILLING_TRUSTED_PROXIES: return False
       try: peer = ipaddress.ip_address(peer_ip)
       except ValueError: return False
       return any(peer in cidr for cidr in config.BILLING_TRUSTED_PROXIES)
   ```
- **空默认 = 不信任**(直接公网部署的安全选)
- **未来 4+ feature 用同样配置时**,再考虑提到 panel-wide(`app/middleware/trusted_proxy.py`),不提早抽象

**沉淀**: ✅ 决策已落 D-012(本 PR);代码模板在 `ops/billing/config.py:BILLING_TRUSTED_PROXIES` + `ops/billing/checkout_endpoint.py:_peer_is_trusted_proxy`,下个 IP-aware feature 直接 copy。

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
