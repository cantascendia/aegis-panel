# 路线图(ROADMAP)

> 最后更新:2026-04-21(第零轮)
> 每阶段末尾或重大优先级变化时更新

---

## 总体思路

**先加固基底,再建差异化,再上商业化**。任何阶段未达标,不进入下一阶段。

时间基于"每周 20-30 小时开发投入 + CTO 并行规划"的节奏估算,实际可能浮动 30%。

---

## v0.1 — 基底加固 + P0 安全(4-6 周)

**目标**: 把刚 fork 的 Marzneshin 变成"可上线但还不商业化"的加固版。

### 必做(依赖顺序)

1. **P0 安全修复**(1-2 周)
   - JWT Secret 外置到 `.env`(禁止库存储)
   - Admin 登录速率限制(slowapi + Redis)
   - CORS 收紧(whitelist 具体域名)
   - JWT 时效收紧到 ≤60 分钟
   - CI 集成 `safety check` + `pip list --outdated`
   - 依赖更新:`v2share` beta → 稳定替代评估

2. **数据库切 PostgreSQL 16 + Redis 7**(1 周)
   - Alembic 迁移脚本兼容多 DB
   - Redis 作为限流令牌桶 + 用户查询缓存
   - `docker-compose.yml` 加 postgres + redis 服务

3. **测试基础设施**(1-2 周)
   - pytest fixture(DB / redis / mock marznode / mock aiohttp)
   - 关键路由端点测试(admin login / user CRUD / subscription gen)
   - GitHub Actions CI:`pytest + vitest + biome + ruff + safety`
   - Dashboard:至少 login / user-list / node-list 的组件快照测试
   - 目标覆盖率:backend ≥40%,dashboard ≥30%

4. **目录骨架 + README**(0.5 周)
   - `hardening/` + `deploy/` + `ops/` 目录 + 各自 README + LICENSE 声明
   - 根目录 `DEVELOPMENT.md`(本地启动步骤 + 常见故障排查)
   - Makefile 补全 `test / lint / format / db-reset` 目标

### 验收

- [ ] AUDIT.md 安全维度从 3/10 提升到 ≥7/10
- [ ] 测试维度从 1/10 提升到 ≥5/10
- [ ] CI 全绿,任何 push 自动跑完 backend + frontend 测试
- [ ] `/api/source` 或 dashboard footer 源码链接就位(AGPL 合规)

---

## v0.2 — 差异化落地 + 一键部署(6-8 周)

**目标**: 让项目有**能卖的理由**。SNI 选型器 + 一键部署 + 计费 MVP。

### 必做

1. **SNI 智能选型器 MVP**(2-3 周)
   - `hardening/sni/selector.py` CLI:输入 VPS IP → 输出候选 SNI 列表(JSON)
   - 实现 6 条硬指标验证(TLS 1.3/H2/X25519/非跳转域/同 ASN/非 DPI 黑名单)
   - 集成到 dashboard "新建节点" 流程 — 创建节点时调一次,预填 serverName
   - 单元测试 + mock 网络调用

2. **一键部署引擎 v1**(2-3 周)
   - `deploy/install.sh` — 单节点一键(幂等):apt / docker / compose / 初始化 DB / 生成 .env / 启动
   - `deploy/compose/` — 生产 compose 配置(含 postgres + redis + marzneshin + marznode + nginx)
   - `deploy/ansible/` — 多节点部署 playbook
   - `deploy/cloudflare/` — CF Tunnel 自动配置脚本(Zero Trust API 调用)

3. **计费系统 MVP**(2-3 周)
   - 数据模型:`Subscription`、`Payment`、`Invoice`(见 AUDIT.md ⑦-1)
   - 订阅价格与流量/时长套餐配置
   - 管理员手动 "激活订阅" + "续费" 操作(无支付网关,先走手工)
   - 用户到期/超额告警(email + Telegram)
   - 审计日志:所有订阅/支付操作 immutable log

