# SPEC — L-032 panel↔marznode gRPC mTLS 修复

> 状态：**SPECIFY**（draft，等用户审核 + 拍板 TBD）
> 上游 issue：L-032（LESSONS.md）
> 下游 PLAN / TASKS：待 specify 通过后产出
> 维护者：CTO + 用户

---

## 1. Why（为何修，不修代价）

**当前痛点**（生产 v0.3.5，2026-05-01）：

每次 panel 增 / 删 / 改用户后，xray-core 实际服务的用户列表**不变**——必须 SSH 上 VPS 手工 `jq` 注入 UUID 到 `/opt/aegis/data/marznode/xray_config.json` 然后 `docker compose restart marznode`。

**业务影响**：
- 🔴 商业化阻塞：≥10 付费客户后，每个续费 / 退费 / 流量重置都要 SSH，运营崩溃
- 🔴 多节点阻塞：手工注 UUID 模式只能管 1 个节点，第 2 节点（≥3 客户）无法启动
- 🔴 audit-log 失语：admin 操作记录到 `aegis_audit_events` 但用户面无变化，审计与现实脱节
- 🟠 体验退化：v0.3.5 切 fork 后 marznode 日志 `ValueError: invalid literal for int() 'riku_self'` 持续 spam，污染监控信号

**不修可能**（B 阶段保守路径）：
- 写半自动脚本 `aegis-sync-clients`（DB → jq → restart）作为永久 work-around
- 客户增长封顶 ~10（运营带宽极限）
- 多节点路线放弃

**修了之后**：v0.3.6 之后 panel 增删用户即时生效，多节点支持自动开锁，audit-log 字段对得上现实。

---

## 2. What（修什么，不修什么）

### Scope 内（必修）

1. **panel 端 grpclib 客户端能成功向 marznode 发起 `SyncUsers` 流式 RPC**——admin 在 panel 创建用户后 ≤5s 内 marznode 的 xray-core inbound clients 反映新增。
2. **panel 端 grpclib 能成功 `RepopulateUsers`**——节点重启 / 重新挂载后能从 panel 全量拉一次用户列表。
3. **生产环境验证**：删除当前手工注入的 4 个 UUID，让 panel 通过正常流程 push 回去；v2rayNG 现有订阅依然可连（订阅 URL 不变，但 server 端 client UUID 由 panel SyncUsers 重新填）。
4. **回滚保险**：保留 `xray_config.json` 备份；失败时 30 秒切回 v0.3.5 + 手工注入。

### Scope 外（不修）

- ❌ 多节点扩展（这是 mTLS 修好之后**自然解锁**的能力，非 SPEC 内交付）
- ❌ marznode 服务端代码改造（upstream 项目，本仓不 patch）
- ❌ audit-log middleware pure ASGI 重写（独立 SPEC，wave-3 主题）
- ❌ install.sh AUDIT_SECRET_KEY 自动生成（独立小 PR）

---

## 3. Acceptance Criteria（可量化验收）

| AC | 描述 | 验证方法 |
|---|---|---|
| AC-1 | panel 创建用户 5s 内 marznode 的 xray clients 包含新 UUID | API `POST /api/users` → SSH 看 `/opt/aegis/data/marznode/xray_config.json` 的 `inbounds[].settings.clients` |
| AC-2 | panel 删除用户 5s 内 marznode 的 xray clients 移除 | 同上 |
| AC-3 | marznode 日志连续 5 分钟无 `ValueError int() ...` 错误 | `docker logs aegis-marznode --since=5m \| grep ValueError \| wc -l` = 0 |
| AC-4 | v2rayNG 用现有订阅链接连接，ip.sb 显示日本 IP（friend_b 端到端不破） | 手工浏览器验证 |
| AC-5 | panel `/api/nodes/1/inbounds` 返回 200 + 实际 inbound 列表 | curl |
| AC-6 | 节点 status 显示 `healthy`，message 列空（无 timeout 残留） | `select status, message from nodes` |
| AC-7 | 失败可在 30 秒回滚到 v0.3.5 + 手工注入态，4 用户连接不中断 ≥30s | 演练 |
| AC-8 | marznode 容器重启（`docker restart aegis-marznode`）后 ≤30s 内 panel 自动调 `RepopulateUsers` 把全量用户列表重新推送，xray_config.json 的 clients 跟 panel users 表完全一致 | restart marznode → 等 30s → diff `jq '.inbounds[].settings.clients[].id'` 与 `select id,username from users` |

---

## 4. 已知诊断（探索阶段成果）

### 4.1 不是 grpcio fallback

Sub-agent 初判 "panel 默认 grpcio 不安全 channel" → **错**。
DB 实测：`select connection_backend from nodes` = `grpclib`。grpclib 是带 mTLS 的客户端。

### 4.2 真正的 RPC 链

