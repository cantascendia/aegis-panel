# 竞品分析(COMPETITORS)

> 最后更新:**2026-04-26**(quarterly refresh,首次自第零轮起)
> 数据来源:GitHub API 实抓(`gh api repos/<owner>/<repo>` + `releases`)+ 我们已落地代码状态
>
> **下次刷新**:2026-07-26(每季度,与 `UPSTREAM-SYNC-REPORT-*.md` 同步进行)

---

## 综合矩阵

新增 **Aegis(我们)** 列,把"我们基底 Marzneshin"和"我们 fork 后的真实状态"分开 —— 这样能清晰看到我们 6 个月在 Marzneshin 之上加了什么。

| 维度 | **Aegis(我们)** | Marzneshin(我们基底) | Hiddify-Manager | 3X-UI | Remnawave | S-UI |
|---|---|---|---|---|---|---|
| Stars | n/a(私仓) | **677**(几乎不动) | **8745**(+45) | **35.1k**(+450) | **3775**(+75) | **8554**(+54) |
| 最近 release | 71 个内部 PR,无对外 release | v0.7.4 @ 2025-07-12 | **v12.2.0b1 @ 2026-03-29** | **v2.9.2 @ 2026-04-22** | **2.7.4 @ 2026-03-30** | v1.4.1 @ 2026-03-29 |
| 最后 push | 2026-04-26(本会话) | **2025-10-04**(7 个月前)| 2026-03-29 | **2026-04-24** | 2026-04-23 | 2026-04-01 |
| 维护状态 | 🟢 活跃 | **⚫ dormant** | 🟢 活跃 + 加速 | 🟢 最活跃 | 🟢 daily-release 节奏 | 🟢 活跃 |
| 技术栈 | Python 3.12 + TS(同 Marzneshin)+ 自研 hardening / ops | Python + TS | Python + Shell | Go + HTML | TS (NestJS) | Go |
| 多节点原生 | ✅ 继承 panel+marznode | ✅ panel+marznode | ✅ | ❌ | ❌ | ❌ |
| 测试覆盖 | **~233 后端测试 + CI 全套**(L-022 / D-009)| ~0% | ~0% | ~0% | ~0% | ~0% |
| 商业化(计费/订阅) | **🟡 进行中**:A.1 数据面 + Admin UI ✅,A.2.2 webhook ✅,A.5 scheduler ⏳,真接码商 ⏳ | ❌ | ⚠️ 用户限制管理但无支付 | ❌ | ❌ | ❌(仅订阅链接) |
| 原生 IP 限制 | **✅ MVP**(PR #24,policy 表 + dashboard UI) | ❌ | ✅ | ❌ | ❌ | ❌ |
| Reality/SNI 选型 | **✅ 全链路闭环**(PR #13/16/18/66 — CLI / REST / UI / runbook) | ❌ | 半(多协议混用) | ❌ | ❌ | ✅(sing-box 原生) |
| CF Tunnel 集成 | ⏳ SPEC-deploy.md D.4 已就位,代码未起 | ❌ | ✅ | ❌ | ❌ | ❌ |
| Telegram Bot | ✅ 继承 aiogram + iplimit 告警拓展 | 已有(aiogram) | ✅ 成熟 | ❌ | ❌ | ❌ |
| i18n | ✅ 继承 6 种 | ✅ 6 种 | ✅ 多种 | 部分 | 部分 | ✅ |
| 反代信任 X-Forwarded-For | **✅ per-feature CIDR env**(D-012,billing webhook 已用) | ❌ | ❌ | ❌ | ❌ | ❌ |

**关键洞察(2026-04-26 复评后修正)**:

1. **基底 Marzneshin 实质 dormant**(详见 [`UPSTREAM-SYNC-REPORT-2026-04-26.md`](./UPSTREAM-SYNC-REPORT-2026-04-26.md))。其他 4 个竞品全部活跃,3X-UI 昨天还在发版。**我们事实上已是 Marzneshin lineage 的承接者**
2. **测试覆盖 0% → 233 后端测试**:首轮观察的"整个生态不重视测试工程"仍成立 —— 我们是唯一有 CI 全套门禁 + alembic stepped upgrade + PG16 matrix + pip-audit 的项目
3. **差异化 #1(SNI 智能选型器)+ #2(IP 限制)已 MVP 落地** —— 6 个月前是 ⏳,现在是 ✅
4. **商业化是当前唯一未完成的差异化大块**(A.5 scheduler / 真接码商)。其他 4 个竞品**都没有**完整支付链路 —— 这仍是最宽护城河,但我们也没合上

## 自第零轮(2026-04-21)以来的 5 天 + 6 个月里发生了什么

| 我们(Aegis) | Marzneshin 基底 | 其他竞品 |
|---|---|---|
| 71 个 PR 合入 | 2 个 hotfix(都在 fork 当天) | 3X-UI 12 个 release(v2.7.x → v2.9.x);Hiddify v12.0 → v12.2.0b1;Remnawave 2.7.0 → 2.7.4(daily) |
| Round 1 leftover 全清 | 长期 stale | — |
| 安全 / 测试 / CI 三档质量门禁 | 无变化 | 无变化(仍然 0%) |
| SNI 选型器全链路闭环(差异化 #1) | — | — |
| IP 限制 MVP(差异化 #2) | — | Hiddify 一直有但实现糙 |
| 计费 A.1 + A.2.2 落地 | — | 仍无人做 |

---

## 1. Hiddify-Manager(8.7k stars)—— 最值得偷学

**定位**: 反审查多协议集成平台(支持 20+ 协议),面向**最广泛用户**。

**技术栈**: Python 47.6% + Shell 25.7% + Xray/Sing-box 双核

**核心能力**:
- ✅ 原生 IP 限制(用户时长、流量、IP 并发)— 在 `app/roles/shared_limit.py`
- ✅ Telegram Bot 远程管理(完整权限框架)
- ✅ 自动备份、CF Tunnel 集成
- ✅ 多域名、多语言
- ⚠️ 体量大而全,自定义复杂

**可偷学(具体文件级)**:
- `app/roles/shared_limit.py` — IP 限制算法,可移植到我们 `hardening/iplimit/`
- `app/telegram/` — Bot 权限管理框架(Marzneshin 已有 aiogram 基础但功能弱)
- CF Tunnel 集成脚本 → `deploy/cloudflare/`

**劣势(相对 Marzneshin)**:多节点通过"脚本复制"实现,不如 Marzneshin 的 control/data plane 分离干净。

---

## 2. 3X-UI(34.7k stars)—— UI/UX 参考

**定位**: 轻量级 Xray 面板,Go 实现,个人用户首选

**技术栈**: Go 36.7% + HTML 38.5%

**核心能力**:
- ✅ 极简 UI,低资源占用(Go 单文件部署)
- ✅ 文档齐全,新手门槛低
- ❌ **明确声明"仅个人用途"**,无商业化
- ❌ 无多节点,无 IP 限制

**可偷学**:
- `app/web/html/` 前端交互模式 — 虽然技术栈不同,但 UX 设计哲学(一屏内查看所有节点 + 用户)值得借鉴

**劣势**:定位不同,无法直接对标商业化机场。

---

## 3. Remnawave(3.7k stars,v2.7.4)—— 新兴 TS/NestJS

**定位**: TypeScript 全栈 NestJS,专注易用性和开发者体验

**技术栈**: TypeScript 50.4% + CSS 38.5%

**核心能力**:
- ✅ 现代 NestJS 架构(DI + decorator)
- ✅ UI 设计较精致
- ❌ 无多节点,无 IP 限制,无商业化

**可偷学**:
- NestJS 架构模式(如果未来考虑 Node.js 重构,可参考)

**劣势**:功能面小,生态不成熟;但增长速度值得关注。

---

## 4. S-UI(8.5k stars)—— Sing-box 生态专属

**定位**: Sing-box 面板,Reality 原生支持最强

**技术栈**: Go 82.4%

**核心能力**:
- ✅ Reality / Sing-box 原生深度集成
- ✅ 多协议路由
- ❌ 无多节点,无 IP 限制,无商业化

**可偷学**:
- Sing-box 集成框架 — 如果我们未来做 "XHTTP/Hysteria2 备用通道" 且决定集成 sing-box,可参考路由配置方案

**劣势**:绑定 sing-box 单一后端。

---

## 5. Marzban 生态工具兼容性(关键!)

这组是我们原计划要用的,但审核后发现大部分**不兼容 Marzneshin**。

### V2IpLimit(houshmand-2005/V2IpLimit)
- **作用**: IP 并发限制(基于 Xray access.log 解析)
- **依赖**: Marzban API(需要用户名密码登录 Marzban 面板)
- **兼容 Marzneshin**: ❌ **不兼容**。代码显式指向 Marzban API 路径
- **关键坑**: Xray 日志写到文件时不会 stdout,miplimiter 等工具无法读取
- **来源**: GitHub + Marzban Issue #672

### luIP-marzban / luIP(marzneshin/luIP)
- **状态**: 仓库 404(已删除或迁移)
- **推断**: Marzneshin 可能未集成官方 IP 限制工具,或官方放弃此方案

### miplimiter(amirgi73/miplimiter)
- **作用**: IP 限制(类似 V2IpLimit)
- **依赖**: Xray access.log 解析
- **配置陷阱**: `"log": { "access": "" }` 必须为空才能让 marzban 读 stdout
- **兼容 Marzneshin**: ❌ 同样依赖 Marzban API

### Xray 原生 `policy.levels` + 短 connIdle
- **作用**: 内置策略(connIdle 120 + handshake 2)
- **兼容性**: ✅ 与协议实现绑定,不依赖管理面板,Marzneshin 可用

---

## 三条核心建议

### 1. 立即从 Hiddify 偷学的具体功能(Round 2+)

从 Hiddify `app/roles/shared_limit.py` 和 `app/telegram/` 模块中移植:

- **IP 并发计数算法**(基于 Xray 连接日志) — 适配 Marzneshin 的 User/Service 模型
- **Telegram Bot 权限管理框架** — 扩展 Marzneshin 现有 aiogram 集成
- **估计工作量**: 2-3 个开发日

### 2. Marzneshin 相对竞品的真实护城河

- **Panel + Marznode 分离架构** — **唯一**天然支持多节点且保持架构优雅的开源方案(Hiddify 靠脚本复制,不如分离干净)
- **TypeScript 全栈潜力** — 允许高效前后端类型共享(大多数竞品 Python+HTML 割裂)
- **新兴 + 轻量** — 比 Hiddify "大而全" 更易定制商业特性

### 3. 防共享工具方案(重要)

基于 V2IpLimit / miplimiter 全部不兼容 Marzneshin 的事实:

- ❌ 不走"fork Marzban 外挂工具改 API"路线 —— 维护成本高,每次上游更新都要跟
- ✅ **短期(Round 2 后半)**: 在 `hardening/iplimit/` 自研一个**原生模块**,直接订阅 Xray stats API(Marznode 已暴露),按用户级计数;参考 Hiddify 算法
- ✅ **长期**: 把 IP 限制作为 Marzneshin 核心能力(类 Hiddify 做法),向上游提 PR(如果合入,减轻自己维护负担)

关键前置:解决 Xray 日志 stdout 问题(Marzban Issue #672 提到的配置)。

---

## 追踪坐标(每季度刷新)

| 项目 | 最后 release | 最后 push | 需要关注的新功能 |
|---|---|---|---|
| **Marzneshin**(我们基底)| v0.7.4 @ 2025-07-12 | 2025-10-04 | **dormant**;关注是否复活(commit count > 5 / 任何新 release)|
| **Hiddify-Manager** | v12.2.0b1 @ 2026-03-29 | 2026-03-29 | 多节点演进、原生计费、IP 限制算法演进 |
| **3X-UI** | **v2.9.2 @ 2026-04-22** | 2026-04-24 | Reality / sing-box 跟进、单节点商业化(若有)|
| **Remnawave** | 2.7.4 @ 2026-03-30 | 2026-04-23 | 是否加多节点(NestJS 架构能否原生支持)|
| **S-UI** | v1.4.1 @ 2026-03-29 | 2026-04-01 | Reality 抗封更新、sing-box 新协议适配 |

**数据刷新策略**:每季度(2026-07-26 / 10-26 / ...)跑:

```bash
gh api 'repos/<owner>/<repo>' --jq '.stargazers_count, .pushed_at, .archived'
gh api 'repos/<owner>/<repo>/releases?per_page=3' --jq '.[].tag_name + "  " + .[].published_at'
```

把上表数字 delta 写到本文件 §刷新历史(末尾),不删旧数据 — 保留纵向历史让我们看出谁加速 / 谁停摆。

## 刷新历史

### 2026-04-26(本次)

- 首次定期刷新
- **关键发现**:Marzneshin 基底实质 dormant(2 commit / 6 个月,见 UPSTREAM-SYNC-REPORT-2026-04-26.md);其他 4 个竞品全部活跃,3X-UI 最快(daily 节奏 + v2.9.x 系列)
- 我们在 6 个月里合 71 个 PR,差异化 #1 SNI 全链路闭环 + #2 IP 限制 MVP + 计费数据面 / Admin / A.2.2 webhook 落地
- **战略修订**:加 "Aegis(我们)" 列到矩阵首位,把"基底状态" 与 "我们状态" 区分(此前混在一列容易让读者误判我们已落地的差异化)
- 维护者(`khodedawsh`)dormancy 同时影响 Marzneshin + v2share 两个 repo(D-013 链接)

### 后续刷新模板

```
### YYYY-MM-DD

- delta 维度 1:
- delta 维度 2:
- 战略修订(如有):
```

---

**原始调研数据留痕**:
- Hiddify 代码引用: `app/roles/shared_limit.py`、`app/telegram/*` — 基于 WebFetch 到的 GitHub 仓库结构
- V2IpLimit Marzban 锁定:WebFetch 到的 `marzban_api.py` 源码 + Issue #672 讨论
- Marzneshin v2share 版本 0.1.0b31 (beta):`requirements.txt` 第 25 行(本地已确认)
