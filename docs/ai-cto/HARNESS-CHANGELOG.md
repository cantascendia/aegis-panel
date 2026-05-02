# Harness Changelog

> 本文件记录 aegis-panel AI agent harness(CLAUDE.md / settings.json / commands / agents / skills / rules / memory)的所有变更。
> 倒序:最新在上。
> 每次 PR 修改 `.claude/*` / `.agents/*` / `docs/ai-cto/{CONSTITUTION,STATUS,LESSONS,DECISIONS,SESSIONS,ROADMAP}.md` 必须在此追一行。
> 配套铁律 #12(Eval Gate)+ harness audit(`/cto-harness-audit`)。

---

## 2026-05-02 — Wave-9 R3: enforce switch + SSOT + recovery hardening (健康分 95 → **99**)

**8 PR 集中收口**(自上次 wave-3..9 sync 之后):

| PR | 主题 | 影响维度 |
|---|---|---|
| #187 | chore(skills): double-location sync | 原则 3 ⚠️→✅ |
| #188 | docs(ai-cto): HARNESS-CHANGELOG wave-3..9 | HARNESS-CHANGELOG 维护 |
| #189 | docs(governance): planner/generator agents + trc20 regression | 原则 7 ⚠️→✅ |
| #190 | docs(lessons): L-039/040/041 wave-9 沉淀 | LESSONS 完整 |
| #191 | fix(deploy): aegis-upgrade.sh multi-path scan (L-040) | 原则 6 强化 |
| #192 | fix(tests): marznode-smoke T6 sync | CI 信噪比(红→绿)|
| #193 | test(deploy): L-041 AEGIS_VERSION pin regression guards | 原则 6 强化 |
| #194 | chore(scripts): SSOT path-detect.sh (L-040 follow-up #1) | 原则 6 强化 + DRY |
| #195 | feat(ops): staging-smoke cutover dry-run (L-040 防线 #2) | 原则 8 强化 |
| #196 | **ci(eval-gate): advisory → enforce(铁律 #12 auto-enforced)** | 原则 8 飞跃 |
| #197 | docs(lessons): L-042 advisory → enforce 提前 11 天经验 | LESSONS 沉淀 |
| #198 | docs(evals): capability/001 codex cross-review saves prod | Eval 集 capability 充实 |

**Harness 关键变化**:
- ➕ `.claude/agents/`:6 个齐(spec-planner / code-generator / eval-runner / harness-auditor / vibe-checker / reliability-auditor)
- ➕ `scripts/lib/path-detect.sh` SSOT(install.sh + aegis-upgrade.sh 共享)
- ➕ `evals/regression/`:4 → 6 yaml(eval-gate-enforce + trc20 roundtrip)
- ➕ `evals/capability/`:0 → 1 yaml(codex cross-review saves prod)
- 🔄 `.github/workflows/eval-gate.yml`:advisory → **ENFORCE 模式 active**(2026-05-02,提前 11 天切)
- 🔄 skills 双位置同步:`.agents/skills/` 9 ↔ `.claude/skills/` 8(codex-bridge agents-only 白名单)

**Audit re-run #3 (2026-05-02 wave-9 R3)**:
- 总分:**95 → 99 / 100**(+4)
- 原则 3 (Self-contained):⚠️→✅(+1)
- 原则 7 (Multi-Agent Separation):⚠️→✅(+2)
- 原则 8 (Validation Gates):✅→✅✅(+1,enforce + regression 集扩到 6)
- 持平:原则 1/2/4/5/6
- HARNESS-CHANGELOG: 13/15 → 15/15(本 entry 后达上限)
- Eval 集: 15/15(golden 5 + regression 6 + capability 1)

**剩余缺口 (99 → 100)**:
- P5 **CONSTITUTION SEALED**(用户 + senior 双签)— DRAFT 5 天,唯一硬阻塞 +1 分

**§48 Codex 累计救生产 P-flag**(本批次):**11 个真 bug 在 ship 前抓**
- 2 P1:PG silent downgrade(#191)/ RETURN trap premature(#195)
- 8 P2:引号处理 / substring 太宽 / lib not co-installed / 等
- 1 P3:golden-fail 跳过 footer(#196)

**Production state (2026-05-02 wave-9 R3)**:
- nilou.cc:image v0.4.1,panel healthy,Deploy Smoke ✅ green
- TRC20 invoice id=1 awaiting_payment(等 user 充值 USDT round-trip)
- 5 active users(4 admin + 1 trial)
- Harness audit:**99/100**,产品就绪 9.9/10

**下一步建议**:
- ✅ 边际收益已饱和,不再开新 harness PR
- ⏳ 进入 product/launch 优先期(等 user 决策驱动 — A.2 round-trip / B VPS / C 微信名单)
- 🎯 CONSTITUTION SEAL PR(用户 + senior 双签 = +1 → 100/100)

---

## 2026-05-02 — Wave-3 ~ Wave-9 sync (production cutover + hot-fix + 健康分 94 → 95)

**Wave 总览**(详见 git log + STATUS.md):
- wave-3 ~ wave-7:audit-log S-AL session 全交付(AL.1-AL.4 19 PR + L-032 mTLS 三段式 SPEC/PLAN/TASKS + 4 客户文档)
- wave-8:运维基建(aegis-watchdog / aegis-staging-smoke / aegis-upgrade / aegis-create-trial-batch + Quick Plans dashboard)
- wave-9:production cutover (v0.4.0 → v0.4.1) + TRC20 hot-fix (PR #186 commit f2b46737) + launch 三件套(PITCH-CARDS / VPS-PROVIDER / HOW-TO-RECRUIT-FROM-WECHAT)

**Harness 关键变化**:
- ➕ `.claude/agents/`:eval-runner / harness-auditor / vibe-checker → +`reliability-auditor`(4 个)
- ➕ `.claude/commands/`:cto-canary / cto-replay / cto-cross-review / cto-relink-all(20 个)
- ➕ `evals/regression/`:0 → 4 yaml(L-018 / L-015 / eval-gate-trigger / migration-rollback)
- ➕ `.github/workflows/eval-gate.yml`:advisory mode active(2 周观察期 ~ 2026-05-13)
- ⏳ skills 双位置仍未同步(`.agents/skills/` 8 vs `.claude/skills/` 8,集合不等,差 6 个互补 — 见 PR #N skills double-location sync)

**Audit re-run (2026-05-02)**:
- 总分:**94 → 95 / 100**(+1)
- 进步:原则 6 (Fail-Fast + Recovery) ⚠️→✅ — TRC20 hot-fix 单会话内闭环验证 recovery path
- 持平:原则 3 (Self-contained skills 双位置)、原则 7 (planner/generator 显式分层缺)
- 下次提升点:CONSTITUTION SEALED (+1)、planner/generator agent 文件 (+2)、eval-gate enforce (+1)

**Production state (2026-05-02)**:
- nilou.cc:image v0.4.1(SHA da37f2b42cce),panel healthy
- TRC20 invoice id=1 awaiting_payment(operator self-test pending)
- 5 active users(4 admin + 1 trial)

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
