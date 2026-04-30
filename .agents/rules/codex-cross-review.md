---
name: codex-cross-review
description: §48 跨模型 review 硬规则(L-028 升级)— 业务路径 PR 必跑 + 修 P2 必二审
activation: always
---

# §48 Cross-Model Review 硬规则

任何业务路径(`scripts/business-paths.txt`)代码 PR 在 push 后**必须**触发 Codex 跨模型 review,无论 PR 看起来多简单。本规则把 LESSONS L-028 升级为硬规则,基于 wave-4 的 4 个 P2 真 bug 数据点(Codex 抓到 / Claude 自审会全漏)。

## Why(L-028 数据点)

Wave-4 单会话推进 audit-log v0.3 第一块,4 个代码 PR 跑 §48 cross-review,Codex(gpt-5.5)在 3 个 PR 中抓到 **4 个 P2 真 bug**:

| PR | Codex P2 | Claude 自审为什么漏 |
|---|---|---|
| #125 | `BIGINT PK` SQLite 不 alias rowid | 没去验证默认 `SQLALCHEMY_DATABASE_URL=sqlite:///db.sqlite3` |
| #126 | `User.key` + `subscription_url` 未 redact | SPEC 写 `subscription_token`,我没 grep 实际项目字段名 |
| #126 | `Admin.hashed_password` 实际列名 | 列了 `password_hash` 别名,没看 `app/db/models.py` |
| #127 | `.env.example` 缺 `AUDIT_SECRET_KEY` | 没考虑 operator fresh-install 流程 |

**根因**:单模型自审有"自我盲点"——同一模型既写代码又审代码,带着同一组假设(SPEC 说啥就是啥)。Cross-model 强制第二模型用**独立先验**重审,会去做 first model 没做的功课(grep 项目实际字段 / 读默认 env / 验证 fresh-install 流程)。

**Codex 真的去做了**:`app/models/user.py` / `app/db/models.py` / `.env.example` 全部 grep 验证。这是 Claude 自审会全漏的关键差异。

## 强制规则

### 1. 业务路径 PR 必跑 cross-review

修改 `scripts/business-paths.txt` 列出的任一路径(`dashboard/src/` / `hardening/` / `ops/` / `deploy/` / `tests/` / `app/`)的 PR,**必须**在 push 后立即跑:

```bash
bash .agents/skills/codex-bridge/run.sh HEAD
```

跳过条件**只有**:
- 纯 docs PR(`.md` only,无 `.py` / `.ts` / `.tsx` / `.sh`)
- Forbidden 路径 PR(自动被 SSOT 过滤,但仍需 spec-driven + 双签;cross-review 走 `FORCE=1` 手动决定是否跑)

### 2. 修 P2 后必跑二审

Codex 给出 P2 finding 修复后,**必须**重新跑:

```bash
git push  # 新 commit 上 origin
bash .agents/skills/codex-bridge/run.sh HEAD  # 同 commit 不会被 dedup
```

理由:修复可能引入新问题(尤其 schema / type 改动),二审 PASS 才算闭环。

### 3. 小 PR 多次审 > 大 PR 一次审

Codex 上下文窗口有上限。审 1000 行 PR 不如审 200 行 × 5 个 PR。

实施约束:
- 单 PR diff > 500 行 → 拆分 stack
- 单 PR 跨 ≥ 3 个目录(如 `ops/audit/` + `app/db/` + `dashboard/`)→ 拆分
- Stack 深度上限 4 层(超过先 merge 底层 PR 解锁)

### 4. P2 finding 修复必须保留 review 历史

修复 commit message 必须明确引用 codex review:
```
fix(<area>): <fix> — codex P2 (REVIEW-QUEUE.md commit <sha>)
```

PR description 必须有 "§48 Cross-Model Review 历史" 段,记录每次 review 的 verdict + 修复 commit。

### 5. Forbidden 路径双签 = cross-review 是物理实现

§32 forbidden 路径(`auth/` / `crypto/` / `migration/` / `payment/` / `secrets/` / ...)的"双签"硬规则,**cross-review 是其中一签的物理体现**:

- 第一签:Claude(drafter)
- 第二签:Codex(独立先验 reviewer)
- 第三签:user(merge UI 操作)

PR 标 `requires-double-review` label 是 administrative,**真正的双签 = cross-review verdict 在 PR comment**。

## 实施 hook

`.claude/settings.json` 已配置 `Stop` / `SubagentStop` hook 自动跑 codex-bridge。但**会话进行中的代码 PR 不会等到 Stop**,所以**主动触发是必须的**(本规则 §1 约束)。

## 例外:本机 dev env hygiene

本机 `decouple` 0.0.7 包冲突让 pytest 跑不动,但**不影响 codex review**(codex 用自己的 sandbox)。

下次 dev setup 时:
```bash
pip uninstall decouple -y  # 只留 python-decouple
```

CI 环境用 requirements.txt(只有 python-decouple),无此问题。

## Review history index

每次 cross-review 输出追加到 `docs/ai-cto/REVIEW-QUEUE.md`,**append-only**。Wave-4 累计 5 次 codex review:
- 4 次 P2 finding(修复 + 二审 PASS)
- 1 次一审 PASS

→ 命中率 80% P2(每次跑都有价值,不是浪费 token)
