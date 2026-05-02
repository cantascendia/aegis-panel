# 会话级教训(LESSONS)

> 记录每轮次里**以小代价换来的 CI / 工具 / 流程教训**,防止同一个坑走两次。
>
> 格式:编号 + 发现轮次 + 现象 + 根因 + 落地防线(rule / config / habit)
>
> 凡沉淀成硬规则(`.agents/rules/*.md`)的,标注 ✓ 并指向文件。未沉淀的先在这里留痕,下轮开始前批量转 rule。

---

## L-043 | wave-9 R3 production self-test | docstring 自承 "Until X lands" 是 documentation drift 高发点

**现象**:wave-9 R3 operator 自付测试发现 `apply_manual` endpoint state→applied 但 user grant **没应用**(data_limit / expire_date 不变)。读 `ops/billing/endpoint.py:apply_manual` docstring 自承:

> "Note: this sets the invoice state to ``applied`` and writes audit rows, but does NOT mutate ``User.data_limit`` / ``User.expire_date`` — that user-side grant application is A.5 scheduler's job. When A.5 lands... Until A.5 lands, the ``applied`` state is effectively audit-only..."

但 **A.5 scheduler 已 ship 于 wave-3 PR #77**,docstring 还停留在"A.5 还没 ship"的旧时代 — **代码忘了改**:scheduler 看 `state=paid` 行才处理 grant,`apply_manual` 直接跳到 `state=applied` → scheduler 永远不 reprocess → grant **永远不应用**。production 影响:admin 救济场景 = 客户拿不到流量 = 投诉 + 丢单。

**根因**:docstring 写 "**Until X lands**" 模式 = 时间锁定,X 真 land 时**作者多半已切下一个任务,没回来更新本处依赖**。这是 documentation drift 的特定子类:
- L-039(LAUNCH-week2 vs trc20 ship)是文档 → 代码方向 drift(文档超前)
- **L-043 是反向**:代码 docstring → 实际 ship 状态 drift(代码 docstring 滞后)

两种都是"docs 与 code 不对齐",但 mechanism 相反 — L-039 误导用户,L-043 误导后续维护者(自我误导)。

