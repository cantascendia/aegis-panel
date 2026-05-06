---
name: customer-portal-build-check
description: >
  在提交 customer-portal/ 改动前自动跑构建 + 19 路由完整性 + dist 预算 + 无样式系统漏混入。
  当任务涉及 customer-portal/src/ 任何 .jsx / .tsx / .css 文件、vite.config.js、package.json、
  index.html、public/assets/ 时触发。在缺正式 GitHub Actions CI workflow 期间作为 agent-layer
  的兜底门(workflow 落地后仍保留作 PR 前自检)。不适用于 dashboard/、app/、marketing/。
---

# customer-portal Build & Integrity Check

P1(PR #240)落地后,`customer-portal/` 缺一道 GitHub Actions CI smoke-build 守门(`.github/workflows/**` 是 §32.1 forbidden-path,需用户双签 + 从 `customer-portal/CI-SNIPPET.md` 复制)。在那之前,本 skill 是兜底:任何 portal 改动 push 前必须跑通这五条。

## 触发

修改以下任一时触发:
- `customer-portal/src/**/*.{jsx,tsx}`
- `customer-portal/src/**/*.css`
- `customer-portal/vite.config.js`、`customer-portal/package.json`
- `customer-portal/index.html`
- `customer-portal/public/assets/**`

不触发(明确排除):
- `customer-portal/README.md`、`customer-portal/CI-SNIPPET.md`(纯文档)
- `customer-portal/src/data/mock.js`(本身是 mock,可静态改)— P1 visual-only

## 必须通过

### 1. Build pass

```bash
cd customer-portal
pnpm install --frozen-lockfile  # 必须无 lockfile drift
pnpm build                       # 退出 0
```

退出非 0 直接停;不允许"build 偶尔过"。

### 2. Dist size 预算

```bash
DIST_SIZE=$(du -sb customer-portal/dist | cut -f1)
P1_BASELINE=$((236 * 1024))      # 236 KB,P1 ship 时
P2_BUDGET=$((400 * 1024))        # P2 + i18n + auth 头预算
P3_BUDGET=$((600 * 1024))        # P3 + API client + error boundary 头预算
```

| Phase | Budget | 触发何时 |
|---|---|---|
| P1(visual + mock) | ≤ 260 KB(baseline + 10%)| 当前 |
| P2(+ i18n + TSX + auth) | ≤ 400 KB | SPEC SEAL 后 |
| P3(+ API client + error boundary) | ≤ 600 KB | P3 SPEC 中 |
| P4(+ marketing 接管)| 重评估 | TBD |

超预算 10% 直接停;5% 写 SPEC 解释;0-5% 静默通过。

### 3. 19 路由完整性

`customer-portal/src/App.jsx`(P2 后 `App.tsx`)的 route table 必须 19 条匹配:

```bash
# 数 route 分支
grep -cE "if \(path === '" customer-portal/src/App.{jsx,tsx} 2>/dev/null
# 期望:21 条 if(=19 路由 + /panel + /panel/ 别名)
```

少于 19 条直接停 — 说明有路由被误删。

### 4. 样式系统纯净度

P1 + P2 期 portal **不**用 Tailwind / shadcn(SPEC TBD-3 SEAL "single CSS-var token")。grep 反查:

```bash
# 不允许 Tailwind utility class 出现在 portal jsx/tsx
grep -rE 'className="[^"]*\b(flex|grid|p-[0-9]|m-[0-9]|w-[0-9]|h-[0-9]|text-(xs|sm|base|lg|xl|[0-9]xl)|bg-(red|blue|green|gray)-[0-9]+)\b' customer-portal/src/ 2>&1 | head -5

# 不允许 shadcn import
grep -rEn "from ['\"]@/(components/ui|lib/utils)" customer-portal/src/ 2>&1 | head -5
```

任一命中 → 警告 + 要求改成 CSS variables(`var(--brand-teal)` 等,见 `customer-portal/src/styles/tokens.css`)。

### 5. AGPL footer 链接保留

`customer-portal/src/lib/Marketing.jsx` 的 `MarketingFooter` 必须含:

```bash
grep -q "github.com/cantascendia/aegis-panel" customer-portal/src/lib/Marketing.jsx || echo "❌ AGPL footer 链接丢失 — 违反 §13 网络服务源码可获取"
```

footer 链接缺失 → 停 + 强制恢复(违 Constitution §④ + AGPL §13)。

## 与其他守门的关系

| 守门 | 状态 | 作用 |
|---|---|---|
| 本 skill(agent-layer)| ✅ 立即可用 | PR 前自检兜底 |
| `.github/workflows/customer-portal-ci.yml` | ⏸ 等用户落地 | CI 强制守门(`customer-portal/CI-SNIPPET.md`) |
| `.claude/rules/forbidden-paths.md` | ✅ 已含 portal 行 | AuthPages.jsx / PanelPages2.jsx 编辑触发双签 |
| `.claude/rules/eval-gate.md` | ✅ 已含 portal 行 | 同上,golden trajectory 配套 |
| `evals/golden-trajectories/006-007` | ✅ wave-12 R0 land | spec-driven + visual-smoke 行为约束 |

## 失败时的处理

- Build 失败 → 不 commit,先看 vite 报错(常见:tokens.css 拼写、import 路径、JSX/TSX 转换边界)
- 预算超 → 看是否引入了大依赖(`pnpm why <package>`),P1 期不应有新依赖
- 路由数错 → 对比 git diff,误删的路由要还原;新增路由要 SPEC 同步
- Tailwind 漏 → 改回 CSS variables,P5 重评估时机
- AGPL 丢 → 立即恢复,不允许 push

## 触发命令

`/cto-skills run customer-portal-build-check` 或在改动 portal 后由 agent 自动调用。

完整 P1 baseline 数据见 `customer-portal/README.md`,P2 数据待 SPEC SEAL 后更新。
