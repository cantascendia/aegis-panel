# 决策记录(DECISIONS)

> 格式:每条决策 = (编号 + 日期 + 决策 + Why + How to apply + 推翻条件)
> 倒序排列,最新在上

---

## D-004 | 2026-04-21 | Round 0 完成,Round 1 聚焦 P0 安全 + 基础测试设施

**决策**: Round 1 **不做新功能**,只做:
1. P0 安全修复(JWT secret 外置 + Admin 速率限制 + CORS 收紧 + JWT 时效收紧)
2. PostgreSQL 切换 + 迁移
3. 测试基础设施(pytest fixture + CI + 至少关键路由端点测试)
4. 目录骨架(`hardening/` + `deploy/` + `ops/` 创建 + README)

**Why**: AUDIT.md 显示安全 3/10、测试 1/10。在这两块没达标前做任何新功能都是在**不可审计的沙滩上盖楼**,每次上线都会带安全债务和回归风险。>200 用户商业场景容不得这种脆弱。

**How to apply**: Round 1 所有任务必须属于以上 4 类。新功能(SNI 选型器、计费等)推到 Round 2+。

**推翻条件**: 用户明确要求优先做 SNI 选型器或计费 demo(商业 deadline 驱动),可调整;但至少 JWT 外置和速率限制这两条必须先做。

---

## D-003 | 2026-04-21 | 商业化机场法律合规 —— 用户已知,CTO 留痕

**决策**: CTO 对用户明确提示了运营付费机场(>200 用户)在中国大陆/伊朗/俄罗斯的刑事风险,用户接受风险并继续。CTO 不再阻止,但在项目多处留下合规警示。

**Why**:
- 2023-2025 年有多起"运营翻墙收费"刑事判例
- CTO 的职责是提示和加固防御,不是代替用户做价值判断
- 留痕后若未来出问题,历史记录清晰

**How to apply**:
- `NOTICE.md` 和 `.agents/rules/security.md` "合规红线"段落已写入
- 建议(非强制):
  - 运营主体 / 支付通道 / 域名 / VPS 账单全部境外化且隔离
  - 中国大陆 IP 黑名单屏蔽
  - 管理面板访问走 CF Tunnel + Access
  - 管理员居住地非高风险司法管辖区
  - 不保留用户真实身份信息;支付走加密货币或境外 SaaS
- 任何涉及"收款"、"实名制"、"电话验证"的功能请求必须再次提醒用户合规风险

**推翻条件**: 用户明确说"只在合规法域运营 + 仅面向持牌用户",此限制可放宽。

---

## D-002 | 2026-04-21 | AGPL-3.0 合规策略 —— 保留版权 + 独立仓库 + 源码披露入口

**决策**: 采用 "hard fork + 独立仓库 + 致谢保留" 策略。

- ✅ `git clone` 上游后 `rm -rf .git && git init` 成为独立仓库,不显示 "forked from"
- ✅ **保留**原版 `LICENSE`(AGPL-3.0)和所有源文件版权头
- ✅ 新增 `NOTICE.md` 致谢 upstream 并标注 fork commit SHA
- ✅ 自研新模块(`hardening/`、`deploy/`、`ops/`)可选独立 license(Apache-2.0 / MIT,与 AGPL 兼容)
- ❌ **禁止**闭源商业化运营;必须对用户提供源码获取入口(面板 footer 或 `/source` 路由)

**Why**:
- 用户希望"不显示 upstream 来源"(不想让其他运营方看到 fork 关系)
- Hard fork + 独立 git init 能满足这个需求(不是 GitHub fork,也不显示 forked 标记)
- **但** AGPL-3.0 不允许隐藏 upstream 版权或不对用户披露源码,这两条必须坚守
- 违反 AGPL 会导致法律风险(强制开源 / 撤销使用权),这是项目生存问题

**How to apply**:
- 所有 commit 中,涉及 upstream 代码的修改必须保留原文件头 Copyright 行
- 上线前必须跑 `.agents/skills/agpl-compliance/SKILL.md` 定义的完整检查
- 面板必须在合理位置(footer、关于页、`/source` API)提供公开的 Git 仓库链接
- 自研模块若要用非 AGPL license,在该模块目录下独立声明 `LICENSE`

**推翻条件**: 只要 upstream license 仍是 AGPL-3.0,不可推翻。若未来 upstream 换 license,重新评估。

---

## D-001 | 2026-04-21 | Fork 基底:Marzneshin(不是 Marzban)

**决策**: 放弃已完成的 Marzban fork(commit `d3cf9fa`,已 `rm -rf .git` 销毁),改从 Marzneshin clone 重做。

**Why**:
- Marzban(Gozargah/Marzban)**最后活跃 2025-01-09**,15 个月无提交,官方团队已迁到 Marzneshin
- Marzneshin 是官方继任,**最近 release v0.7.4 @ 2025-10-02**,仍在活跃维护
- Marzneshin **原生多节点弹性**(control/data plane 分离 + gRPC 到 marznode),与 >200 用户 + 多节点目标完全对齐
- Marzneshin 前端是 **TypeScript + Vite + React + shadcn/ui**(比 Marzban 的 Vue2 现代);有 tests/ 骨架
- 代价:Marzban 生态的 V2IpLimit / luIP / miplimiter 等 IP 限制外挂**不兼容 Marzneshin**,我们需要改造或自研(详见 COMPETITORS.md 建议 3)

**How to apply**:
- 所有以后对"上游"的引用默认指 Marzneshin
- 不要 copy-paste Marzban 的 issue/PR 讨论作为 Marzneshin 的指导
- 季度性评估 `marzneshin/marzneshin` upstream 变更,策略性同步(不盲合)

**推翻条件**:
- Marzneshin 停更超过 12 个月 → 评估再 fork 或换基底
- 出现更优秀的活跃替代品(如 Remnawave 进入多节点阶段且生态起来)→ 重新评估

---

## 模板(新决策按此格式追加到顶部)

```
## D-NNN | YYYY-MM-DD | <一句话决策>

**决策**: <详细描述>

**Why**: <为什么这样选,而不是其他方案>

**How to apply**: <具体如何落地,哪些文件/流程受影响>

**推翻条件**: <什么情况下这条决策失效,要重新讨论>

---
```
