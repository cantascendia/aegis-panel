# Aegis Panel — Project Constitution

> 本文件定义项目不可妥协的原则。所有 SPEC / PLAN / 代码改动必须服从。
> 修改本文件需要 CTO + 至少一位 senior engineer 双签。
> 最近修改:2026-04-28 by CTO + Sub-agent C(初版,等用户 + senior 双签生效)
> 状态:**DRAFT** — 待用户与 senior engineer 双签(参考 §37.3 双签流程)

---

## ① 产品宪法

### 必须

- 一句话产品愿景:**面向中型付费机场运营者(>200 付费 / 多节点 3-10 VPS)的 Marzneshin + Reality 2026 加固版一体化发行版**
- 核心目标用户:独立机场主,有以下痛点
  - 上游 Marzneshin 无计费/续费/订阅管理,无法直接变现
  - 五件套加固(SNI 选型 / IP 限制 / Reality 巡检 / 面板加固 / CF Tunnel)拼接成本高,试错代价大
  - Reality SNI 选错就被封,缺自动化巡检
  - 故障恢复无健康度仪表盘,运维全靠肉身
- 解决:抗封 + 抗共享 + 快部署 + 商业化运营基础设施(订阅 / 计费 / 告警 / RBAC)
- 差异化护城河四件:
  1. SNI 智能选型器(同 ASN + TLS 1.3 + DPI 黑名单)
  2. 商业化运营层(计费 / 续费 / 订阅 / 告警)
  3. Reality 健康度仪表盘(被封预警 + 主动切换)
  4. 一体化部署(install.sh + Ansible + CF Tunnel + AGPL 自检)

### 绝对禁止

- 服务普通单用户自用(那是 Marzneshin / Marzban 原版的市场,跑去同质化等于自杀)
- 服务超大型商业(Vigo / WgTunnel 级别需要另一套架构,不是本项目时间盒目标)
- 给中国大陆 / 伊朗 / 俄罗斯 IP 提供运营 panel 入口(D-003 留痕,合规风险;数据面节点不在此限,但控制面 panel 必须切流)
- ~~做用户自助门户 SPA / 用户侧 web auth(D-016 决策)~~ → **D-016 已被 D-018(2026-05-06,双签生效)推翻**:商业化 Phase B 解禁,见 `docs/ai-cto/DECISIONS.md` D-018。门户实现路径硬约束:`customer-portal/`(独立目录,不混入 `dashboard/` 上游同步区,不混入 `app/` 后端)
- 把 v2share 0.1.0b31 beta 替换成自研订阅生成(D-013,2026-10-26 复评前不动)

---

## ② 架构宪法

### 必须

- **控制面 / 数据面分离**:Marzneshin(控制面,本仓库)通过 gRPC 调用多个 Marznode(数据面 = xray-core),不允许在控制面进程内直接跑 xray
- **upstream 同步区**(`app/` + `dashboard/src/`)修改前必须 `git diff` 评估冲突;每季度 `git fetch marzneshin-upstream` 审核 changelog,**不盲合**
- **自研模块独立目录**:
  - `hardening/` — SNI 选型器、Reality 配置审计、IP 限制器、面板加固向导
  - `deploy/` — install.sh、Ansible playbook、CF Tunnel 自动化、AGPL self-check
  - `ops/` — 计费、流量告警、审计日志、RBAC、管理员分层
