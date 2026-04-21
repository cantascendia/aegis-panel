# 产品愿景 + 技术愿景

> 最后更新:2026-04-21(第零轮)
> 更新频率:每轮若有愿景进化,CTO 主动更新;用户说"愿景更新"时输出完整最新版

---

## 🎯 产品愿景

### 📦 最终产品形态

**面向中型付费机场运营者的 "Marzneshin + Reality 2026 加固版" 一体化发行版**。

定位:比上游 Marzneshin 更抗封、更抗共享、更快部署、自带商业化运营基础设施。一键让 VPS 变成可运营的合规机场。

### 目标用户画像

- 主要用户:运营 **>200 付费用户、多节点(3-10 VPS)** 的独立机场主
- 用户痛点:
  - 上游 Marzneshin 无计费/续费/订阅管理,无法直接变现
  - 五件套加固需要手动拼接 V2IpLimit + luIP + Xray policy + CF Tunnel + SNI 选型,试错成本高
  - Reality SNI 选错一个就被封,没有自动化巡检
  - 封禁后没有健康度仪表盘,故障恢复全靠运维肉身
- 用户不是:普通单用户自用(对他们 Marzneshin/Marzban 原版就够了)
- 用户不是:超大型商业(Vigo/WgTunnel 级别),那个量级需要另一套架构

### 🧩 核心功能全景

| 模块 | 状态 | 功能 |
|---|---|---|
| Reality/VLESS/XTLS-Vision 协议栈 | 🔄 上游已有 | 默认策略需按 compass_artifact 调优 |
| 多节点管理 | ✅ 上游已有 | Marzneshin + Marznode gRPC 原生支持 |
| **SNI 智能选型器** | ⏳ 待建(差异化 #1) | 同 ASN 邻居扫描 + TLS 1.3/H2/X25519 验证 + DPI 黑名单 |
| **防账号共享集成** | ⏳ 待建 | Marzban 生态工具不兼容(见 COMPETITORS),需自研或改造 |
| **面板加固套件** | ⏳ 待建 | CF Tunnel/Access 向导、Dashboard Path 随机化、JWT ≤60min、WAF 规则 |
| **一键部署引擎** | ⏳ 待建 | install.sh + docker-compose + ansible playbook |
| **商业化运营层** | ⏳ 待建(差异化 #2) | 订阅计费 / 流量告警 / 到期续费 / 管理员 RBAC |
| **Reality 健康度仪表盘** | ⏳ 待建(差异化 #3) | SNI 被封预警、IP 进黑名单检测、主动切换 |
| XHTTP / Hysteria2 备用通道 | ❓ 待确认优先级 | 规划文档点名,但上游不原生 |

图例:✅ 完成 / 🔄 已有需改 / ⏳ 待建 / ❓ 优先级待定

### 🏁 当前状态 vs 最终目标

- 代码:刚完成 fork,**上游功能保留 100%,自研功能 0%**
- 完成度:结构就位 ~30%,功能落地 ~0%
- 关键差距:
  1. 安全基线不达商业化标准(AUDIT.md 显示安全得分 3/10,JWT/CORS/限流全缺)
  2. 零计费系统 → 无商业模式
  3. 测试覆盖率 1/10(只有迁移测试)
  4. SNI 选型 / IP 限制 / CF Tunnel 集成全部需要自研

### ⚠️ 规划文档挑战点(CTO 反思)

- compass_artifact 文档未覆盖**计费、流量上限告警、订阅过期**等商业化必备功能,必须补齐
- "V2IpLimit + luIP 同时跑"可能互相干扰;且**两者均不兼容 Marzneshin**(见 COMPETITORS.md),真实方案是自研或 port
- "XHTTP/Hysteria2 作为备用通道"引入协议栈复杂度,若用户不需要可推迟到 v0.3
- "一键部署"容易流于脚本堆砌,真正有价值的是**可幂等、可回滚、可观测**的部署

---

## 🧠 技术愿景

### 📐 架构评判

**上游 Marzneshin 现状**:FastAPI + SQLAlchemy 2.0 + gRPC + Vite/React dashboard。**控制面/数据面分离**已到位,比 Marzban 单体设计进步明显。

**能支撑 ≤1000 用户**,>200 付费场景需要以下投入:

- DB 切 PostgreSQL 16(默认 SQLite 在并发订阅生成时吃不消)
- Redis 7 作为缓存层(用户查询 / 统计 / 限流令牌桶)
- 加固模块**插件式**:`hardening/{sni,reality,iplimit,panel}` 各自独立可裁剪
- 部署层独立于业务:`deploy/` 不碰 `app/`
- 运营层独立:`ops/{billing,audit,alerting}` 可单独替换

### 🔄 根本性改变

1. **引入 `hardening/` 模块目录** — 与上游 `app/` 解耦,upstream 同步时冲突面最小
2. **引入 `deploy/`** — IaC 独立,docker-compose/ansible/install.sh 分离管理
3. **引入 `ops/`** — 运营层独立承载计费、告警、报表、RBAC
4. **把 dashboard 的双组件库(shadcn + NextUI)收敛到单一体系** — 见 AUDIT ⑧-5,bundle size 和一致性双收益

### 💡 创新机会(差异化核心)

1. **SNI 智能选型器**(没有任何竞品做到,Hiddify 只做静态候选列表)
2. **Reality 健康度仪表盘** — 实时监测 SNI 被封、IP 黑名单、主动告警并推荐新候选
3. **一键机场**:install.sh 拉起完整五件套 + CF Tunnel + 计费 demo 数据
4. **合规一键自检**:AGPL 版权头、源码披露入口、依赖 license 扫描自动化

### 🛠️ 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| Python | 3.12 | 上游选 |
| Web | FastAPI 0.115 + Uvicorn | 上游选,Starlette 生态足够 |
| ORM | SQLAlchemy 2.0 + Alembic | 上游选,typed mappings 是 bonus |
| DB | PostgreSQL 16 | >200 用户 SQLite 撑不住 |
| Cache | Redis 7 | 热数据 + 限流令牌桶 + 会话 |
| 前端 | Vite + React + TS + shadcn/ui | 上游选,现代栈 |
| 包管 | pnpm | 上游选 |
| Lint | Biome + Ruff(待引) | Biome 上游已有,Ruff 是我们加 |
| 部署 | Docker Compose(单机)+ Ansible(多节点)+ CF Tunnel | 标准组合 |
| CI | GitHub Actions | 免费 + 够用 |
| 监控 | Prometheus + Grafana(可选 Loki 日志) | 标配 |

### 🎯 如果只能做三件事

1. **P0 安全修复 + 计费系统 MVP**(让项目可上线可变现)
2. **SNI 智能选型器 MVP**(差异化护城河 #1)
3. **一键部署引擎 v1**(商业化落地抓手)

其他都是第二波。

---

## 架构演进路线图(摘要)

完整详见 `docs/ai-cto/ROADMAP.md`。

- **v0.1**(4-6 周):上游 fork 可跑 + P0 安全修复 + PostgreSQL 切换 + 测试基础设施
- **v0.2**(6-8 周):SNI 选型器 + 一键部署引擎 + 计费 MVP + 基础告警
- **v0.3**(8-12 周):Reality 健康度仪表盘 + 原生 IP 限制 + RBAC + XHTTP/Hysteria2 备用通道

---
