# PLAN — L-032 panel↔marznode gRPC mTLS 修复

> 状态：**PLAN**（spec-driven phase 2/3）
> 上游：SPEC-mtls-fix.md（已 merged，TBDs 锁定）
> 下游：TASKS-mtls-fix.md（phase 3/3）

---

## 1. 关键代码层认知（grpclib.py 通读）

### 1.1 Channel 生命周期

```
MarzNodeGRPCLIB.__init__
  ├── load mTLS cert/key (verify_mode=CERT_NONE — panel 不验 marznode server cert)
  ├── Channel(address, port, ssl=ctx)
  └── _monitor_task = asyncio.create_task(_monitor_channel())  ← 启动监控

_monitor_channel  # 每 10s 循环
  ├── try await __connect__(timeout=2s)
  ├── except: status=unhealthy, message="timeout", cancel _streaming_task
  └── else:
      └── if not synced:
          ├── _sync()  ← 关键阻塞点
          │   ├── _fetch_backends()
          │   ├── store_backends(...)
          │   ├── users = list_users()  # from local DB
          │   └── _repopulate_users(users)  ← 实际推 4 用户
          ├── _streaming_task = create_task(_stream_user_updates())
          └── status=healthy
```

### 1.2 用户增删传播链

```
POST /api/users (admin)
  → crud.create_user (commit DB)
  → marznode.operations.update_user(user)
  → db_node.update_user(user, inbounds)
  → MarzNodeGRPCLIB.update_user
  → _updates_queue.put({"user": user, "inbounds": inbounds})

[消费者]
_stream_user_updates  # 必须先启动
  └── async with stub.SyncUsers.open() as stream:
      └── while True:
          ├── user_update = await _updates_queue.get()
          ├── stream.send_message(UserData(user=User(id, username, key), inbounds=[...]))
          └── (marznode 端写 xray_config.json + reload xray)
```

**致命缺陷**：`_stream_user_updates` 仅在 `_sync()` 成功后才 spawn（line 92）。如果 `_repopulate_users` 失败，streaming task 不存在，`_updates_queue.put()` 仍成功——**数据塞进 queue 但没消费者，永久丢**。

---

## 2. 候选根因再排序（多发现 H-E）

| H | 假设 | 评估 | 优先 |
|---|---|---|---|
| H-A | client cert 与 marznode CA 不匹配 | 不太可能 — `__connect__` 成功（status 偶尔 healthy），TLS 握手没断；只是某个 RPC 失败 | 低 |
| H-B | `FetchUsersStats` 异常掐断整个 channel | 较低 — fetch_stats 是独立 unary call，挂了不影响 SyncUsers stream（除非底层 channel 一起断） | 中 |
| H-C | `_stream_user_updates` task 没起 / 早死 | **高**（新发现 H-E） | **★** |
| H-D | gRPC TLS verify mode 问题 | 极低 — 已设 CERT_NONE | 极低 |
| H-E **新** | `_sync()` 失败 → streaming task 永远不 spawn → SyncUsers RPC 没人调 → 用户增删 silent drop | **最高** | **★★★** |

**新工作假设 = H-E**：
- 现场症状 `status=healthy, message='timeout'` 表示监控曾切换过状态
- 用户从未通过 panel API 加进 xray（只能手工注），完全符合 streaming task 不存在
- marznode 端 `FetchUsersStats` spam 来自周期 stat 调用（独立路径），不冲击诊断

---

## 3. 修复 Plan

### 3.1 Phase A — 数据净化 + H-E 实证（45 min）

| Step | 操作 | 预期 | 命令 |
|---|---|---|---|
| A1 | SSH backup `/opt/aegis/data/marznode/xray_config.json` → `xray_config.json.bak.<ts>` | 文件存在 | `cp` |
| A2 | 把 xray_config.json 的 `inbounds[].settings.clients` **清空**（`[]`） | json 合法 | `jq '.inbounds[].settings.clients = []'` |
| A3 | `docker compose restart marznode` | 容器 Up | — |
| A4 | 等 60s 让 panel `_monitor_channel` 跑两轮 | — | `sleep 60` |
| A5 | 看 panel 日志 grep `Connected to node`、`opened the stream`、`_sync`、`_repopulate` | 至少看到 `Connected to node 1` | `docker logs aegis-panel --since=2m` |
| A6 | 看 xray_config.json 的 clients | **应包含 4 个 panel 用户的 UUID**（panel 自动 RepopulateUsers） | `jq '.inbounds[].settings.clients'` |

**判定**：
- A6 看到 4 用户 UUID → H-E 假设成立 + 自愈 → 跳到 Phase D 验证 AC-1..8
- A6 仍空 → `_sync()` 还失败，进 Phase B 加日志诊断

### 3.2 Phase B — 仅当 Phase A 失败时（90 min）

| Step | 操作 | 输出 |
|---|---|---|
| B1 | 在 panel 容器开 verbose log：`PYTHONUNBUFFERED=1 LOG_LEVEL=DEBUG` | 完整 grpclib trace |
| B2 | 直接调 `docker exec aegis-panel python -c '...'` 实例化 grpclib client，手动 `_sync()` | 看具体异常类型 + 行号 |
| B3 | 根据异常分类决策：<br>• `GRPCError` → marznode 拒服务，转 H-A cert 重发<br>• `StreamTerminatedError` → 协议不匹配，转 H-D | 走 SPEC TBD-3 顺序：H-A → H-D → workaround |

