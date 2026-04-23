# 多会话协作索引(SESSIONS)

> **CTO 裁判台**。所有并行 session 的地盘、状态、冲突规则登记在此。
> 开新 session 前先读这份文件;合 PR 时裁决以这里为准。
>
> 手册参考:CTO handbook §5(模型路由)、§7(Spec-Driven)、
> 铁律 #1/#8/#10(决策服务愿景 / 先建分支 / 国际化+环境分离)。

_Updated: 2026-04-23_

---

## 活跃会话

| 编号 | 名字 | 工具 | 模型 | 地盘(独占) | 当前 PR | 状态 |
|---|---|---|---|---|---|---|
| **S-B** | 商业化后端 | Claude Code | Opus(money) | `ops/billing/**`, `hardening/panel/middleware.py`(billing rows), Alembic, 相关 tests | A.2.1 #46 ✅,A.2.2 待开 | 进行中 |
| **S-F** | 商业化前端 | Claude Code | Sonnet | `dashboard/src/modules/billing/user/**`, `billing.{purchase,my-invoices}.lazy.tsx` | #41 open | ready for review |
| **S-D** | 部署一体化 | (待开) | Opus(SPEC)→Sonnet | `deploy/**`, `docs/ai-cto/SPEC-deploy.md` | — | 未启 |
| **S-R** | Reality 审计器 | (待开) | Opus(SPEC)→Sonnet | `hardening/reality/**`, `docs/ai-cto/SPEC-reality-audit.md` | — | 未启 |
| **S-X** | 前端测试基建 | (待开) | Sonnet | `dashboard/src/**/*.test.tsx`, `dashboard/src/test-utils/**`, `dashboard/vitest.config.*` | — | 未启 |
| **S-O** | 文档 / 流程 | (part-time) | Sonnet | `docs/ai-cto/**`(非 SPEC-*), `.agents/rules/**` | — | 异步触发 |

## 归档(已完成)

| 编号 | 名字 | 工具 | 产出 | 完工 |
|---|---|---|---|---|
| **S-I** | iplimit 生产化 | Codex | PR #40/#42/#43/#44/#45 合并 —— runbook + xray 日志样本 + CIDR allowlist + 时区修正 + owned-disable 可见性 | 2026-04-23 |

---

## 每个会话的 Charter

### S-B — 商业化后端

- **独占**:
  - `ops/billing/**`(Python)
  - `app/db/migrations/versions/<billing-*>`
  - 新增 `app/db/extra_models.py` 里的 billing import 行
  - `hardening/panel/middleware.py` 里 billing router `include_router` 调用(2 行,追加)
  - `tests/test_billing_*.py`(除 S-F 可能写的 dashboard-side mock 测)
- **禁动**:`app/**`(upstream 同步区)、`dashboard/**`、`hardening/{iplimit,sni,reality}/**`
- **子 PR 顺序**(per `docs/ai-cto/SPEC-billing-a2-a3.md`):A.2.1 ✅ → A.2.2 webhook → A.3.1 TRC20 matcher → A.3.2 poller + scheduler → A.3.3 admin demo stub
- **模型**:Opus(支付逻辑 = 资金,容错为零)

### S-F — 商业化前端(本会话)

- **独占**:`dashboard/src/modules/billing/user/**`, 新 routes `billing.{purchase,my-invoices}.lazy.tsx`
- **共享追加**(append-only 约定):`dashboard/src/modules/billing/types/index.ts`(末尾 re-export `./user`), `dashboard/public/locales/{en,zh-cn}.json`(新 subtree), `dashboard/src/features/sidebar/items.tsx`(新 Account 组)
- **禁动**:`ops/**`, `hardening/**`, `app/**`, 任何其他 `dashboard/src/modules/{billing/api,billing/components,nodes,users,...}/**` 里的现有文件
- **模型**:Sonnet(UI 不触 money logic)

### S-D — 部署一体化(待开)

- **独占**:
  - `deploy/install.sh`
  - `deploy/ansible/**`
  - `deploy/cloudflare/**`
  - `deploy/docker/**`(如需)
  - `deploy/.env.example`
  - `docs/ai-cto/SPEC-deploy.md`(第一 PR;骨架本次 kit 落地)
  - `docs/ai-cto/OPS-deploy-runbook.md`(后续)
- **禁动**:任何 `app/**, ops/**, hardening/**, dashboard/**`
- **第一步**:读 VISION + ROADMAP + `compass_artifact_*.md` 五件套,fleshed out SPEC,PR 后再写脚本
- **模型**:Opus 写 SPEC,Sonnet 写 install.sh / Ansible