- `POST /api/users` → `app/db/crud.py:create_user` → `app/marznode/operations.py:update_user(user)` → `app/marznode/grpclib.py` 入队 `_updates_queue` → `_stream_user_updates()` 调 `SyncUsers` 流式 RPC

### 4.3 现场症状

- `select * from nodes`：tokyo-1 / 127.0.0.1:62051 / **grpclib** / status=`healthy` / message=`timeout` / last_status_change=2026-04-30 10:04
- marznode 持续 spam `FetchUsersStats`/`int() 'riku_self'`——这是**手工注 UUID 时用了 username 字符串当 xray client email**，marznode 期望 `<panel_user_id>.<protocol>` 数字前缀格式
- `/api/nodes/1/inbounds` 返回 500（疑似又一个 paginated endpoint 或 dep 问题）

### 4.4 候选根因（待 PLAN 阶段实证收敛）

| H# | 假设 | 验证方法 | 落地代价 |
|---|---|---|---|
| H-A | panel 客户端 cert 与 marznode 服务端 CA 不匹配（cert chain 错） | 在 marznode 容器跑 `openssl s_client -cert ... -connect 127.0.0.1:62051`；对比 panel 发出的 cert 与 marznode 期望的 CA | 重发 cert（已有 NodeSettings.certificate API） |
| H-B | `FetchUsersStats` 抛 ValueError 把 grpclib **持久 stream 整体掐断** → SyncUsers 没机会跑 | 临时清空 xray_config.json clients → 看 marznode 不再抛 → 测 SyncUsers 是否成功 | 清空 + 重启 marznode + panel 创建用户 |
| H-C | panel 启动后 `_stream_user_updates` task 没起 / 早死 | panel 内 `print(asyncio.all_tasks())` | 在 marznode init 加 task 检查 |
| H-D | grpclib 连接成功但 SyncUsers RPC 因为 cert verify mode 问题被服务端默默拒绝 | 在 panel 容器调 `curl --cert ... https://127.0.0.1:62051` 看 TLS 握手 | 调 cert verify mode |

**初步直觉**：H-B 概率最高（`FetchUsersStats` 是 marznode 主动周期发起的，但在 grpclib 上下文里**任何 RPC handler 抛未捕获异常都会关 stream**）。

---

## 5. TBD 决策（已锁定 — 用户授权 CTO 自决）

| TBD | 选项 | 决策 | 理由 |
|---|---|---|---|
| TBD-1 修复路径 | A 数据先净化 / B 代码先读 / C 双管齐下 | **C** | A 30 分钟试 H-B 假设性价比最高；不通再 B |
| TBD-2 回滚边界 | A 接受短暂中断 / B 延期 / C 通知 friend 后做 | **C** | friend_b/c 是测试员可通知；维护时段操作 |
| TBD-3 H-B 失败回退顺序 | — | **H-A → H-D → 写 work-around** | 重发 cert 比改 TLS code 安全；最差也有 fallback 脚本兜底 |
| TBD-4 xray client email 格式 | A 纯数字 / B 复合 / C 不动 | **A** `<user_id>` 纯数字 | marznode `int(stat.name.split(".")[0])` 期望此格式；最小改动 |

锁定时间：2026-05-01 specify phase 闭环。
锁定方式：用户授权 CTO 自决（"你自己判断"）。
反悔成本：PLAN 阶段还能回炉；impl 后改要新 SPEC。

---

## 6. 时间盒（specify 阶段估）

- specify（本文件）：**0.5h** ✓
- plan（PLAN-mtls-fix.md）：1h
- tasks（TASKS-mtls-fix.md）：0.5h
- impl + 生产验证：3-6h（看 H 命中哪个）
- review + lessons：0.5h

**总：6-9h**，跨 2-3 个工作 session。

---

## 7. 不属于本 SPEC 的回归测试

- L-034 防御 eval：tag bump 后 paginated endpoint 200（已在 L-034 wave-2 候选 #4 staging VPS workflow 内）
- 节点重启 RepopulateUsers 端到端 case：**已纳入 AC-8**（codex review 反馈，原稿误标为 AC-2 覆盖）

---

## 8. 决策记录（D-XXX）

修完之后产生的 DECISION 候选（PLAN 阶段决定是否记入 DECISIONS.md）：
- D-### "panel↔marznode mTLS 客户端实现 = grpclib（默认且唯一）"
- D-### "xray client email 字段编码 = ?"（依赖 TBD-4）

---

## 9. 状态

specify phase 已闭环（2026-05-01）：
- ✅ TBDs 全部锁定（§5）
- ✅ codex cross-review 通过（commit c9912f0，REVIEW-QUEUE.md 2026-05-01T13:45:53）+ AC-8 P2 修复（commit 1c544b2）
- ⏭️ 下一步：PLAN-mtls-fix.md（phase 2/3）
