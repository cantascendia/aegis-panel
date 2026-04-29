---
name: sub-agent-worktree
description: 并行 sub-agent 临时 worktree 模式硬规则(L-018 / L-026 / L-027 升级)
activation: always
---

# Sub-agent 临时 worktree 模式

并行 sub-agent 跑 git-heavy 任务(branch / commit / push / PR open)时,**每个 sub-agent 必须有自己独立的 git worktree**。本规则把 LESSONS L-027 升级为硬规则,经 10 波 / 25+ sub-agent / 25+ 临时 worktree 全程 0 撞车验证。

## 何时使用

| 场景 | 用临时 worktree? |
|---|---|
| 主会话单线写代码 | ❌ 不用,直接在主 repo |
| 主会话委派 1 个 sub-agent 做 read-only 调研 | ❌ 不用 |
| 主会话委派 1 个 sub-agent 做 commit + push + PR | ✅ 必须 |
| 主会话同波并行 ≥2 个 sub-agent,任一会 git mutate | ✅ 必须每个独立 |
| 跨多日的 fixed session(S-B / S-D / S-X 等)| 用 SESSIONS.md 铁规则 #7 的 fixed worktree |

判定原则:**git mutate(branch / add / commit / push / PR open)= 必须独立 worktree**。

## 命名规范

| 类型 | 路径 | 生命周期 |
|---|---|---|
| 主 repo | `C:/projects/aegis-panel` | 永久 |
| Fixed session worktree | `C:/projects/aegis-{B,D,F,O,R,X}` | 跨多日,SESSIONS.md 登记 |
| 临时 sub-agent worktree | `C:/projects/aegis-tmp-<slug>` | 单波,merge 后立即清理 |

`<slug>` 用 kebab-case 描述任务,例如 `aegis-tmp-governance` / `aegis-tmp-rbac-spec` / `aegis-tmp-r4-tests`。**不复用同名 slug**,即便上一波已 cleanup —— 用 `aegis-tmp-governance-2` 区分。

## 流程(主会话角度)

### 1. 主会话先建 worktree + branch

```bash
# 在主 repo 执行
git fetch origin main
git worktree add -b docs/governance-l027 C:/projects/aegis-tmp-governance origin/main
```

### 2. Sub-agent prompt 硬编码 cd

每个 sub-agent prompt 必须包含:

- worktree 绝对路径(`C:\projects\aegis-tmp-<slug>`)
- branch 名(已建好,不要 sub-agent 自己 checkout)
- base commit SHA(让 sub-agent 起手 `git log -1` 自检)
- 明确禁止 cd 到主 repo
- 任务边界(改哪些文件,不能动哪些)

### 3. Sub-agent 自完成 PR open

Sub-agent 在自己 worktree 内 `git add` / `git commit` / `git push -u origin <branch>` / `gh pr create`,返回 PR URL + commit SHA + 文件变更摘要给主会话。

### 4. 主会话 merge + cleanup

- 主会话审 PR diff(读 sub-agent 改动)
- merge PR(squash 或 merge commit 按 git-conventions.md)
- `git worktree remove C:/projects/aegis-tmp-<slug>`
- `git branch -d <branch>`(本地)+ `git push origin --delete <branch>`(远端,如未自动)

## 并发上限

**每波 ≤ 5 个 sub-agent**。

理由:

- 主会话 token 暴涨:每个 sub-agent 启动 prompt + 返回报告都进主会话上下文,>5 之后主 session context 难审,易出 hallucination
- 1M context 也撑不住:5 个 sub-agent × 平均 30k token 报告 = 150k,加上主会话本身工作上下文,逼近 caching window 边界
- 串行 review 收敛:超过 5 个 PR 同时开,主会话 review 排队 > 实际并行收益

如果一波超过 5 个,**拆成多波**(wave-1 / wave-2 / wave-3),每波等上一波 PR merge + cleanup 完再发下一波。

## SESSIONS.md 铁规则 #7 关系

两条规则**互补不冲突**:

| 维度 | SESSIONS.md 铁规则 #7 | 本规则 |
|---|---|---|
| 对象 | 跨多日的 **fixed session**(人 + Claude 长期协作) | 单波的**临时 sub-agent**(主会话委派) |
| 路径 | `aegis-{B,D,F,O,R,X}`(固定字母) | `aegis-tmp-<slug>`(任务相关) |
| 生命周期 | 数日至数周,SESSIONS.md 活跃会话表登记 | 单波,merge 后立即 `git worktree remove` |
| 登记 | SESSIONS.md 必须 | 不需登记(短命) |
| 谁起的 | 用户跑 `tools/setup-session-worktrees.sh` | 主会话 `git worktree add` |

**判定**:如果是用户开新 terminal 起一个会跑很多天的 session,走铁规则 #7。如果是主会话本波内派发的并行子任务,走本规则。

## 反模式

❌ Sub-agent 在主 repo `C:/projects/aegis-panel` 跑 `git checkout -b ...`(撞主会话 working tree)
❌ 同一波两个 sub-agent 共用同一个 `aegis-tmp-<slug>`(branch / stash 撞车)
❌ Merge 后忘了 `git worktree remove`(磁盘膨胀 + 下波同名 slug 报错)
❌ Sub-agent prompt 让 agent "自己挑路径"(不可复现,主会话不知道哪去 cleanup)
❌ 一波 7+ sub-agent 一起发(超并发上限)

## 来源

- **L-018**(原撞车事故): 多 session 在同 working tree 跑导致 branch / stash / PR 撞车 —— 提出**独立 worktree** 方案
- **L-026**(候选): sub-agent 临时 worktree 模式首次系统使用,7 波验证稳定
- **L-027**(确认升级): 10 波 / 25+ sub-agent 累计 0 撞车,模式成熟,正式转硬规则

## 关联文件

- `docs/ai-cto/SESSIONS.md` — 铁规则 #7,跨日 fixed session worktree
- `.agents/rules/git-conventions.md` — 分支命名 / commit 规范 / merge 策略
- `tools/setup-session-worktrees.sh` — fixed session worktree 一键初始化(铁规则 #7 配套)
- `docs/ai-cto/LESSONS.md` — L-018 / L-026 / L-027 原文

完整背景见 `docs/ai-cto/LESSONS.md` 对应条目。