4. **审计日志系统**(1 周,可与 #3 合并)
   - `AuditLog` 表 + 中间件自动记录管理员操作
   - Dashboard 页面查看审计日志(支持筛选 admin、时间段、操作类型)

### 验收

- [ ] 新节点创建流程中 SNI 候选自动预填,用户 80% 场景不用手填
- [ ] 从空 VPS 到面板可访问用时 ≤15 分钟(install.sh 跑完)
- [ ] 管理员能为用户 "激活订阅" + 查看到期提醒 + 查看订阅历史
- [ ] 所有关键操作有审计记录

---

## v0.3 — 运维成熟 + 抗封进化(8-12 周)

**目标**: 从"能卖"走到"可长期运营"。健康度仪表盘 + 原生 IP 限制 + 备用通道 + RBAC。

### 必做

1. **Reality 健康度仪表盘**(2-3 周,差异化 #3)
   - 实时监测每节点 SNI 可达性、延迟、握手成功率
   - DPI 黑名单变化监测(外部情报源 + 内部事件统计)
   - 自动告警 + 推荐新 SNI 切换
   - 历史趋势图(Prometheus + Grafana)

2. **原生 IP 限制模块**(2 周)
   - `hardening/iplimit/` 自研(参考 Hiddify `shared_limit.py` 算法)
   - 订阅 Xray stats API(通过 Marznode 转发)
   - 按用户级计数 + 超限自动断连 + Telegram 告警
   - 配置可精细(时长、并发、国家过滤)

3. **备用通道(XHTTP / Hysteria2)**(2-3 周)
   - `hardening/fallback/` 支持多协议回切
   - 订阅链接同时下发 Reality + 备用协议
   - 客户端指南 + dashboard 客户端状态面板

4. **RBAC + 管理员分层**(2 周)
   - `Role` + `Permission` 表
   - 默认角色:sudo / ops / finance / support
   - UI 管理角色 + 权限矩阵
   - 细化审计:记录 "who + action + target"

5. **自动化 Upstream 同步**(1 周)
   - Codex Automation:每周 `git fetch marzneshin-upstream`,diff changelog,生成报告
   - 冲突预警 + 人工审核后合并

### 验收

- [ ] 健康度仪表盘能在 SNI 被封后 10 分钟内推送告警并推荐替代
- [ ] IP 限制能在用户 3 设备并发时自动断连一个并推送 Telegram 提醒
- [ ] 用户在 Reality 被封的国家自动切到 Hysteria2
- [ ] 管理员可为"财务审计员"角色配置"只读 + 只看付款数据"权限

---

## v1.0 — 发布候选(基于 v0.3 稳定 2 个月后)

**目标**: 产品正式 1.0,开始对外分发。

### 准备工作

- 文档站(MkDocs 或 Docusaurus)
- 多语言用户指南
- 部署场景白皮书(单节点、3 节点、10 节点)
- 性能基准测试(1000 用户压测 + 报告)
- 安全审计(外部团队)
- 升级/迁移脚本(从上游 Marzneshin 迁入我们分支)

---

## 长期方向(2026 下半年 +)

- **向上游贡献 PR**:IP 限制、审计日志、RBAC 等若通用,提回 Marzneshin 上游
- **Kubernetes 支持**:超大规模部署
- **API 生态**:开放 OAuth2 + Webhook,允许第三方 dashboard/客户端
- **企业 SaaS**:向"面板即服务"方向演进(我们托管,客户只填域名和上游)

---

## 路线图调整原则

- 每轮末尾评估当前阶段达成度,未达成就不进下一阶段
- DPI 黑名单变化 / 新漏洞爆发 → 安全任务永远可插队到最高优先级
- 商业 deadline 可驱动某项优先级提升(如营销计划要求 v0.2 提前 2 周)
- 新竞品出现重大创新 → 每 3 轮评估一次是否需要跟进(参考 COMPETITORS.md "追踪坐标")

---