- **`app/db/extra_models.py` aggregator**:自研 SQLAlchemy model 单点注册(L-014 硬规则,防 Alembic autogenerate 漏检)
- **`app/marzneshin.py` 对 upstream 1 行 diff 封顶**:`apply_panel_hardening()` 三位一体入口,所有 hardening hook 在此一处挂载,不散落
- **计费分层**:`ops/billing/pricing.py`(纯函数,产 UserGrant)与 `ops/billing/grants.py`(改 User 表)互不 import,scheduler 是唯一胶水(D-014)
- **每个并发 Claude session 独立 worktree**(SESSIONS.md 铁规则 #7,L-018)

### 绝对禁止

- 自研代码混入 `app/` 上游目录(增加 sync 冲突面,违反"冲突最小化"原则)
- mutate 已 merged 的 Alembic revision(L-015 硬规则,**必须**走新 safety-net revision)
- 删除上游 `LICENSE` 头或 commit message Co-Authored-By 行(违 AGPL §5)
- 删除重建替代精确修复(铁律 #11,丢失 git blame + 增加 review 面)
- 跨 feature 共享一个全局 `TrustedProxyMiddleware`(D-012 反对,必须 per-feature `*_TRUSTED_PROXIES` env)
- 在 cart-checkout 前置层 import SQLAlchemy `User`(违 D-014 边界,污染 import 图)
- 链上支付匹配做"差不多"/"近似"/模糊金额匹配(D-015,只允许 memo > exact-amount + window)

---

## ③ 安全宪法

### 必须

- **JWT secret 外置 .env**(禁止 DB 存,禁止硬编码,禁止 commit 进 git history)
- **Admin 登录速率限制**(slowapi + Redis,默认 5/minute;只用同步 def 路由,不装饰 async def — L-010)
- **CORS 收紧白名单**(具体域名,禁止 `*`)
- **JWT 时效 ≤ 60 分钟**
- **bcrypt ≥ 12 rounds** 密码 hash
- **per-feature `*_TRUSTED_PROXIES` env**(CIDR 列表,反代信任 D-012)
- **SSL 默认安全**:`main.py` 无 SSL 时强制监听 127.0.0.1(外部访问走 SSH tunnel / Nginx / Cloudflare Tunnel),不要改这个行为
- **AGPL §13 网络服务源码可获取**:已落地 `NOTICE.md` + `deploy/compliance/agpl-selfcheck.sh` + UI footer + `GET /api/system/info` source_code_url 字段
- **TRC20 链上匹配**:memo HMAC-SHA256 8 字符 salt 化 → 退回精确金额 + 时间窗口;欠付 / 超付都不补偿(D-015)
- **`MIN_CONFIRMATIONS` 默认 1**(Tron 3 秒块,paranoid operator 可调 19 = SR round)
- **Forbidden 路径**(`auth/` `crypto/` `payment/` `billing/` `secrets/` `keys/` `migration/`)双签 + spec-driven + ≥80% mutation score(`.claude/rules/forbidden-paths.md`)

### 绝对禁止

- 硬编码 secrets(JWT / DB password / merchant_key / Xray 私钥 / CF token / EPay key / TRC20 hot wallet seed)
- 跨 feature 共享一个全局 `TrustedProxyMiddleware`(D-012 反对)
- 使用 `slowapi @limiter.limit` 装饰 `async def` 路由(L-010 已知 bug,limiter 静默 noop)
- merchant_key / 用户敏感字段以明文落 DB(必须 Fernet 加密)
- 自动 fetch 链上汇率(D-015,操作员 env 锁定 `BILLING_TRC20_RATE_FEN_PER_USDT`,不依赖 CoinGecko / Binance)
- vibe coding(铁律 #13)— 不读代码就部署、yes-man AI、hallucination 反复迭代加深、依赖幻觉、context starvation、eval gaming(`.claude/rules/forbidden-paths.md` 六大反模式)

---

## ④ 合规宪法

### 必须

- **License: AGPL-3.0**(继承上游 Marzneshin,见 `LICENSE` 与 `NOTICE.md`)
- **保留上游版权头**:每个 upstream 修改文件首部不删,commit message 保留原作者 Co-Authored-By
- **`NOTICE.md` 声明 fork source URL**:满足 AGPL §13 用户获取源码义务;Source code URL 行格式锁定为 `**Source code URL**: <url>`(`agpl-selfcheck.sh` canonical-extraction 契约)
- **`deploy/compliance/agpl-selfcheck.sh` 上线前跑通**(差异化 #4 第一件工具,D-017;退出码契约 0/1/2,bash 4+ 零依赖)
- **i18n bilingual baseline**:中文(简体)+ English 必备,所有 UI 文本走 i18n key,新加 i18n 缺 4 语言时走 i18next defaultValue fallback(L-012 防线)
- **依赖 license 兼容**:仅引入 MIT / Apache-2.0 / BSD-2 / BSD-3 / ISC / AGPL-3.0 兼容许可
- **运营敏感数据走 .env**:JWT secret / DB 密码 / Xray 私钥 / CF 凭据 / EPay key / TRC20 凭据(`.gitignore` 已覆盖)

### 绝对禁止

- 闭源商业化(违反 AGPL §13)
- 引入 GPL-2.0-only / commercial-only / proprietary 依赖
- `requirements.txt` 引入名字奇怪 / 0 stars / 0 download / 维护者匿名的依赖(防 supply chain attack;新增依赖必须在 PR 描述给出维护活跃度证据)
- 把 `v2share 0.1.0b31` 替换成自研而不评估(D-013 决策,2026-10-26 复评前不动)
- UI 硬编码中英文(必须走 i18n key)

---

## ⑤ 质量宪法

### 必须

- **测试覆盖**:核心模块 ≥ 70% 行覆盖;**Forbidden 路径**(auth / payment / billing / crypto / migration)≥ 80% mutation score(`.claude/rules/test-lock.md`)
- **Spec → Test → Code 顺序**(§18.6,Forbidden 路径强制)
- **CI 三门禁**:`ruff check` + `pytest` + `pip-audit` 全绿(自研目录 `hardening/` / `deploy/` / `ops/`)
- **Alembic stepped-upgrade CI**:防 L-016 已 merged revision 被 mutate;每个 PR 跑 `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` 三连
- **AGPL self-check 上线前跑通**(`bash deploy/compliance/agpl-selfcheck.sh` 退出 0)
- **Eval Gate**(铁律 #12):修 `CLAUDE.md` / `.claude/commands/*.md` / `.claude/agents/*.md` / `.claude/skills/*/SKILL.md` / `playbook/handbook.md` 必须配套 `evals/golden-trajectories/` yaml + `/cto-eval run` 通过
- **Test-Lock**(铁律 #14):测试断言 read-only,只能改实现;合法修改场景仅限 spec 变更 / bug 修复 / 新增覆盖 / 结构 refactor
- **每个并发 Claude session 独立 worktree**(SESSIONS.md 铁规则 #7,L-018,防 cross-contamination)
- **`HARNESS-CHANGELOG.md` 追加**:每次 PR 改 `.claude/*` / `.agents/*` / `docs/ai-cto/{CONSTITUTION,STATUS,LESSONS,DECISIONS,SESSIONS,ROADMAP}.md` 必须追一行(§34)

### 绝对禁止

- 改测试断言"作弊式 TDD"(铁律 #14;失败实现 → 改测试让它通过)
- 修 CLAUDE.md / commands / agents / skills **不带 eval** 进 main(铁律 #12)
- 跳过 `git diff` 直接 commit upstream 同步区
- "硬编码占位 = 未完成" 视为可 ship(铁律 #9;`TODO`/`FIXME`/mock 数据上线)
- 删除"麻烦的"测试(铁律 #14)
- 失败实现 → 喂 AI 测试源码让它"猜答案"(L-026;只允许喂 stderr 盲修复)

---

## 修改流程(§37.3)

1. **CTO 提案**:开 issue 描述新条款 + Why + 推翻条件(预设证伪条件,防教条化)
2. **Senior engineer review**:至少一位 senior + 第二模型(`/cto-review`)独立审一遍
3. **双签后 PR 修改本文件**:PR 必须打 `requires-double-review` label
4. **Commit message** 标注 "Constitution amendment: <短描述>"
5. **修改后 30 天内**,所有 in-flight SPEC 必须重审是否冲突;新冲突 SPEC 暂停或合规化

## 验证

每条都可 grep / 工具检查:

- 项目身份 → `cat README.md docs/ai-cto/VISION.md`
- AGPL 合规 → `bash deploy/compliance/agpl-selfcheck.sh`(退出 0)
- Forbidden 路径覆盖 → `pytest tests/ --cov=ops/billing --cov=hardening --cov-fail-under=80`
- worktree 隔离 → `git worktree list`(并发会话期 > 1 项)
- Eval Gate → `ls evals/golden-trajectories/*.yaml`(覆盖最近 .claude/* 改动)
- HARNESS-CHANGELOG 追加 → `git log -p docs/ai-cto/HARNESS-CHANGELOG.md` vs `.claude/` 改动 commit 列表

## 与其他文档关系

| 文档 | 频率 | 性质 | 修改门槛 |
|---|---|---|---|
| `CLAUDE.md` | 频繁 | 当前迭代规则 + quick reference | 普通 PR |
| `docs/ai-cto/SPEC-*.md` | 频繁 | 单 feature 规约 | 普通 PR |
| `docs/ai-cto/DECISIONS.md` | append-only | 单决策记录 | 普通 PR(append-only 模式) |
| `docs/ai-cto/LESSONS.md` | append-only | 教训记录 | 普通 PR |
| `CONSTITUTION.md`(本文件) | 季度级 | **不可妥协原则** | **双签 PR + `requires-double-review` label** |

CLAUDE.md / SPEC / DECISIONS / LESSONS 是"日常工作流",CONSTITUTION 是"宪法层" — 当低层文档与本宪法冲突时,**以本宪法为准**;如发现冲突,必须先走"修改流程"修宪,再回头改低层文档。

---

## 引用的硬规则索引

- **14 条铁律**:见 `CLAUDE.md` 顶部("铁律")
- **D-001 ~ D-017**:`docs/ai-cto/DECISIONS.md`(D-012 反代信任 / D-013 v2share 暂留 / D-014 计费分层 / D-015 链上匹配 / D-016 admin checkout / D-017 AGPL 自检优先)
- **L-001 ~ L-026**:`docs/ai-cto/LESSONS.md`(L-010 slowapi async / L-012 i18n fallback / L-014 extra_models / L-015 Alembic immutable / L-018 worktree 隔离 / L-026 失败回灌)
- **`.claude/rules/forbidden-paths.md`**:Forbidden 路径双签 + spec-driven + 80% mutation
- **`.claude/rules/eval-gate.md`**:Eval Gate(铁律 #12)
- **`.claude/rules/test-lock.md`**:Test-Lock(铁律 #14)
- **`NOTICE.md`**:AGPL §13 fork URL + 上游 attribution

---

> **DRAFT 状态说明**:本文件为初版起草,未生效。生效条件 = 用户(项目所有者)+ 一位 senior engineer 在 PR 中明确批准 + 合并到 main。生效后状态改为 **SEALED**,后续修改走 §37.3 双签流程。