**为什么 wave-3 ~ wave-8 没发现**:
- A.5 scheduler ship 时(PR #77)只测 happy path(client 真转账 → trc20_poller → state=paid → scheduler apply)
- apply_manual 是 emergency 路径,从 ship 起没真跑过一次 production
- wave-9 R3 是**第一次** operator 真用 apply_manual → bug surface

**防线**:
1. **禁用 "Until X lands" docstring 模式**:改写"current behavior"陈述句,不带时间承诺。如必须留 forward-looking,**加 issue link** 跟踪(`# TODO: integrate with scheduler when ship — see #issue-NNN`)
2. **A.x scheduler ship 时**必须扫一遍 codebase grep "Until A.5" / "Until A.x" 关键字,**移除/重写**所有相关 docstring(本次修在 PR #200)
3. **emergency 路径的实测覆盖**:任何 admin bypass / fallback / manual override 类 endpoint,**ship 时必须有 production smoke test**(不是 unit test mock,是真 SSH 调一遍)。本次教训:如果 wave-3 ship A.5 时跑过 apply_manual,bug 当时就 surface
4. **apply_invoice_grant helper 抽出**(PR #200)= 两路径(scheduler / admin)走同一逻辑,未来不再 drift

**沉淀**: ✅ PR #200 修代码 + docstring 移除 "Until A.5 lands"。下次 emergency endpoint ship 走防线 #3 实测覆盖。

**L-043 与 L-039 配对**:两条 LESSONS 应一起读 — docs drift 双向防御。

---



**现象**:eval-gate.yml(PR #146)ship advisory mode,SPEC 写 "2 周观察期" (2026-04-29 → 2026-05-13)。实际 4 天后(2026-05-02)就切 enforce — **提前 11 天**,无延迟无问题。

**根因**:advisory 期 SLA 设 "2 周" 是**保守 default**,不是基于实际 false positive 率。
- wave-3 ~ wave-9 跑过 12+ harness PR(audit-log AL.1-AL.4 + launch docs + cutover + L-040 fix)
- 0 false positive
- 现有 5 P0 + 4 regression yaml schema 全 valid
- → 提前切 enforce 是**信号驱动**,不是日历驱动

**为什么会犯**:
- "2 周" 是参考工业实践(canary deploy 1-2 周观察期)
- 但 eval-gate 是 schema validator,不是 runtime feature(canary 1 周观察是因为流量峰谷),schema 当下就能验
- SPEC 默认 wait 2 周是 over-engineered

**防线**(下次 ship advisory 类工具):
1. **SPEC 写 "0 false positive AND 12+ PR validation" 触发条件**,而非硬定 N 天
2. 工具 ship 时 emit metrics(false positive rate / advisory-only fail count),用 `aegis-watchdog.sh` 拉到 dashboard
3. 当满足条件就切 enforce(不再等 calendar)— 切完写 LESSONS / STATUS 留痕

**沉淀**: 不转 rule(单次 lesson)。**适用范围**:advisory → enforce 类切换决策(不限 eval-gate,任何 advisory 工具)。

---

## L-041 | wave-9 production cutover | docker-compose.yml hardcode :latest tag —— production image 不可重现性

**现象**:cutover production v0.4.0 → v0.4.1 后,`docker inspect aegis-panel --format "{{.Config.Image}}"` 显示 `ghcr.io/cantascendia/aegis-panel:latest`,**不是** `:v0.4.1`。SHA 对(da37f2b42cce 是 v0.4.1 build),但 tag 是 `:latest`。

**根因**:`deploy/compose/docker-compose.sqlite.yml` 的 panel service 用 `image: ghcr.io/cantascendia/aegis-panel:latest`(hardcode `:latest`),没用 `${AEGIS_VERSION}` 变量。`.env` 里的 `AEGIS_VERSION=v0.4.1` 没生效到 compose pull/run 阶段。

**为什么是 bug**:
1. **不可重现性**:回滚时 `aegis-upgrade rollback v0.4.0` 没意义,因为 compose 永远拉 `:latest`
2. **意外升级**:GH Actions push v0.5.0 → `:latest` tag 自动 update → 下次 panel 重启拉新版,无声升级
3. **L-040 链反应**:aegis-upgrade.sh 改 .env 的 AEGIS_VERSION 也无效,因为 compose 没读

**防线**:
1. **修 compose**:`image: ghcr.io/cantascendia/aegis-panel:${AEGIS_VERSION:-latest}`(env 变量驱动,fallback 仍 :latest)
2. **修 GH Actions**:tag push 触发只 push 该 tag,**不**同时 push :latest(避免无声升级)
3. **加 production check**:aegis-watchdog.sh 加一条 — image tag 不应是 :latest(否则告警)

**沉淀**: 未转 rule(单次发现,fix 在本批次 LESSONS PR 之后另起 PR 跟踪)。下次 wave 时观察是否复发。

---

## L-040 | wave-9 production cutover | aegis-upgrade.sh compose 路径 hardcode 错位

**现象**:nilou.cc cutover v0.4.0 → v0.4.1 时执行 `aegis-upgrade v0.4.1` 报:
```
[upgrade] FATAL: no compose file found under /opt/aegis/compose
```
被迫绕过自动化,手动跑 `docker compose -f /opt/aegis-src/deploy/compose/docker-compose.sqlite.yml pull panel && up -d`。

**根因**:`scripts/aegis-upgrade.sh` 在 PR #160 (v0.3.6) 设计时假设 compose 文件在 `/opt/aegis/compose/`,但 `deploy/install/install.sh` 实际把仓库 clone 到 `/opt/aegis-src/`,compose 文件路径是 `/opt/aegis-src/deploy/compose/`。两个脚本对"compose 在哪"假设不一致 → cutover 工具链断了。

**为什么 wave-3-7 没发现**:
- wave-1 cutover 是 manual 跑(install + 手动 pull 第一次 fork image)
- wave-3-7 没真做过 image tag 切换(L-035-037 都是改 marznode v0.5.7,不动 panel image)
- wave-9 是**第一次** panel image tag 切换 (v0.4.0 → v0.4.1) 的 production cutover → bug surface

**防线**:
1. **修 aegis-upgrade.sh**:扫描多个候选路径 `/opt/aegis/compose` / `/opt/aegis-src/deploy/compose` / 用 systemd unit 读 compose 路径
2. **加 staging-smoke 覆盖**:`scripts/aegis-staging-smoke.sh` 加一段 cutover dry-run,在本地 docker-compose 测 aegis-upgrade.sh 是否能找到文件
3. **install.sh + aegis-upgrade.sh 共享 SSOT**:一个 `scripts/lib/path-detect.sh` 统一 export `COMPOSE_PATH` env,两边 source 它

**沉淀**: ✅ fix PR 跟本批次 LESSONS 同时进行(下个 PR 修 aegis-upgrade.sh)。

---

## L-039 | wave-9 trc20 dashboard checkout | LAUNCH-week2 文档超前于 v0.4.0 ship 状态(documentation drift)

**现象**:operator 按 `docs/ai-cto/LAUNCH-week2-trc20-only.md` Phase 4.2 跑 `POST /api/billing/cart/checkout`(channel_code=trc20),返 **404 "payment channel 'trc20' not found"**。文档说"周末上线",但代码根本没 trc20 fallback path。

**根因**(详见 PR #186 commit f2b46737):
1. `ops/billing/checkout_endpoint.py:96` 强制查 `PaymentChannel` 表 — 但 `db.py:PaymentChannel` docstring 明说 "TRC20 is NOT represented here, it's a singleton via env vars"
2. `:175` hardcode `provider=f"epay:{channel_code}"` — 即使 channel 存在,trc20 invoice 也被打成 epay prefix
3. `:152` 强制 `BILLING_PUBLIC_BASE_URL`(EPay 码商 webhook 才用)— trc20 不该卡这步
4. **TRC20 在 v0.4.0 的 ship 状态 = "数据面已 ready,接入面没接通"**

文档(`LAUNCH-week2-trc20-only.md`)写得像"产品级 ready",实际是"代码级 spec",没区分。**operator 按文档跑必踩 404**。

**防线**:
1. **文档前置 disclaimer**:LAUNCH 类文档顶部必须写 "**最低代码版本要求** v0.X.Y 之后",且与 git tag 联动
2. **真机 staging 验证**:LAUNCH 类 checklist 上线前必须由非 author 真机跑一次,verify 每条 curl 真返 200(目前缺 staging-smoke 覆盖 launch checklist)
3. **add 005-trc20-hot-fix-roundtrip.yaml regression**(已在 PR #189 ship,防 fallback 退化)

**沉淀**: ✅ PR #186 hot-fix 修代码 + PR #189 regression yaml 防退。文档 disclaimer 落地是 follow-up(LAUNCH-week2 加版本要求)。

---

## L-037 | Round 3 mid late-8 wave-5 | RPC 一直在工作；误导的诊断 endpoint 让我们 wave-2/3/4 都误判

**结论**：panel↔marznode 增量 SyncUsers 流式 RPC **从 wave-4 开始就完全工作**。我们 wave-2/3/4 全部"看 xray_config.json file 没新增用户 → 推断 RPC 失败"的诊断方法**错了**。

**真相**：marznode v0.5.7 的 `_add_user(user, inbound)` 调 xray gRPC `add_inbound_user`——**只动 xray 内存运行时**，**不写回 xray_config.json 文件**。`/api/nodes/1/xray/config` panel API 返回 marznode `FetchBackendConfig` 结果，**就是读 xray_config.json 文件**（不是 xray 内存）。所以即使 xray 内存里有 100 个用户，文件没变，endpoint 也只显示 boot 时那 5 个。

**wave-5 诊断（PR #167 / v0.3.8）**：在 panel grpcio.py 的 `_stream_user_updates` + `update_user` 加 INFO 日志，临时给 marznode 加 `DEBUG=True` 环境变量。**真生产实测**：

```
panel  | New user `wave5_pure` added
panel  | node 1: queueing update_user user=wave5_pure id=21 inbounds=['Reality-VLESS']
panel  | node 1: dequeued user wave5_pure (id=21) inbounds=['Reality-VLESS']
panel  | node 1: wrote user wave5_pure to SyncUsers stream
marznode | DEBUG - service: adding user `wave5_pure` to inbound `Reality-VLESS`
marznode | DEBUG - xray_backend: xtls-rprx-vision
```

panel API → marznode xray runtime **端到端 ≤2 秒**。delete 也一样。`api/system/stats/users` active count 实时 +1 / -1。

**之前 wave-2/3/4 误判路径**：
- wave-2 看到"clients=5"以为 _sync 工作了 → 实际是 rollback backup 恢复
- wave-3 修 grpclib `_monitor_channel` 后看到 `Missing content-type header` → 推断 TLS 错位
- wave-4 升 marznode v0.5.7 + grpcio backend 后看到"5 clients in xray_config" 不变 → 推断"incremental stream 还 broken"
- wave-5 加 DEBUG 后才看清楚：marznode **DEBUG 日志已经显示 `adding user`**（增量同步在工作），只是 xray_config.json file 不会因为 dynamic add 而更新

**正确诊断 endpoint**：
- ❌ `GET /api/nodes/1/xray/config` — 返回静态 xray_config.json 文件
- ✅ `GET /api/system/stats/users` — 返回真实 active user count
- ✅ marznode container 的 `_add_user` DEBUG 日志（需 `DEBUG=True` env）
- ✅ panel grpcio v0.3.8+ INFO 日志（永久打开，零额外成本）

**因此 aegis-sync-clients.sh workaround 现在是真的可选**：
- 真正同步路径：panel API → grpcio SyncUsers stream → marznode xray runtime（已工作）
- workaround 路径：panel DB → 写 xray_config.json → restart marznode（可弃用，但留作 disaster recovery）
- 操作员 UX：建议保留 `aegis-user` CLI 调 `aegis-sync-clients` 作为 belt-and-suspenders（如果 panel _stream_user_updates task 死了，sync-clients 仍能恢复）

**真 B 阶段就绪度：9.5/10**（之前以 9.0 计是因为以为 RPC 还有 gap；实际无 gap）。

**落地防线**：
- ✅ panel grpcio.py INFO 日志保留（PR #167 v0.3.8）
- ✅ marznode `DEBUG=True` 默认 OFF（performance + log volume），调试时临时打开
- ⏳ wave-6 候选：移除 aegis-user CLI 的 sync-clients 自动调用（让真 RPC 是首要路径，sync-clients 仅手动 fallback）
- ⏳ wave-6 候选：写 `OPS-runbook-debug-marznode.md` — 教操作员怎么打开 DEBUG 调试

**深教训**：
> 当工具显示"什么都没变"时，**先问那个工具是否在看正确的数据源**——而不是假设系统真的什么都没做。
> wave-2/3/4 我们烧了大量精力修"不工作的 RPC"，实际 RPC 早就工作了，是我们的诊断 endpoint 在骗人。

---

## L-036 | Round 3 mid late-8 wave-4 | marznode 版本错位 = panel↔marznode 真正的根因（不是 TLS）

**wave-3 假设修正**：L-035 推断 "TLS 配置错位"——错。真根因更直接：**marznode v0.2.0 vs panel v0.3.x 的 gRPC proto 不同代**。

**深查 marznode v0.2.0 容器源码**（`/app/marznode/service/service_grpc.py`）：

| 旧 API (marznode v0.2.0) | 新 API (panel v0.3.x 调) |
|---|---|
| `FetchInbounds` | `FetchBackends` |
| `RestartXray` | `RestartBackend` |
| `FetchXrayConfig` | `FetchBackendConfig` |
| `StreamXrayLogs` | `StreamBackendLogs` |

panel 调 `/marznode.MarzService/FetchBackends` → marznode v0.2.0 没 handler → grpclib 服务端返回**缺 grpc content-type 的 unimplemented 响应** → panel 客户端报 `Missing content-type header`。

不是 TLS 错位（`openssl s_client` 探测时 marznode v0.2.0 实际跑 TLS，但 wave-4 升 v0.5.7 后 INSECURE=True env 真的让 marznode 跑 plain HTTP/2——证明 v0.2.0 的 INSECURE 是个 noop env，v0.5.7 才尊重）。

**marznode tag 选择**（`registry.hub.docker.com/v2/repositories/dawsh/marznode/tags`）：
- v0.5.7（2025-02-23 / `latest`）= 最新有 Backend API + 真正的 INSECURE 支持
- v0.2.x = 老的 Xray-only API

**修法 wave-4**（PR #165）：
- compose 三处 `image: dawsh/marznode:${AEGIS_VERSION:-latest}` → `${MARZNODE_VERSION:-v0.5.7}`
- `env.tmpl` 加 `MARZNODE_VERSION=v0.5.7` 字段（独立于 AEGIS_VERSION，因为 marznode 是 upstream 不 fork）
- 生产 VPS：`.env` 加 `MARZNODE_VERSION=v0.5.7`，`docker compose pull marznode` + `up -d --force-recreate marznode`
- panel `connection_backend` 从 `grpclib`（TLS）切到 `grpcio`（insecure_channel = plain HTTP/2，匹配 marznode INSECURE=True）

**生产验证（v0.3.7 panel + marznode v0.5.7 + grpcio backend）**：
- ✅ panel log: `@app.marznode.grpcio: Connected to node 1`
- ✅ `_sync()` `_fetch_backends` 成功（panel DB `backends` 表写入：`xray / 25.2.21`）
- ✅ `_repopulate_users` 成功推 5 个老用户（marznode runtime xray config 含全部 5 用户，email 是数字 ID `1..5`）
- ✅ marznode 日志 0 ValueError（之前 spam 也消失）
- ❌ **incremental SyncUsers stream 仍 broken**：API 创新用户（id=18 wave4_long）panel 端 `update_user` 入队列，marznode 完全不收。`_stream_user_updates` 任务可能 silent crash 或 marznode `_update_user` 对新用户 add 路径有问题
- ❌ PUT 节点触发 `_sync` 重跑也不能让新用户进 marznode runtime（深层未解：marznode `_storage.list_inbounds(tag=['Reality-VLESS'])` 可能返回空，导致 `_add_user` 跳过新用户）

**wave-4 部分胜利**：
- panel↔marznode RPC **整体连通**（之前 6 个版本 0% RPC 工作率 → 现在 5/6 用户通过 RepopulateUsers 真同步）
- email 数字格式由 marznode 自己输出（之前是 panel 错误手注 username 字符串）
- 老用户管理（增删 admin / 老用户 disable）走 RPC 真生效

**wave-5 候选**（独立 SPEC）：incremental SyncUsers stream + 新用户 add-to-MemoryStorage 路径
- 写最小可复现：panel API 创建用户 → marznode log debug → panel grpcio `_stream_user_updates` task 状态
- 可能根因：marznode v0.5.7 的 `_update_user` 对 storage 没有的新用户 + `list_inbounds` 返回空时 silent skip
- 修法选项：(a) 修 marznode 端逻辑（不可行，upstream 不 fork）；(b) panel 创建用户后 force-trigger RPC 路径；(c) 升 marznode 到更新 tag 看上游修了没

**Phase C workaround 仍是 B 阶段唯一全覆盖路径**：
- aegis-sync-clients.sh 直接写 xray_config.json + restart marznode → 100% 同步保证
- 缺点：每次 marznode 重启丢 in-memory state（包括 `_storage` 收到的增量同步）；下次 panel _sync 重新填回。可接受。

**落地防线**：
- ✅ env.tmpl pin `MARZNODE_VERSION` 独立变量
- ✅ panel default node `connection_backend` 应在新装时设为 `grpcio`（新增 install.sh 改动 — 待 wave-5 PR）
- ⏳ wave-5 SPEC：marznode 增量 RPC 不工作根因 + 修法

---

## L-035 | Round 3 mid late-8 wave-3 | grpclib 修暴露更深问题：marznode TLS 配置错位

**起因**：wave-3 修 `_monitor_channel`（PR #163 / v0.3.7）替换 `except: pass` 为显式 `logger.error(... exc_info=True)`。生产滚动后 panel 日志立刻冒出**之前看不见的真错误**：

```
grpclib.exceptions.GRPCError: (<Status.UNKNOWN: 2>, 'Missing content-type header', None)
File ".../marznode/grpclib.py", line 193, in _sync
File ".../marznode/grpclib.py", line 189, in _fetch_backends
```

每次 `_sync()` → `_fetch_backends` RPC，marznode 返回的 HTTP/2 响应**缺 `content-type: application/grpc` 头**。grpclib 客户端拒收。

**深挖**：probe marznode 62051 端口
- 明文 HTTP `curl http://...:62051/...` → `Empty reply from server`
- HTTPS `curl -k https://...:62051/...` → `Connection reset by peer`
- TLS 握手 `openssl s_client` → ✅ TLSv1.3 + AES_256_GCM_SHA384 + self-signed cert（"Verify return code: 18"）
- marznode env: **`INSECURE=True` + `SSL_CLIENT_CERT_FILE=/etc/marzneshin/ssl_client_cert.pem`**

**矛盾** — marznode 标称 INSECURE 但实际跑 TLS。INSECURE 的语义是"不验证客户端 cert"，不是"明文"。
- panel grpclib client 用自签 cert + `verify_mode=CERT_NONE` 连进去（TLS OK）
- 但 marznode 应用层校验 panel cert 失败（panel-issued cert vs marznode 期望的 CA 不匹配）
- 失败方式：连接维持但 RPC 响应空 → panel 收到不完整 HTTP/2 → 报 `Missing content-type header`

**为什么之前看不见**：v0.3.0 → v0.3.6 的 grpclib.py 代码用的是 `try: await self._sync(); except: pass`——任何异常都吞了。每次 `_sync()` 失败后 panel 静默 retry，永远不到日志。L-032 wave-2 我们只看见"clients 不同步"现象，反推到"_streaming_task 被取消"假设——其实 _sync 根本就没成功过一次，stream task 也没真启动过。

我们之前以为 PUT 节点后 xray 拿到 5 客户是"`_sync()` 跑了一次然后 stream 死"——其实那 5 客户是从 rollback backup 恢复的，panel 连一次成功的 RepopulateUsers 都没发过。

**真根因（仍未修）**：marznode 端 TLS 配置（INSECURE 模式 + 客户端 cert 校验语义）与 panel 端不一致。可能选项：
1. marznode 改 `INSECURE=False` + 提供真服务端 cert + panel 信任此 CA（最干净）
2. panel 改用 `insecure_channel`（grpcio backend）+ marznode 关 TLS（也明文）—— 测试发现 marznode 不管 INSECURE 都跑 TLS，所以这条路不通
3. 改 marznode 源（upstream `dawsh/marznode:v0.2.0`），不可行（不维护其镜像）
4. fork marznode + 自构镜像 + 改 TLS 逻辑 —— C 阶段考虑

**当前生产状态**：
- v0.3.7 grpclib 监控修 ship → ✅（错误可见 + 重试逻辑健全）
- 真 RPC 仍 broken → 🔴
- aegis-sync-clients workaround 仍是 B 阶段唯一 operational sync 路径 → ✅
- 操作员体验无变化（aegis-user CLI 自动调 sync）

**B 阶段就绪度**：仍 9.0/10。workaround 真稳。客户感知 0 影响。

**Wave-4 候选**（独立 SPEC）：marznode TLS 配置对齐。需要：
- 读 dawsh/marznode 源理解 INSECURE 实际语义
- 决定 panel cert 颁发流程是否要变（NodeSettings.certificate 是 panel-issued self-signed）
- 测：换成 panel 提供 marznode 服务端 cert + 自己作为 CA 签客户端 cert 模型
- 估时 4-6h（含 marznode 行为验证）

**落地防线**：
- ✅ 永远不再用 `except: pass` 包 RPC 调用 — `.agents/rules/no-silent-rpc-error.md`（待写）
- ✅ wave-3 grpclib 修保留（即使真 RPC 还没通，可观测性大改善）
- ⏳ Wave-4 独立 SPEC

---

## L-032 (final) | Round 3 mid late-8 wave-2 | panel↔marznode mTLS 修不动；Phase C workaround 兜住 B 阶段

**现象（最终诊断）**: panel API 创建/删除用户后，xray_config.json 不变，客户端连不上。需要手工 jq 注 UUID。

**5 个候选根因排查后，真正问题不止一个**：

| H | 假设 | 真假 |
|---|---|---|
| H-A | client cert 与 marznode CA 不匹配 | ❌ 不是（TLS 握手成功） |
| H-B | FetchUsersStats 异常掐断 channel | 部分（导致 status flap，但不直接影响 SyncUsers） |
| H-E **新发现** | `_sync()` 失败 → streaming task 不 spawn → 用户更新 silent drop | ✅ 部分对，但更深 |
| **真正主因** | panel `nodes_startup` lifespan 跑了，`add_node` 创建 MarzNodeGRPCLIB 实例，**但 `_monitor_channel` 第二轮 `__connect__()` 总 timeout 取消 streaming task**，导致 SyncUsers 永远只有第一次 _sync 时的批量 RepopulateUsers 一次机会 | 🎯 这才是 |

**实战暴露**：
- 2026-05-01 wave-2 执行 Phase A（清空 xray clients 等自动 RepopulateUsers）→ 60s 内 panel 完全无 grpclib log → 节点 last_status_change 卡 19h 前
- PUT `/api/nodes/1` 触发 `modify_node` → `remove_node + add_node` → MarzNodeGRPCLIB 重新实例化 → _monitor_channel 第一轮 connect 成功 → _sync 跑 → RepopulateUsers 推 5 用户到 xray ✅
- 10s 后 _monitor_channel 第二轮 → `await asyncio.wait_for(self._channel.__connect__(), timeout=2)` 超时 → 进 except 分支 → `set_status(unhealthy)` + `cancel(_streaming_task)` ❌
- 之后 `update_user(test_e2e)` 调 `for node_id in marznode.nodes: ...put(_updates_queue)`，但消费者已死 → 数据塞 queue 但无人读 → silent drop

**这是 grpclib 设计 bug**，不是 panel 代码 bug。修复需要：
1. 调 `__connect__` timeout 从 2s → 5-10s
2. 区分 transient timeout（不取消 streaming）vs real disconnect（取消）
3. 或重写为 keepalive PING 机制

涉及修改 upstream `app/marznode/grpclib.py` ~30 行。**估时 90 min + 测试 + 镜像 build + 滚 v0.3.7**——超出 wave-2 时间盒。

**Phase C workaround ship**（PR #159, #160, #161）：

`scripts/aegis-sync-clients.sh` 绕过整个 panel↔marznode RPC：
- 直接读 panel SQLite DB → 用 xxhash.xxh128(key) 转 xray UUID（与订阅 URI 一致）
- email = numeric `<user.id>` → 修复 marznode FetchUsersStats `int()` 报错族
- atomic 写 xray_config.json + restart marznode
- 集成到 aegis-user CLI（create/renew/disable 自动跑 sync）

**B 阶段（10-200 客户）operational 上是稳的**：
- 创建用户 → 5s 内 xray 同步 ✅ AC-1 通过
- 删除/disable → 5s 内 xray 移除 ✅ AC-2 通过
- marznode 30s+ 0 ValueError int() ✅ AC-3 通过
- 节点重启 RepopulateUsers ✅ AC-8 通过
- `aegis-mtls-rollback` 单行回滚 ≤30s ✅ AC-7 通过

**deferred 到 wave-3**:
- 真正 grpclib `_monitor_channel` 修（独立 SPEC）
- AuditMiddleware pure ASGI 重写（B.4，依赖 RBAC schema 冻结）
- staging VPS workflow（B.7）

**操作员 UX 没退化**：操作员仍跑 `aegis-user create X plan`，CLI 自动调 sync。多了 ~3s 等 marznode restart。

**落地防线**：
- ✅ scripts/aegis-sync-clients.sh ship（PR #159）+ codex 3 项 P1/P2 修（multi-inbound guard / flow preservation / AUTH_GENERATION_ALGORITHM 兼容）
- ✅ scripts/aegis-upgrade.sh `--env-file` 修（PR #160）
- ✅ install.sh 自动生成 AUDIT_SECRET_KEY + 自动部署 sync helper（PR #161 + codex P2 修：openssl 替代 cryptography + 自动检测 compose path）
- ⏳ wave-3 真正修 grpclib._monitor_channel（独立 SPEC + 90 min impl）

---

## L-034 | Round 3 mid late-8 fork-cutover | BaseHTTPMiddleware × FastAPI 0.115+ scope 不兼容族(4 PR 链式发现)

**现象**: v0.3.0 切 fork 镜像后 dashboard Management 页面空 / 全部分页 endpoint 500:

```
AssertionError: fastapi_inner_astack not found in request scope
```

`/api/users` `/api/admins` `/api/services` 全 500;`/api/users/{name}` `/api/system/stats/users` 200。差别 = 是否分页(`Page[T]` + `paginate(...)`)。

**4 个 PR 链式查根因(v0.3.1 → v0.3.5)**:

| PR | 假设 | 验证后结果 |
|---|---|---|
| #151 v0.3.2 | `AuditMiddleware`(BaseHTTPMiddleware)是元凶 | 条件挂载后仍 500 — 不是它 |
| #152 v0.3.3 | `SlowAPIMiddleware`(也 BaseHTTPMiddleware)是元凶 | 取消挂载后仍 500 — 不是它 |
| #153 v0.3.4 | `fastapi-pagination==0.12.31` 与 fastapi 0.121 不兼容,patch 升 0.12.34 | 仍 500 — fix 不在 0.12 系列 |
| #154 v0.3.5 | 跨主版本升 `fastapi-pagination → 0.15.12` | ✅ 修好 |

**根因(双层)**:

1. **应用层**: `fastapi-pagination` 0.12.x 实现假设了 FastAPI ≤ 0.114 的请求生命周期。FastAPI 0.115 引入 `fastapi_inner_astack` scope key + assert,0.12.x 没适配,所有 `paginate(...)` 路由 assert fail。fix 在 0.13.0 重写。

2. **中间件层**: starlette `BaseHTTPMiddleware` 的工作方式(包一层 ASGI app + 单独 scope)与 FastAPI 0.115 假设的 scope 直传相冲突。**任何 `BaseHTTPMiddleware`-based middleware 在 FastAPI 0.115+ 下都是定时炸弹**:
   - `AuditMiddleware`(我们写的) ❌
   - `SlowAPIMiddleware`(slowapi 0.1.9) ❌
   - 凡是 `class XXX(BaseHTTPMiddleware)` 都要重写为 pure ASGI(`async def __call__(self, scope, receive, send)`)

**实战体现**:
- 测试期 4 个用户场景下 dashboard Home 能用,Management 整页空。换个用户操作就 500。
- 4 个候选都"听起来像"根因,但只有 #154 是真的;#151 #152 是合理但非必要的 hardening。
- 4 PR 连发,生产 panel 在 1 小时内被滚 5 次。零数据丢失(volume mount + idempotent aegis-upgrade),证明 cutover 流程本身可靠。

**根因(流程)**: 我们的 fork CI 没有 staging VPS,SPEC #119 / #149 没要求"先在 staging 跑 30 分钟"再合 main → 生产是第一次真跑 fork 镜像,bug 当场暴露。L-033 + L-034 都是这个流程缺口的衍生。

**落地防线**:

- ✅ requirements.txt 锁 `fastapi-pagination >= 0.15`(防回退)
- ✅ AuditMiddleware 改回 pure ASGI(下一个 PR,v0.4 阻塞)
- ⏳ `.agents/rules/no-base-http-middleware.md` — 凡新 middleware 必须 pure ASGI,review 时 grep `BaseHTTPMiddleware` 警告
- ⏳ Round 3 mid late-9 起加 staging VPS:tag push → CI build → staging 自动 deploy + smoke → 通过才 promote 生产
- ⏳ `evals/regression/` 加 case:tag bump 后 paginated endpoint 200 必跑

---

## L-033 | Round 3 mid late-8 first-real-deploy | "代码差异化在仓库睡着"— upstream 镜像不读 fork 代码,生产 panel 跟同行一样

**现象**: 部署完发现一个矛盾:

| | 仓库代码 (fork) | 生产 panel 镜像 |
|---|---|---|
| 镜像 | cantascendia/aegis-panel | **dawsh/marzneshin:v0.2.0 (upstream)** |
| SNI selector (差异化 #1) | ✅ ship | ❌ 不在镜像里 |
| Reality audit (差异化 #3) | ✅ ship | ❌ 不在镜像里 |
| IP limiter (差异化 #2) | ✅ PR #24 ship | ❌ 不在镜像里 |
| 233 后端测试 + CI | ✅ 跑 (GitHub Actions) | N/A |
| D-012 trusted_proxies | ✅ ship | ❌ 不在镜像里 |
| audit-log 19 PR (v0.3) | ✅ stack | ❌ 不在镜像里 |

**生产 panel 实际跑的 = upstream Marzneshin 原版** = 跟 Hiddify / 3X-UI / Remnawave 一样级别。**所有差异化代码在仓库 sleeper**。

实战体现(本会话 24h 内):
- L-031 SNI 选错 2 次 — 因为 sni-selector 没在 panel 跑,我手动选
- L-032 panel↔marznode mTLS 炸 — upstream bug,我们没 patch 镜像
- L-030 install.sh 6 bug + L-032 第 7 bug — 都是因为 upstream 镜像跟 fork install.sh 假设不匹配

**根因**:

```
fork 流程缺一步:
  COMPETITORS.md 说 "我们差异化 ✅"
  → 写 SPEC + 实现代码 + 233 测试
  → push 到 GitHub 仓库
  → ❌ 没有 build & push panel 镜像到 registry
  → ❌ 没有改 install.sh 默认拉自构镜像
  → 部署用 dawsh/marzneshin (upstream 原版)
  → 差异化代码永远不被消费
```

实战中 = "你跟同行一样",不是因为差异化不存在,而是**没有部署链让差异化生效**。

**防线 / 修复路径**(C 阶段必做):

1. **建 image build pipeline**(GitHub Actions):
   - push to main → docker build → push cantascendia/aegis-panel:v0.x.x
   - 标 v0.3.0 = 第一个真正自构镜像

2. **install.sh 默认拉自构镜像**:
   ```bash
   AEGIS_VERSION="${AEGIS_VERSION:-v0.3.0}"  # 自构版本号
   # docker-compose 拉 cantascendia/aegis-panel:v0.3.0,不再 dawsh/marzneshin
   ```

3. **加 deploy-smoke CI gate**:
   - 自构镜像 push 后,跑端到端测试(创建 user / 跑订阅 / mTLS 通信)
   - 失败阻塞 deploy
   - 防 L-030/L-032 类 bug 再次溜过 dry-run

4. **patch upstream bugs 通过 fork**:
   - L-032 panel↔marznode mTLS 在 cantascendia/aegis-panel 自构镜像里修
   - 不再依赖 upstream patch (上游 dormant 7 个月,等不及)

**B 阶段 work-around**(< 50 客户阶段不做自构镜像):

- 用 upstream 镜像 + 手动 work-around (sync-clients / 手动 SNI 选择)
- 接受"差异化对客户感知 = 0"的现实
- 群里**只讲"信任 + 朋友 + 退款"** 不讲技术差异化(L-031 已沉淀)
- 50 客户后再投入 1-2 周做自构镜像 — ROI 算得过

**C 阶段触发条件**:

```
任一满足 → 启动自构镜像项目 (~1-2 周工程):
  - 客户数 ≥ 50 (sync-clients work-around 手动维护成本上升)
  - 客户问 "你们机场跟别家有啥区别" (品牌差异化诉求)
  - panel↔marznode mTLS bug 严重影响多节点部署
  - 客户数据安全要求(audit-log 用户可见)
```

**沉淀**: ✅ 本 entry。

**升级建议**(下次 batch S-O):
- 加 D-XXX 决策: "v0.3 第一个产物 = 自构 panel 镜像 + image registry pipeline"
- 把 COMPETITORS.md 矩阵分两列: "代码层" vs "生产层"(明确哪些已生效)
- 让 fork 自检 (`agpl-selfcheck.sh` 类似)同时跑 "image-deployed-check" — 验证 panel image 是 fork 自构而非 upstream

**关联**: 
- L-030 (install bugs), L-031 (SNI), L-032 (mTLS),
- COMPETITORS.md 矩阵 (5 件硬差异化)
- VISION.md "差异化护城河四件" 全部 sleeper code
- C 阶段第一件大事 = 让差异化醒过来

---

## L-032 | Round 3 mid late-8 first-real-deploy panel↔marznode | gRPC mTLS 链断,xray clients 永远空,user 全断

**现象**: friend_b 试了 30min Reality 节点,流量统计停在 0.01GB,客户端报"连接超时,没有信号"。我自己手机也连不上(在日本 → 排除 GFW)。深查发现:

1. ✅ xray :443 LISTEN
2. ✅ ufw 防火墙允许 443
3. ✅ 内外网 TCP connect 443 都 OK
4. ❌ `xray_config.json` 里 `"clients": []` **永远是空的**
5. ❌ panel 报 `node msg: "timeout"` (gRPC 调 marznode AlterInbound 超时)
6. ❌ marznode 报 `ConnectionRefusedError ('127.0.0.1', 8080)` xray 反复 stopped/started

**根因 5 层洋葱**:

```
表层:        客户端 "超时 / 没信号"
第 1 层:     xray Reality 拒绝任何 UUID handshake (clients=[])
第 2 层:     panel 创建 user 时 UUID 没推到 xray
第 3 层:     panel.gRPC(marznode).AlterInbound 调用超时
第 4 层:     panel ↔ marznode mTLS 双向认证不对称
第 5 层:     install.sh 缺一步 — marznode 自动生成的 server cert
            panel 不信任,gRPC TLS 握手成功但 streaming 失败
```

**真正的 install.sh 设计缺陷**:

```
install.sh step 7 (我之前 PR #140 加的) 只做了:
  panel → /api/nodes/settings → 拿 panel 的 client cert
  → 写到 marznode 的 SSL_CLIENT_CERT_FILE

漏了反方向:
  marznode → 启动时 self-sign 一个 server cert
  → panel 需要 trust 这个 cert 才能调 gRPC
  → 但 panel 不知道 marznode 的 server cert
  → 即使 TCP 握手成功 mTLS handshake 失败 → AlterInbound 超时
```

**实战 Work-around**(B 阶段不修 mTLS,直接绕):

每次创建/删除 user 后,**手动**把 user UUID inject 到 xray_config.json:

```bash
# 拿 user UUID (从订阅 URL base64 decode 提取)
UUID=$(curl -s "http://127.0.0.1:8443/sub/$user/$key" \
  -H "User-Agent: v2rayN" | base64 -d | grep -oP "vless://[a-f0-9-]+" | \
  head -1 | cut -d/ -f3)

# inject 到 xray_config.json (jq 操作)
jq ".inbounds[0].settings.clients += [{\"id\":\"$UUID\",\"flow\":\"\",\"email\":\"$user\"}]" \
   /opt/aegis/data/marznode/xray_config.json > /tmp/x.json && \
   mv /tmp/x.json /opt/aegis/data/marznode/xray_config.json

# 重启 marznode → xray 重读 config → clients 数组生效
docker restart aegis-marznode
```

**关键陷阱**:

1. **每次 PUT /api/nodes/{id}/xray_config**(panel API 改 SNI / inbound)→ panel 试图给 marznode push 新 config → 超时 → marznode 重启 → **clients 被清空** → user 全断
2. **每次 marznode 重启** → 读 host 文件 `xray_config.json` → 如果文件 clients=[] → 空载启动 → user 全断
3. **"node status: healthy"** 是 panel 看 TCP connect OK 给的,**不代表 gRPC 真通**。msg 字段才是真信号(`"timeout"` = bug)

**永久修复路径**(C 阶段做):

1. 修 `app/marznode/grpclib.py` 的 mTLS 双向证书逻辑:
   - panel 启动时把自己 CA 发给 marznode (新 endpoint /api/nodes/{id}/ca)
   - marznode 用 panel CA 签 server cert (不再 self-signed)
   - panel 信任所有 panel-CA 签的 cert
2. install.sh step 7.5 加 gRPC reachability 验证(不只是 TCP):
   - panel 调 marznode FetchUsersStats RPC,wait 30s,fail = exit 5
3. 给 upstream Marzneshin 提 issue: `INSECURE=True` 应该真禁 mTLS, 不是只是文档不要

**B 阶段 work-around 自动化**:

`tools/aegis-sync-clients.sh` (本 PR 新增) — 单命令同步 panel users → xray clients:

```bash
aegis-sync-clients   # 拉 panel 全部 users → inject 到 xray_config.json → 重启 marznode
```

每次 admin 在 panel 创建 user 后手动跑一次。或者 cron 每 5 分钟跑(client 列表幂等)。

**沉淀**: ✅ 本 entry + `tools/aegis-sync-clients.sh` 脚本(本 PR ship)。

`.agents/rules/marznode-grpc-broken-known-issue.md` 候选 — "Marzneshin upstream `dawsh/marznode` 镜像 mTLS 不对称已知 bug,B 阶段用 sync-clients work-around,C 阶段自构 panel 镜像修 grpclib"。

**关联**: L-030 (install.sh 6 bugs), L-031 (SNI selection),  
PR #140 (install fixes), PR #141 (L-031),  
本 PR (L-032 + sync-clients).

---

## L-031 | Round 3 mid late-8 first-real-deploy SNI selection | 改 Reality SNI 必先验"国内可达 + TLS 1.3 + H2 三件套",社区共识不能盲信

**现象**:首次给 friend_b 配 Reality 节点,SNI 我**两次都选错**:

| 尝试 | 选择 | 错在哪 |
|---|---|---|
| 1 | `www.tesla.com` | 太流行,DPI 重点关注 |
| 2 | `discord.com` | **国内被墙(2018年起)**,SNI 用被墙网站 = GFW 加 SNI 层阻断时节点立刻死 |
| 3 | `www.microsoft.com` | 社区警告"太流行" — 短期可用但不抗未来封锁 |

第二次 user 直接挑出来"discord 国内被墙吧?" — **我没验证就改了**,凭印象选,违反 cross-review 精神。

**根因**:

1. **凭印象选 SNI** — 没实际跑过国内可达性 + TLS 三件套验证
2. **`hardening/sni/selector.py` 在仓库里"睡着"** — sni-selector skill 设计上做这件事(同 ASN 邻居 + TLS 1.3 验证 + DPI 黑名单 + 国内 ping),但 v0.2 panel 镜像 `dawsh/marzneshin:v0.2.0` **不含 fork 代码**,所以选型完全靠运营方手动
3. **env.tmpl 已经有合格默认值** — `REALITY_SNI_DEFAULT_GLOBAL=www.microsoft.com` / `_JP=www.lovelive-anime.jp` / `_KR=static.naver.net` / `_US=swdist.apple.com` + `BLOCKLIST=www.google.com,speedtest.net`。这些是 compass §"冷门 SNI" 的 SEALED 选择,但**panel 镜像不读**

**根因总结**:**fork 写了 sni-selector,但生产 panel 跑的是 upstream 镜像没有 fork 代码,选型变成手工**。这是镜像 build 链断裂的体现。

**社区共识(2026-04-30 调研)**:

✅ 推荐 (冷门 + TLS 1.3 + 国内可达):
- `download-installer.cdn.mozilla.net` (Mozilla CDN, Firefox 走这条更新)
- `addons.mozilla.org`
- `gateway.icloud.com` / `swdlp.apple.com` (Apple 全球 CDN)
- `www.lovelive-anime.jp` (动漫小站,小众无人盯)
- `static.naver.net` (韩国 CDN)

❌ 不要(虽然 TLS 1.3 但太流行 / 已被墙):
- `www.google.com` ❌ DPI 黑名单
- `speedtest.net` ❌ 黑名单
- `www.tesla.com` ⚠️ 流行
- `www.microsoft.com` ⚠️ 流行
- `discord.com` ❌ 国内被墙
- `www.cloudflare.com` ⚠️ 流行

**防线**:

1. **改 SNI 前必须三验证**(命令模板,无 sni-selector 时手动跑):
   ```bash
   # On VPS:
   echo | openssl s_client -connect <SNI>:443 -tls1_3 -servername <SNI> 2>/dev/null | grep Protocol
   curl -sI https://<SNI>/ | head -1   # 看 HTTP/2 + 状态码
   # On 国内手机/朋友: 试着浏览器开 https://<SNI> 看是否秒开
   ```
   三全过 → 才是合格 SNI

2. **首选 env.tmpl 内置默认**(`REALITY_SNI_DEFAULT_*`)— compass 团队已经审过的,默认就是冷门 + 国内可达

3. **sni-selector skill 必须在生产 panel 跑** — 当前 v0.2 镜像缺 fork 代码,B 阶段 work-around 就用 env.tmpl defaults;C 阶段升级到自构 panel 镜像把 hardening/sni/ 注入

4. **频繁换 SNI 是反模式** — 每换一次客户必"更新订阅",同一周换 3 次 = 客户体验崩溃。一次决策选好 + 等真实 ping/丢包数据再换

**实战补充(2026-04-30 当晚发生第 4 次错)**:
本 LESSON 写完 5 分钟后,我又把 SNI 改到 `download-installer.cdn.mozilla.net`,VPS 端 TLS+H2 都通,但 friend_b 国内 client **超时**!**LESSON 写了"国内可达性"防线,但我自己跳过了这步**。

**真根因 = VPS 端测通 ≠ 国内可达**:
- mozilla CDN 在国内有些 ISP / 时段访问不稳
- VPS 在 Tokyo,看到的是 mozilla 全球 CDN 边缘节点,
- 国内 client 看到的是不同的 mozilla CDN 边缘节点(可能被限速 / 路由差)
- **不同地理位置看到的 SNI 可达性可能完全不同**

**升级防线(必须同时三个 vantage points 都通过)**:

```
1. VPS 端: openssl s_client + curl HTTP/2 验证 ✅
2. 国内 client 端: 真实 ping + 浏览器秒开验证 ⚠️ 缺这步就翻车
3. tesla.com / 已知能用的 SNI 做 baseline 对照 ✅
```

**B 阶段 work-around**(没国内测试 client 时):
- **不要换** SNI,除非有 client 反馈"现在卡"
- 所有"理论上更好"的 SNI 候选先记 docs,等有 ≥3 个朋友实测数据再批量切换
- **friend_b 用过的 SNI = 已验证的 SNI**(不要轻易抛弃)

**沉淀**:✅ 本 entry + 5 分钟后实战 lesson。`.agents/rules/reality-sni-selection.md` 候选 — "改 Reality SNI 必跑三件套 + 国内 client 实测 + 不要换已验证的 SNI"。下次新部署再犯就升硬规则。

**关联**:同会话 L-030 (install.sh 实战 6 bug)、`SPEC-sni-selector.md`、`hardening/sni/selector.py`、`compass §"冷门 SNI"`、env.tmpl L77-L87。

---

## L-030 | Round 3 mid late-8 first-real-deploy | install.sh 在真 VPS 上踩到 6 个 bug,全是路径/启动顺序/healthcheck 错配

**现象**: 2026-04-30 第一次在 Vultr Tokyo VPS 跑 `bash deploy/install/install.sh --non-interactive --domain nilou.cc --db sqlite --marznode same-host --cf-tunnel skip`。Dry-run 全绿,真跑炸 6 次:

| # | bug | 表现 | 根因 |
|---|---|---|---|
| 1 | `SQLALCHEMY_DATABASE_URL` 用 host 路径 | sqlite3 unable to open database file | render.sh 默认值 `/opt/aegis/data/panel/db.sqlite3` 是宿主路径,容器内 mount 到 `/var/lib/marzneshin`,数据库 URL 应该用容器路径 |
| 2 | `UVICORN_UDS=` 空字符串 | uvicorn `IndexError: string index out of range` 启动崩溃 | env.tmpl 把 UVICORN_UDS 渲染成空,uvicorn 试 `path[0]` 上空字符串炸。必须 unset 不能空 |
| 3 | nginx 服务引用 `/opt/aegis/nginx/nginx.conf` 但 install.sh 不渲染该文件 | nginx 容器 mount fail "not a directory" | install.sh 没生成 nginx.conf,但 compose 强制 mount,B 阶段都用 CF Tunnel 不需要 nginx |
| 4 | marznode `INSECURE: "True"` 不真禁 mTLS | "No certificate provided for the client; exiting" | marznode 上游代码读 `SSL_CLIENT_CERT_FILE` env,缺这个文件就退出。INSECURE 文档误导 |
| 5 | marznode 缺初始 `xray_config.json` | "config doesn't have inbounds" ValueError | marznode 启动验证 xray config 不允许 inbounds=[],install.sh 没准备初始模板 |
| 6 | panel healthcheck path 错 | `curl http://127.0.0.1:8443/api/system/info` → 404 | Marzneshin 上游没这个 endpoint;用 `/openapi.json`(FastAPI 自动)代替 |

**根因**:install.sh 之前只用 `--dry-run` 验证模板渲染 + Alembic stepped CI 测 schema,**从来没在真 VPS 跑过完整 9 步**。Dry-run 跳过 docker compose up + healthcheck → 跳过所有运行时启动顺序问题。

**防线**(本 PR 修复):

1. `render.sh`:`DATABASE_URL` 默认值改容器路径 `sqlite:////var/lib/marzneshin/db.sqlite3`
2. `env.tmpl`:`UVICORN_UDS=` → 注释 `# UVICORN_UDS=`(unset 而非空)
3. `docker-compose.sqlite.yml`:
   - panel healthcheck `/api/system/info` → `/openapi.json`,`start_period` 30s → 60s
   - marznode 加 `SSL_CLIENT_CERT_FILE` env + 加 host volume `marznode-ssl:/etc/marzneshin`
4. `templates/xray_config.json`(新):marznode 初始 xray config 含 placeholder dokodemo-door
5. `install.sh` step 6:加 `prepare_marznode_dirs()` 创建 marznode + marznode-ssl 目录 + 拷贝 xray_config.json;**只先启 panel** 不启 marznode
6. `install.sh` step 7:panel healthy 后 `fetch_marznode_client_cert()` 拉 panel 的 client cert,然后再 `up -d` 启 marznode

**沉淀**:✅ 本 entry。`.agents/rules/install-script-real-deploy-gate.md` 候选 — "install.sh 改动必须在 fresh VPS 跑完整 9 步,不只 dry-run"。本次改动若再次出 bug 就升级为硬规则。

**额外收获**(同一天发现):
- nginx 服务缺 nginx.conf 模板 — 现阶段 B 都用 CF Tunnel,nginx 暂不修(留下次)
- DASHBOARD_PATH env 在 marzneshin 新版本被忽略,dashboard 永远在 `/dashboard/` — 不是 install.sh bug,是 upstream 行为变化
- `PASSWORD_HASH` admin 密码字段:Marzneshin upstream `marzneshin-cli.py admin create` 现在用 `--sudo` 不是 `--is-sudo`(API 变化,2025-2026 间)

**关联 PR**:本 PR 修 1-6 项;nginx + DASHBOARD_PATH 留 follow-up。

---

## L-029 | Round 3 mid late-7 wave-5 | TanStack Router 生成文件手动 patch 模式(无 vite plugin 时)

**现象**: AL.4' dashboard PR(#136)新增 `routes/_dashboard/audit.lazy.tsx`,运行 `pnpm exec tsc --noEmit` 时 fail:`Argument of type '"/_dashboard/audit"' is not assignable to parameter of type 'keyof FileRoutesByPath'`。Codex review P1 抓到。

**根因**: TanStack Router 用 vite plugin 自动生成 `dashboard/src/routeTree.gen.ts`(开发时跑 `pnpm dev` / `pnpm build` 时触发)。但**单 session 推进 dashboard 改动时**,Claude 在主目录直接写代码不跑 vite,生成文件不会自动更新。新加 `.lazy.tsx` 文件后,routeTree.gen.ts 7 处需要 audit 条目:
1. `createFileRoute('/_dashboard/audit')()` import declaration
2. `DashboardAuditLazyImport.update({...})` 路由 update 块
3. `FileRoutesByFullPath` 接口
4. `FileRoutesByTo` 接口
5. `FileRoutesById` 接口
6. `fullPaths` / `to` / `id` 三处 union literal
7. `DashboardRouteChildren` interface + value
8. 底部 children 字符串清单 + 文件 metadata

漏一处 → tsc 失败,sidebar 链接 type error。

**Codex 怎么发现的**(L-028 数据点延伸): codex 真的跑了 `pnpm exec tsc --noEmit` 看到 type error,而 Claude 自审走 mental model "vite plugin 会自动处理" 没去验证。这是 L-028 同一根因 — 单模型自审带着同一组假设。

**防线**:

1. **首选 — 跑 vite 自动重新生成**:开发流程 `pnpm dev` 一秒钟内重新生成 routeTree.gen.ts,然后 commit。本会话主目录跑 vite 大依赖,所以跳过这条。
2. **手动 patch 时镜像参考路由**:本 PR mirror reality 路由的所有 7 处出现位置(本 LESSON 上面列的)。grep `DashboardRealityLazyImport\|DashboardRealityLazyRoute\|/_dashboard/reality` 一次,逐处镜像,**漏一处 tsc 就 fail**。
3. **PR description 必须标注**:"手动 patch routeTree.gen.ts; 后续动同 dashboard module 的 PR 应跑 vite 重新生成"。本 PR #136 已加。
4. **Codex review 必须跑**:tsc type-check 验证是 codex 抓 P1 的关键途径,业务路径 PR 严格遵守 L-028 / `.agents/rules/codex-cross-review.md` 跑流程。

**沉淀**: ✅ 本 entry。`.agents/rules/dashboard-routes.md` 候选,内容 = "新增 `.lazy.tsx` 必须 vite 自动生成或手动 patch 7 处镜像最近的 module";如果未来有第二次同样事故就升级。

---

## L-028 | Round 3 mid late-7 wave-4 | §48 Cross-Review 实战:Codex 抓到 4 个 Claude 自审会全漏的 P2 真 bug

**现象**: 单会话推进 audit-log v0.3 第一块,4 个代码 PR(#125-#128)依次跑 §48 Claude → Codex 跨模型 review。Codex(gpt-5.5)在 3 个 PR 中找到 **4 个 P2 真问题**(不是 nit),全部需要立即修复:

| PR | Codex P2 finding | 真实风险 |
|---|---|---|
| #125 | `BIGINT PRIMARY KEY` SQLite 不 alias rowid | 默认 `SQLALCHEMY_DATABASE_URL=sqlite:///db.sqlite3`,普通 `AuditEvent()` 插入 IntegrityError |
| #126 | `User.key` + `subscription_url` 未 redact(实际项目 bearer 字段) | 加密审计 row 被合法 key holder 解密后仍含 16-hex bearer token |
| #126 | `Admin.hashed_password` 实际列名漏(我列了 `password_hash` 别名) | bcrypt 哈希进 audit ciphertext,offline crack 风险 |
| #127 | `.env.example` 缺 `AUDIT_SECRET_KEY` | fresh install `cp .env.example .env` 流程 boot 时 fail-loud 但 operator 无 hint |

**关键观察**: Codex 真的去 grep 项目实际代码:
- `app/models/user.py` → 验证 `User.key` / `subscription_url` 字段名
- `app/db/models.py` → 验证 `Admin.hashed_password` 列名
- 默认 `.env.example` → 验证 fresh-install 流程

**Claude 自审会全漏这 4 个**:因为 Claude(主 agent)写代码时引用 SPEC § 而非 grep 实际项目字段。SPEC 写 "redact subscription_token" 但实际字段是 `subscription_url` —— SPEC 自己也没去 grep。

**根因**: 单模型自审有"自我盲点"——同一个模型既写代码又审代码,写代码时的假设(SPEC 说啥就是啥)审代码时也带着。Cross-model review 强制第二个模型用**独立先验**重新审视,会去做 first model 没做的功课(grep 项目代码 / 读默认 env / 验证 fresh-install 流程)。

**落地防线**:

1. **§48 Cross-Review 必须跑**(非可选):任何业务路径(`scripts/business-paths.txt`)代码 PR 在 push 后 *必须* 跑 codex-bridge,无论 PR 看起来多简单。本 wave 的 4 个 PR 都"看起来简单",每个都被 Codex 找到 P2。
2. **Forbidden 路径 P0/P1 必有 cross-review**(L-018 升级):`auth/` `crypto/` `migration/` `payment/` 涉及真 bug 时影响半径大;cross-review 是必须双签的物理实现。
3. **小 PR 多次审 > 大 PR 一次审**:本 wave 把 audit-log 拆成 5 个 stack PR(schema → redact → crypto → config → ...),每个独立 cross-review。如果合成 1 个大 PR,review 长度超 codex 上下文,会漏 finding。
4. **修复 P2 后必须**重新跑 codex 二审(`bash .agents/skills/codex-bridge/run.sh HEAD`):不是同一 commit 不会被 dedup,确保修复正确。本 wave PR #125 / #126 都跑了二审,二审都 PASS。
5. **dev env decouple 包冲突**(本机 `decouple` 0.0.7 shadow `python-decouple` 3.8)让 pytest 跑不动,但**不影响 codex review**(codex 用自己的 sandbox)。固化为日常 hygiene:`pip uninstall decouple -y`(只留 `python-decouple`)。本会话不动用户环境,留待下次 dev setup。

**rule 沉淀**: `.agents/rules/codex-cross-review.md` 候选,内容 = "业务路径 PR 必跑 + 修 P2 后必二审 + 拆小 PR 多次审"。可在下个 batch S-O refresh 时落地。

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
