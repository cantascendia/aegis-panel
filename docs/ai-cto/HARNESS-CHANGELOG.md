# Harness Changelog

> 本文件记录 aegis-panel AI agent harness(CLAUDE.md / settings.json / commands / agents / skills / rules / memory)的所有变更。
> 倒序:最新在上。
> 每次 PR 修改 `.claude/*` / `.agents/*` / `docs/ai-cto/{CONSTITUTION,STATUS,LESSONS,DECISIONS,SESSIONS,ROADMAP}.md` 必须在此追一行。
> 配套铁律 #12(Eval Gate)+ harness audit(`/cto-harness-audit`)。

---

## 2026-04-29 — Re-audit post wave-2: 78 → 94 (+16)

**Audit 报告**(`/cto-harness-audit` 第二跑):

- 总分:**94 / 100**(原 78 → +16)
- 三大缺口全闭环:
  - ✅ `evals/` 5 P0 trajectory 落地(PR #109 `06db847`)→ 铁律 #12 可执行
  - ✅ `HARNESS-CHANGELOG.md` 创建(PR #110 `5e718d8`)
  - ✅ `CONSTITUTION.md` 创建(PR #110 `5e718d8`)— DRAFT 状态,等用户 + senior 双签
- 八条原则评分变化:
  - 原则 8 (Durable State + Validation Gates):⚠️ → ✅(+5 分)
  - 原则 3 (Self-contained):⚠️ → ⚠️ → 后续 chore PR 同步 .claude/skills/ 缺 3 个后转 ✅
- 三 Agent 模式: 18/20 (planner/generator 显式分层缺,CI eval-runner 调度缺)
- 反模式规避: 9/10 → 10/10(Eval Gaming 防线启动)

**残余 Top-3 ROI**:

1. ⚠️ `.claude/skills/` 缺 3 个(agpl-compliance / reality-config-audit / sni-selector)→ in-flight chore PR
2. ⚠️ `.github/workflows/eval-gate.yml` CI 自动调度缺 → 待 SPEC + 双签(forbidden 路径)
3. ⚠️ CONSTITUTION DRAFT → SEALED 等用户决策

**预计上述 3 项落地后:94 → 99+**。

**本会话 PR 全清单**(2026-04-28 ~ 04-29 wave-2 + wave-3):

- PR #99 R.4 Reality dashboard(差异化 #3 前端闭环)
- PR #100 / #106 S-O batch refresh ×2
- PR #101 SPEC-audit-log + SPEC-rbac skeletons
- PR #105 chore: handbook path fix(ai-guidebook → ai-playbook)
- PR #107 chore: cto-* commands sync
- PR #108 chore: bulk playbook sync(agents + skills + rules + output-styles + statusline)
- PR #109 chore: evals/ init
- PR #110 docs: CONSTITUTION + HARNESS-CHANGELOG

**新增 issue**: #102 R.4 follow-up tests / #103 audit-log TBDs / #104 RBAC TBDs(各自带决策清单)

---

## 2026-04-28 — Init: harness audit 78/100,三大缺口启动补齐

**Audit 报告**(`/cto-harness-audit` 跑通):

- 总分:**78 / 100**
- 八条原则 33/40(原则 1/2/4/5/7 ✅,原则 3/6/8 ⚠️)
- 三 Agent 模式 18/20(planner / generator / evaluator / validator 齐,缺 CI 集成)
- HARNESS-CHANGELOG: 0/15 → **本文件创建后 +15**
- Eval 集: 5/15 → **`evals/` init PR 后 +10 = 15/15**
- 反模式规避: 9/10
- 关键缺口:
  - ❌ `evals/` 不存在 → 铁律 #12 不可执行 → **本批次 PR `chore(evals): init` 修复**
  - ❌ `HARNESS-CHANGELOG.md` 缺失 → **本 PR 修复**
  - ❌ `CONSTITUTION.md` 缺失(`.claude/settings.json:26` SessionStart hook 引用但文件不存在,静默 noop) → **本 PR 修复**
  - ⚠️ `.agents/skills/`(9 个)与 `.claude/skills/`(5 个)双位置不同步 → 后续 PR
  - ⚠️ `cto-vibe-check` / `cto-review` / `cto-audit` 三命令边界部分重叠 → 后续 ASCII 图区分

**Top-5 立即可执行**(每项 ≤ 30 分钟):

1. ✅ 创建 `evals/` 骨架(本批次 PR)→ +10 分
2. ✅ 创建 `HARNESS-CHANGELOG.md`(本 PR)→ +15 分
3. ✅ 创建 `CONSTITUTION.md`(本 PR)→ +5 分
4. ⏳ 同步 skills 双位置 → 后续 PR(+3 分)
5. ⏳ commands 边界 ASCII 图 → 后续 PR(+2 分)

**预计上述 5 项完成后:78 → 92+**

---

## 2026-04-28 — chore(commands): sync cto-* commands from playbook

PR #107 — playbook §33/§34/§35/§37 新增章节同步:

- ➕ `.claude/commands/cto-constitution.md`(§37)
- ➕ `.claude/commands/cto-eval.md`(§35)
- ➕ `.claude/commands/cto-harness-audit.md`(§34)
- ➕ `.claude/commands/cto-vibe-check.md`(§33)
- 🔄 `.claude/commands/cto-spec.md`(三段式 specify / plan / tasks 升级,对齐 GitHub Spec Kit)

**理由**:playbook 升级到 §37,本仓库 commands 落后,新会话无法触发新章节工作流。
**影响**:`/cto-constitution` / `/cto-eval` / `/cto-harness-audit` / `/cto-vibe-check` 四个新命令可用;`/cto-spec` 流程升级为三段式。

---

## 2026-04-28 — chore(harness): bulk sync from playbook(本批次同期 chore PR)

PR #NNN(待 PR 编号确定后回补)— 后续 playbook 同步:

- ➕ `.claude/agents/`(三 Agent 模式: eval-runner / harness-auditor / vibe-checker)
- ➕ `.claude/output-styles/`
- ➕ `.claude/skills/`
- ➕ `.claude/statusline.sh`
- ➕ `.claude/commands/cto-image.md`(§26.5 视觉生成命令)
- ➕ `.claude/commands/cto-link.md`(§29.8 跨机器路径探测)
- 🔄 9 个 cto-* commands description 加章节号引用

**理由**:本仓库 sub-agent / skill / output-style 全缺,新会话能力大打折扣;cto-link 修复多机器手册路径硬编码痛点。
**影响**:三 Agent 模式可在 SDK / hooks 中触发;`/cto-image` / `/cto-link` 启用。

---

## 历史(隐式记录,自项目 init 至 2026-04-28)

按 commit history 隐式追溯,具体见 `git log -- .claude/ .agents/ CLAUDE.md docs/ai-cto/`:

- 2026-04-21 ~ 2026-04-28:CLAUDE.md / `.agents/rules/` / `.agents/skills/` / `docs/ai-cto/*` 初版与多轮迭代
- 关键里程碑(PR 编号):
  - #1(脚手架 + 初版 CLAUDE.md)
  - #7(slowapi limiter,L-010 同期诞生)
  - #34(`app/db/extra_models.py` aggregator,L-014)
  - #52(SESSIONS.md 铁规则 #7 worktree 隔离,L-018)
  - #88(`deploy/compliance/agpl-selfcheck.sh`,D-017)
  - #99(R.4 dashboard Reality 审计页)
  - #101(SPEC-audit-log + SPEC-rbac 双骨架,v0.3 scope)
  - #105(CLAUDE.md 手册路径修正 ai-guidebook → ai-playbook)
  - #106(late-7 wave-2 batch:R.4 + SPEC #101 + tracking issues)
  - #107(本批次:cto-* commands sync from playbook §33/§34/§35/§37)

> 自本日(2026-04-28)起,所有 harness 改动**必须**在此文件追加,**不再依赖** `git log` 隐式追溯。

---

## 模板(下次追加格式)

```markdown
## YYYY-MM-DD — <一句话标题>

PR #NNN — <简介>:
- ➕ <新增>
- 🔄 <修改>
- ❌ <删除>

**理由**:<为什么改>
**影响**:<对哪些行为有影响>
```

完整定义见手册 §34 Harness 设计自审 + §35 Eval-Driven Development。
