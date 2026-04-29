---
name: agpl-compliance
description: AGPL-3.0 合规检查器 — 扫描修改过的上游文件是否保留版权头、是否有对用户源码披露入口、依赖 license 兼容性。发版前必跑。
---

# AGPL-3.0 合规检查(Skill)

## 目的

项目是 Marzneshin 的 AGPL-3.0 fork。运营商业化机场 = 通过网络对用户提供服务 = AGPL 触发 = 必须对用户提供对应源码。

合规错一次不是罚款问题,是项目生存问题(license 违约可导致强制开源 / 撤销使用权)。这个 Skill 把合规检查自动化,每次发版前必跑。

## 何时调用

- **发版前**(release 分支合 main 前)
- **引入新依赖时**(pip install 前检查新包 license)
- **修改 upstream 文件时**(必须保留原版权头)
- **季度合规审计**

## 检查项

### ① 上游版权头保留检查

扫描 `app/` 和 `dashboard/src/` 下所有文件,对比 upstream 原始文件。
如果文件头部原本有 `# Copyright ...` / `// Copyright ...` / `/*! ... */` 注释块,修改后必须保留。

实现:
```bash
# 用 git show 上游首个 commit 的文件版本,diff 前 30 行
git show ca4735e:app/marzneshin.py | head -30
```

**违规**:有任何文件的原版权头被删除或改写 → BLOCK。

### ② LICENSE 文件完整性

- `LICENSE`(根目录)必须存在且内容为 GNU AGPL-3.0 全文(35156 bytes)
- `NOTICE.md` 必须存在且包含 upstream commit SHA

```bash
wc -c LICENSE   # 应为 35156(或接近,改行符差异)
grep "d3b25e23c4977c63eacc6aca591e0cdf0c2bcd68" NOTICE.md
```

### ③ 依赖 license 兼容性

扫描所有依赖的 license,必须与 AGPL-3.0 兼容(即不得是更限制性的 license,比如 GPL-only 无 AGPL 补充)。

AGPL-3.0 兼容(可用):
- ✅ MIT, BSD (2/3-clause), ISC, Apache 2.0
- ✅ LGPL-3.0, GPL-3.0-or-later(但要双向)
- ✅ AGPL-3.0

不兼容(禁用):
- ❌ GPL-2.0-only(单纯 GPL-2 无"or later")
- ❌ 专有 / commercial-only license
- ❌ BSL (Business Source License)
- ❌ SSPL (MongoDB license)

实现:
```bash
pip install pip-licenses
pip-licenses --format=json | jq '[.[] | select(.License | test("SSPL|BSL|Proprietary|GPL-2\\.0-only"; "i"))]'
```

对 npm 侧:
```bash
cd dashboard && pnpm licenses list --json > licenses.json
# 扫 problematic license pattern
```

### ④ 用户源码披露入口检查

运营 >200 用户付费机场时,AGPL 要求能让用户获取源码。

检查项:
- 面板登录页或 footer 必须有源码链接(指向 public Git 仓库 URL)
- 或有 `/api/source` 端点返回源码 tarball / Git URL

实现:
```bash
# 扫 dashboard 代码是否有 source link
grep -r "github.com" dashboard/src/components/layout/ 2>/dev/null

# 扫后端是否有 /source 路由
grep -r "source" app/routes/ | grep -i "route\|path"
```

**违规**:商业化部署版 dashboard 无源码链接 → BLOCK 发版。

### ⑤ 自研模块 license 声明

`hardening/`、`deploy/`、`ops/`、`docs/ai-cto/` 下的独立新模块如要用非 AGPL license:
- 每个模块目录必须有自己的 `LICENSE` 文件
- 文件头必须标明 license

无独立 license 文件 = 默认 AGPL-3.0(向上继承)。

### ⑥ NOTICE.md 最新性

- upstream commit SHA 必须与当前 `git log` 中 upstream-sync 的最新 commit 匹配
- 如执行过 `upstream-sync/YYYY-MM-DD` 分支合并,`NOTICE.md` 必须更新 "forked at" → "last synced at"

## 脚本位置建议

- `hardening/agpl/check.py` — 主 CLI:`python -m hardening.agpl.check`
- 退出码 0=全过,2=有违规(CI 阻断)

## CI 集成

```yaml
# .github/workflows/agpl-compliance.yml
- name: AGPL-3.0 compliance check
  run: python -m hardening.agpl.check
```

## 违规处理

1. 版权头被删 → 从 git 历史恢复该文件对应部分 + re-commit
2. 不兼容依赖混入 → 立即移除或找替代;无替代则退回不引入
3. dashboard 无源码链接 → 在 Layout 组件底部加,link 到部署方的公开 fork 地址
4. NOTICE.md 陈旧 → 更新 SHA 和日期

## 参考

- `NOTICE.md`
- `LICENSE`(AGPL-3.0 全文)
- AGPL-3.0 官方 FAQ: https://www.gnu.org/licenses/agpl-3.0.html