### S-R — Reality 审计器(差异化 #3,待开)

- **独占**:
  - `hardening/reality/**`
  - `docs/ai-cto/SPEC-reality-audit.md`(本次 kit 落骨架)
  - `tests/test_reality_*.py`
- **共享追加**:`hardening/panel/middleware.py` 加 1 行 `include_router`(append-only)
- **禁动**:`ops/**, app/**, dashboard/**, hardening/{iplimit,sni,panel}/**`
- **模型**:Opus SPEC,Sonnet 实施

### S-X — 前端测试基建(待开)

- **独占**:
  - `dashboard/vitest.config.*`(改)
  - `dashboard/src/**/*.test.tsx|ts`(新增,配对每个组件)
  - `dashboard/src/test-utils/**`(新增 render helpers)
  - `docs/ai-cto/SPEC-dashboard-tests.md`(本次 kit 落骨架)
- **共享追加**:`dashboard/package.json` 的 devDependencies(append-only);`.github/workflows/dashboard-ci.yml` 的 test job 加法(append)
- **禁动**:任何 `.tsx` 源组件;只能配对加 `.test.tsx`
- **模型**:Sonnet

### S-O — 文档 / 流程(part-time)

- **独占**:
  - `docs/ai-cto/STATUS.md`
  - `docs/ai-cto/LESSONS.md`
  - `docs/ai-cto/DECISIONS.md`
  - `docs/ai-cto/ROADMAP.md`
  - `.agents/rules/**`(LESSONS 固化)
- **禁动**:任何代码、任何 SPEC-*.md(每个 SPEC 归对应 session)
- **触发**:每 3 轮(按手册铁律 #6)或每个重大 PR 合并后
- **模型**:Sonnet

---

## 冲突地带 + 化解规则

| 文件 | 谁会动 | 规则 |
|---|---|---|
| `hardening/panel/middleware.py` | S-B, S-R | 每人只加 1 行 `include_router`;后 merge 者 1 行冲突 rebase |
| `app/db/extra_models.py` | S-B(billing)、S-R(可能加 reality) | append-only 一行 `import ... # noqa: F401` |
| `app/db/migrations/versions/**` | S-B、S-R | Alembic 严格串行:后起的 revision 的 `down_revision` 指先 merge 那条的 id |
| `docs/ai-cto/STATUS.md` | S-O 为主;其他人可追加 PR 表行 | append-only 新行;S-O 周期性压缩 |
| `dashboard/public/locales/en.json` + `zh-cn.json` | S-F(purchase/my_invoices)、S-R(reality)、S-X(测试 fixtures 的 key) | 每人独立 subtree,append-only;merge 二者按 JSON key 子树互不相交 |
| `dashboard/src/features/sidebar/items.tsx` | S-F(Account 组已在 #41)、S-R(可能加 Security 组) | 每个新组塞文件末尾;1-5 行冲突可人工解决 |
| `dashboard/src/routeTree.gen.ts` | 任何前端加路由的 session | 自动生成,**禁手改**;后 merge 者重跑 `npx tsr generate` |
| `dashboard/package.json` devDeps | S-X、S-F | append-only,JSON 冲突人工 |
| `.github/workflows/*.yml` | S-X(dashboard-ci 加 test job)、S-D(deploy workflow 新文件) | S-D 只新增文件;S-X 只追加 job,不改现有 job |

---

## 铁规则

1. **每个 session 必须在此表登记**。没登记就 push 代码的 PR,review 时一票否决。
2. **共享冲突点**改动必须 append-only(除非该规则明示可改)。
3. `app/**` **upstream 同步区**禁动,除非是 `upstream-sync/YYYY-MM-DD` 专用 PR。
4. 每个 session 开 PR 时:
   - PR body 列 "I touch:", "I don't touch:"
   - 链接本文件
5. 冲突裁决顺序:本文件登记谁先 → CI 触发时间 → 强制写 boundary-update PR 补规则
6. 每 3 轮或每重大 merge 后 S-O 触发,刷 STATUS + 归档已完成 session。

---

## 待办(模板驱动 kickoff)

每个新 session 的启动 prompt 见 `docs/ai-cto/SPEC-deploy.md`、`SPEC-reality-audit.md`、`SPEC-dashboard-tests.md` 的开头 `## Kickoff prompt` 节。
