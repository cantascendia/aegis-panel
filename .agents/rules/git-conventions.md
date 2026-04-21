---
name: git-conventions
description: 分支命名、PR 标题、commit 消息规范(含 conventional-commit type 白名单)
activation: always
---

# Git / PR 规范

本仓 `amannn/action-semantic-pull-request` workflow 会校验 PR 标题;脚本和人都按以下规范操作。

## PR 标题:conventional commit,type 必须在白名单

**允许的 type**(upstream 固化,不要自己发明):

```
build  chore  ci  docs  feat  improve  fix
merge  perf   refactor  refact  revert  style  test  wip
```

```
# ✅ 合法
fix(security): externalize JWT signing secret
feat(infra): PostgreSQL 16 + Redis 7 optional integration
chore(deps): upgrade 6 non-auth packages with CVEs
docs(memory): Round 1 closeout

# ❌ type 不在白名单,CI 直接拒
hardening(p0): admin-login rate limiter
security: tighten CORS policy
harden: JWT secret externalization
```

**scope 是必填**(本仓 `amannn/action-semantic-pull-request` 配了 `requireScope: true`)。`fix: ...` 会被 CI 打回,必须写成 `fix(security): ...` / `fix(ci): ...`。没 scope 的 commit title 不违法(`git log` 允许),但 PR 合并前 title 必须带 scope。

推荐 scope 词典:`security / hardening / infra / cache / cd / memory / rules / spec / deps` 等领域名。首次出现一个新 scope 记一下,下次沿用同名。

**body 细节** 放 PR description,不挤标题。标题 ≤ 70 chars。

## 分支命名(`.claude/settings.json` 的 bash 权限和各种 CI 的 path 过滤都依赖命名规范)

| 前缀 | 用途 |
|---|---|
| `feat/*` | 新功能 |
| `fix/*` | bug 修复 |
| `hardening/*` | 安全加固 / panel 自身防御 |
| `deploy/*` | IaC / 部署脚本 |
| `ops/*` | 商业化运营层(计费 / 审计 / 告警 / RBAC) |
| `chore/*` | 依赖升级 / 格式化 / 清理 |
| `docs/*` | 文档 / memory 刷新 |
| `test/*` | 补测试(独立测试 PR 才用) |
| `upstream-sync/YYYY-MM-DD` | 从 marzneshin upstream 合入 |

## Commit 消息

- **Conventional Commits 1.0**:`<type>[optional scope]: <description>`
- 标题 ≤ 72 字符,祈使句现在时
- body 用空行分隔,解释 **why + 关键决策**,不重复 diff 能说明的 what
- breaking change 写 `BREAKING CHANGE:` 段落

```
fix(security): CORS strict by default, whitelist via CORS_ALLOWED_ORIGINS

AUDIT.md section 4, finding P0-4. Upstream shipped:

    allow_origins=["*"], allow_credentials=True

... (rationale)

Behavior change for operators: any deployment whose dashboard lives on
a different origin than the API must now set CORS_ALLOWED_ORIGINS.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## 铁律(来自 `CLAUDE.md` 核心循环)

1. **先建分支再动手**。`main` 直接改是事故。LESSONS.md 记过一次"git commit 意外落在 main"的教训,路径是工具副作用,但**规矩没守住会让事故从小变大**
2. **destructive git 操作**(`reset --hard`、`push --force`、`branch -D`)只在用户明确请求时才跑;否则用 `--force-with-lease` 或 `git branch -f <ref>` 等软路径
3. **永不 `--no-verify` 跳过 hook**,除非用户明确说跳
4. **合并用 squash 或 merge commit,不 rebase merge**(除非分支只有一个 commit 且本地 ff)

## 跨越 PR 的 docs 更新

- 主流程:每 PR 的改动顺手在 `docs/ai-cto/STATUS.md` 有 "Round 1 PR 汇总" 类表格时更新一行
- 大 PR / SPEC-driven PR:附带 `docs/ai-cto/SPEC-<name>.md`(见 D-005)
- 新学会的 CI / 工具坑:加到 `docs/ai-cto/LESSONS.md`,同类 ≥2 次再升为 `.agents/rules/*.md`
