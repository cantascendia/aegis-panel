# 项目状态(STATUS)

> 最后更新:2026-04-21(第零轮结束)
> 更新频率:每 3 轮或重大节点

---

## 当前轮次

**第零轮 —— 项目启动 / Fork + 开荒**

状态:✅ 已完成

## 项目画像(一句话)

Marzneshin 硬 fork,面向商业化机场 >200 付费用户 + 多节点 + Reality 2026 加固,Round 0 已完成基础设施搭建(fork、CTO 配置、八维审核、竞品分析、记忆文件、路线图),尚无自研代码。

## 产品完成度

- 核心功能 0/8 已实现(自研部分)
- 上游功能 6/6 保留(面板 / 多节点 / Reality / 订阅 / Telegram / 多语言)
- 关键缺口:SNI 选型器 / 计费 / IP 限制 / CF Tunnel 集成 / 审计日志 / 健康度仪表盘 / 备用通道 / RBAC

## 当前代码质量评分

**5.0 / 10**(基于 AUDIT.md 八维平均)

| 维度 | 分数 |
|---|---|
| 架构 | 7 |
| 代码质量 | 6 |
| 性能 | 5 |
| 安全 | 3 ⚠️ |
| 测试 | 1 ⚠️ |
| DX | 6 |
| 功能完整性 | 4 |
| UX | 7 |

## 关键决策记录

- **Fork 基底:Marzneshin(不是 Marzban)** — 活跃维护 + 原生多节点优势,详见 DECISIONS.md #1
- **License 策略:严守 AGPL-3.0 合规** — 保留 upstream 版权头,自研模块可选独立 license(见 NOTICE.md),详见 DECISIONS.md #2
- **商业化合规风险:用户认知** — 运营主体境外化、管理员非高风险法域、不存真实身份信息,详见 DECISIONS.md #3

## 已部署配置文件

- ✅ `CLAUDE.md` — 项目身份 + 技术栈 + 构建测试 + 约定
- ✅ `GEMINI.md` — Antigravity 通用规范
- ✅ `AGENTS.md` — Codex 项目规则
- ✅ `NOTICE.md` — AGPL 合规致谢
- ✅ `.gitignore` — 扩展了 operator secrets / generated / private
- ✅ `.claude/settings.json` — 允许开发常用命令,禁止破坏性操作
- ✅ `.agents/rules/python.md` — Python 编码规范
- ✅ `.agents/rules/xray-config.md` — Xray/Reality 配置硬指标
- ✅ `.agents/rules/security.md`(always 激活)— 安全基线
- ✅ `.agents/skills/sni-selector/SKILL.md`
- ✅ `.agents/skills/reality-config-audit/SKILL.md`
- ✅ `.agents/skills/agpl-compliance/SKILL.md`
- ✅ `.agents/skills/{accessibility,design-system,i18n,release,ux}-*/SKILL.md`(上游前置 5 个)

## 未解决问题

- TOP 5 紧急修复(见 AUDIT.md):
  1. P0 计费系统(5-7 周)
  2. P0 JWT Secret 外置到 .env(2 天)
  3. P0 Admin 登录速率限制(1-2 天)
  4. P1 审计日志系统(3-4 天)
  5. P1 N+1 + Task 异步化(2-3 天)
- 依赖管理:Marzneshin 当前 v2share 是 0.1.0b31(beta),风险;需评估替代

## 竞品关键发现

- Hiddify-Manager(8.7k stars)有原生 IP 限制 + Telegram Bot + CF Tunnel 集成 → 可偷学
- V2IpLimit / miplimiter / luIP 不兼容 Marzneshin(API 不同),需要改造或自研
- Marzneshin 的真实护城河:panel+marznode 天然多节点 + TS 全栈
- 详见 COMPETITORS.md

## 🔀 分支状态

- `main` — 当前唯一分支,包含 Round 0 初始 commit(`ca4735e`)
- 计划创建:`feat/round-1-*` 系列(见 ROADMAP 第一轮)

## 📅 最后同步确认

**轮次 #0**,确认读取了:
- `compass_artifact_wf-*.md`(Reality 2026 加固清单)
- Marzneshin upstream 核心文件(main.py, requirements.txt, Dockerfile, docker-compose.yml, makefile, pyproject.toml, README.md)
- `app/`、`dashboard/`、`tests/`、`docs/`、`tools/` 目录结构
- 所有自生成配置文件(CLAUDE/GEMINI/AGENTS/rules/skills)

## 💭 最新想法

- "老项目 fork 基底的选择"比后续加功能更重要,这次差点选错(user 质疑才换)
- 上游 test 覆盖率 1/10 意味着我们接下来每改一处代码都有引入回归的风险,**建立 CI + 基础测试 fixture 是 Round 1 必做项,优先级高于新功能**
- 商业化合规提醒已做,但技术 CTO 应当记住:这个项目能走多远取决于运营方的法律合规,不是我们的技术