### 3.3 Phase C — workaround（仅当 A+B 都失败，最后兜底）

写 `/usr/local/bin/aegis-sync-clients`：
- 读 panel DB → 生成 xray_config.json client 列表 → diff + atomic write → restart marznode
- 半自动：admin 增删用户后手工跑 `aegis-sync-clients`
- B 阶段顶住，wave-3 再正经修

### 3.4 Phase D — AC-1..8 端到端验证（30 min）

| AC | 操作 | 预期 |
|---|---|---|
| AC-1 | API POST /api/users 创 test_e2e | 5s 内 xray_config.json clients 含新 UUID |
| AC-2 | API DELETE /api/users/test_e2e | 5s 内 xray_config.json clients 移除 |
| AC-3 | 5 分钟看 marznode 日志 `ValueError int()` count | =0 |
| AC-4 | v2rayNG 用 friend_b 现有订阅 connect → ip.sb | 显示日本 IP |
| AC-5 | curl /api/nodes/1/inbounds | HTTP 200 + items 列表（依赖 pagination 修，已在 v0.3.5） |
| AC-6 | `select status,message from nodes` | status=healthy / message=NULL or "" |
| AC-7 | 演练：rollback 到 v0.3.5 + 手工注入态 30s 内完成 | friend_b connect 不中断 ≥30s |
| AC-8 | `docker restart aegis-marznode` → 等 30s → diff xray_config.json clients vs panel users | 完全一致 |

---

## 4. 是否要改代码？

**Phase A 走通 → 零代码改动**（仅运行态净化），SPEC 时间盒大幅压缩。

**Phase B 触发 → 改 `app/marznode/grpclib.py`**：
- L88-90 `try: await self._sync() except: pass`：吞异常 → 改成 `except Exception as e: logger.error("sync failed for node %i: %s", self.id, e, exc_info=True)`
- L92 `_streaming_task = create_task(...)`：改成无论 `_sync` 是否成功都 spawn streaming task（让 SyncUsers 单独工作，不依赖 RepopulateUsers 成功）
- 这两点修了 → 即使 `_sync` 抛错，user update 也能流出去

**Phase C 触发 → 新增 `scripts/aegis-sync-clients.sh`**（不改 panel 代码）

---

## 5. AC 与 yaml eval 映射

per playbook §35，将 SPEC AC-1..8 落成 `evals/regression/005-mtls-fix-acceptance.yaml`：

```yaml
id: mtls-fix-acceptance
description: L-032 panel↔marznode gRPC mTLS — full repair acceptance
priority: P0
expected_steps:
  - "Phase A: empty clients + restart marznode"
  - "Verify xray_config repopulated in 60s"
  - "Create test user via API → assert UUID in xray_config ≤5s"
  - "Delete test user → assert UUID removed ≤5s"
forbidden_actions:
  - "manual jq UUID injection in production"
  - "skip Phase D verification"
acceptance_criteria:
  - "AC-1..8 from SPEC-mtls-fix.md §3 all green"
```

TASKS phase 写入。

---

## 6. 风险

🔴 **R1 friend_b 连接中断 ≤60s**：Phase A2-A4 期间 marznode 无 xray clients。
  缓解：操作前微信通知 friend_b/c "晚 X 点 maintenance"（TBD-2 已锁定 C 路径）。

🟠 **R2 Phase A 看似自愈但实际 RepopulateUsers 写错 client email 格式**：
  marznode 仍 spam `int('riku_self')`。
  缓解：AC-3 验证；如不通过转 Phase B 改 grpclib.py 把 `username` 字段映射到 `email` 时用 `id` 不用 username。

🟡 **R3 Phase B 改代码需新 build + 滚 v0.3.6**：
  延期 ~1h。
  缓解：local syntax check + sub-agent code review 先把疑似改错的语法层兜住，再发 PR。

🟢 **R4 Phase C 兜底**：永远有 fallback。

---

## 7. 时间盒细化

| Phase | 时长 | 累计 |
|---|---|---|
| A | 45 min | 45 min |
| B（仅触发时） | 90 min | 2h 15min |
| C（仅触发时） | 60 min | 3h 15min |
| D | 30 min | A+D=1h 15min, A+B+D=2h 45min, A+B+C+D=3h 45min |
| TASKS phase 文档 + eval yaml | 30 min | +30 min |

最坏 4h 15min（A+B+C+D+docs），最好 1h 45min（A+D+docs）。仍在 SPEC 6-9h 时间盒内。

---

## 8. 进入 TASKS phase 前

- [x] grpclib.py / operations.py / user.py 通读
- [x] H-A..H-E 排序定 H-E 为头号
- [x] 修复 plan 三相 ABC 落定
- [x] AC ↔ Phase 映射闭环（AC-1..8 全在 Phase D 验证清单）
- [x] yaml eval 雏形定义
- [x] 风险 R1..R4 全列 + 缓解

PLAN phase 闭环。下一步：TASKS-mtls-fix.md（具体文件改动 + 测试 case + 操作脚本）。
