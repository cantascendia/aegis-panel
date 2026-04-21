---
name: ci-workflows
description: GitHub Actions workflow 与 Docker Compose 配置规范(踩过的坑总结)
activation: glob
globs:
  - ".github/workflows/**/*.yml"
  - ".github/workflows/**/*.yaml"
  - "docker-compose*.yml"
  - "docker-compose*.yaml"
---

# CI / Compose 规范

Round 1 从血泪里总结出来的坑,修起来小但发现前能让 CI 轮询翻两倍。来源对应 `docs/ai-cto/LESSONS.md`。

## GitHub Actions

### `continue-on-error` 放 **step 级**,不是 job 级(L-004)

```yaml
# ❌ 错:job 还是报 fail,PR checks UI 继续红
jobs:
  security:
    continue-on-error: true
    steps:
      - run: pip-audit ...

# ✅ 对:step 失败后 step 视为成功,job 整体报 success
jobs:
  security:
    steps:
      - name: pip-audit
        continue-on-error: true
        run: pip-audit ...
```

意图是"可见但非阻塞"时,**必须**放到执行真实命令的那个 step 上。

### ASCII hyphen,不是 em-dash(L-005)

YAML step name / comment / label 只用 ASCII `-`。`gh pr checks` tab-separated 输出、一些通知 bot、Windows 终端字体在 em-dash `—` 上都不稳定。

```yaml
# ❌
- name: ruff check - self-owned dirs only  # em-dash looks fine in GitHub UI, breaks elsewhere

# ✅
- name: ruff check (self-owned dirs only)
```

文档正文(README / markdown)可以用 em-dash,那里渲染器稳定。

### 默认 branches 值要显式(`main`)

不依赖 repo 默认分支推断(`$default-branch` 在 reusable workflow 里可以,在 on.push.branches 下得写死)。Marzneshin fork 过来的 workflow 多半写着 `master` —— 新建 fork 时首轮 CI 前必须搜 `branches:\s*\[\s*["']master` 全替成 `main`。

## Docker Compose

### 可选 profile 的"必需"env 用 `${VAR:-}`,不是 `${VAR:?err}`(L-006)

Compose 变量替换发生在 **parse 阶段**,profile 过滤发生在 **execution 阶段**。`:?err` 触发的是 parse-time failure,根本走不到 profile 判断 —— 所有人都 fail,包括**完全没启这个 profile** 的部署。

```yaml
# ❌ 让 docker compose up(无 profile)对所有人 fail
services:
  postgres:
    profiles: [postgres]
    environment:
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"

# ✅ 不启 postgres profile 时 compose parse 成功;启了但缺密码时 postgres 容器自己退出
services:
  postgres:
    profiles: [postgres]
    environment:
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-}"
```

fail 点从"所有人 parse 失败"转移到"真正需要时容器启动失败",时机正确。

### 可选服务永远挂 `profiles:`,不开默认

新增 PG / Redis / Prometheus 等 **可选** 服务必须带 `profiles:` 字段,`docker compose up` 默认不拉起。SQLite-only / 无 Redis 部署零行为变化。

### 生产服务容器的 `--maxmemory` / `--save` 等覆盖要写注释解释**为什么这个值**

比如本仓 `docker-compose.yml` 的 redis:
```yaml
command: >
  redis-server
  --save ""
  --maxmemory 256mb
  --maxmemory-policy allkeys-lru
```
注释写明 "rate-limit-only use case, short-lived counters, no durability needed"。否则半年后没人敢调。

## 规则之外

- 任何让 CI 红的配置误差,把修复经过记到 `docs/ai-cto/LESSONS.md`;同类出现 ≥2 次 → 追加到本文件作为硬规则
- upstream workflow 里依赖外部 token / secret 的任务(Telegram / Chromatic / Codecov),fork 场景下要么加 "skip-if-secret-unset" 守卫,要么直接删。别留着让 PR 永远红一条
