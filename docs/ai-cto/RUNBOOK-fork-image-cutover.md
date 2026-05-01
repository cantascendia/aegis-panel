# RUNBOOK — Fork Image Cutover (upstream → ghcr.io fork)

> **何时用**：第一次把生产 panel 从 `dawsh/marzneshin` upstream 镜像切到自构 `ghcr.io/cantascendia/aegis-panel`。
> 后续仓库升级走 `aegis-upgrade vX.Y.Z`，不再走本 runbook。
>
> **触发条件回顾**（L-033）：≥50 客户 / mTLS 修复 / 品牌差异化客户问询，三选一即开始。

---

## 0. 前置条件

| 项 | 检查命令 | 期望 |
|---|---|---|
| 仓库公开 | https://github.com/cantascendia/aegis-panel | "Public" 标签 |
| ghcr.io image 存在 | https://github.com/cantascendia/aegis-panel/pkgs/container/aegis-panel | `v0.3.0` tag 可见 |
| VPS SSH 可达 | `ssh -i ~/.ssh/id_ed25519 root@<vps>` | 登入成功 |
| 当前 image 跑的是 upstream | `docker compose -f /opt/aegis/compose/*.yml ps` panel image 列 | `dawsh/marzneshin:v0.2.0` |

---

## 1. 触发首次 CI 构建

```bash
# 主机本地
git checkout main && git pull
git tag v0.3.0
git push origin v0.3.0
```

CI workflow `.github/workflows/package.yml` 监听 `v*.*.*` tag，约 5–8 分钟后产出：
- `ghcr.io/cantascendia/aegis-panel:v0.3.0`
- `ghcr.io/cantascendia/aegis-panel:latest`

监控：https://github.com/cantascendia/aegis-panel/actions

CI 完成后，浏览器看 https://github.com/cantascendia/aegis-panel/pkgs/container/aegis-panel，应有 `v0.3.0` tag。

---

## 2. VPS 全量备份（5 分钟，必做）

```bash
ssh -i ~/.ssh/id_ed25519 root@<vps-ip>

mkdir -p /opt/aegis-backup-pre-fork
cp /opt/aegis/.env /opt/aegis-backup-pre-fork/.env
cp -a /opt/aegis/data/panel /opt/aegis-backup-pre-fork/panel
cp /opt/aegis/data/marznode/xray_config.json /opt/aegis-backup-pre-fork/xray_config.json
docker compose -f /opt/aegis/compose/docker-compose.sqlite.yml ps \
  > /opt/aegis-backup-pre-fork/state-before.txt

# 验证备份大小合理
ls -lh /opt/aegis-backup-pre-fork/
```

---

## 3. 部署 aegis-upgrade 脚本到 VPS

**首次切换时仓库还没 clone 到 VPS**（install.sh 是直接拷过来跑的），所以本次必须手动放：

```bash
# 主机本地
scp -i ~/.ssh/id_ed25519 scripts/aegis-upgrade.sh \
  root@<vps-ip>:/usr/local/bin/aegis-upgrade
ssh -i ~/.ssh/id_ed25519 root@<vps-ip> "chmod +x /usr/local/bin/aegis-upgrade"
```

后续 `install.sh` 重跑时会自动部署（见 install.sh 的 `deploy_aegis_upgrade_script` 函数）。

---

## 4. 执行切换（30 秒）

```bash
ssh -i ~/.ssh/id_ed25519 root@<vps-ip> "aegis-upgrade v0.3.0"
```

脚本自动：
1. 备份 `/opt/aegis/.env` 到 `.env.bak.<timestamp>`
2. 把 `AEGIS_VERSION=v0.2.0` 改成 `v0.3.0`
3. `docker compose pull panel`（仅 panel，marznode/postgres/redis 不动）
4. `docker compose up -d panel`（滚动重启）
5. 打印验证命令

**保留数据原理**：volume mount `/opt/aegis/data/panel:/var/lib/marzneshin` 是 host 路径，换 container image 不动 host 文件系统。SQLite DB / .env / xray_config.json / Reality 私钥全部留存。

---

## 5. 验证 (8 项)

```bash
ssh -i ~/.ssh/id_ed25519 root@<vps-ip>
cd /opt/aegis/compose
COMPOSE=docker-compose.sqlite.yml   # or docker-compose.prod.yml

# 1. 容器健康
docker compose -f $COMPOSE ps
# panel = "Up X seconds (healthy)"

# 2. API 活
curl -fsS http://127.0.0.1:8443/openapi.json | head -c 100
# 返回 {"openapi":"3.x.x"...

# 3. fork 代码加载
docker compose -f $COMPOSE exec panel python -c \
  "import hardening.panel.middleware; from ops.audit import middleware; print('OK')"
# 输出: OK

# 4. 启动日志包含加固 hook
docker compose -f $COMPOSE logs --tail=200 panel | grep -E "apply_panel_hardening|audit"
# 应有匹配行

# 5. 镜像 tag 正确
docker compose -f $COMPOSE images panel
# image 列 = ghcr.io/cantascendia/aegis-panel:v0.3.0

# 6. DB 留存（浏览器登 https://nilou.cc/dashboard/）
# 4 用户 + 订阅链接全部存在

# 7. 端到端代理通（v2rayNG 用现有订阅）
# ip.sb 显示日本 IP

# 8. AGPL self-check
curl -fsS https://nilou.cc/__source__
# 返回 GitHub 仓库地址（fork 独有）
```

---

## 6. 回滚

**任意验证项失败 → 立即回滚（30 秒）**：

```bash
ssh -i ~/.ssh/id_ed25519 root@<vps-ip> "aegis-upgrade v0.2.0"
```

会把 image 切回 `dawsh/marzneshin:v0.2.0`（upstream）。volume 数据完整。

**Alembic 迁移破坏 DB（极少见但有保险）**：

```bash
ssh -i ~/.ssh/id_ed25519 root@<vps-ip>
cd /opt/aegis/compose
docker compose -f docker-compose.sqlite.yml stop panel
cp /opt/aegis-backup-pre-fork/panel/db.sqlite3 /opt/aegis/data/panel/db.sqlite3
sed -i 's/AEGIS_VERSION=v0.3.0/AEGIS_VERSION=v0.2.0/' /opt/aegis/.env
docker compose -f docker-compose.sqlite.yml up -d panel
```

---

## 7. 切换成功后的状态变化

| 项 | 切换前 (v0.2.0 upstream) | 切换后 (v0.3.0 fork) |
|---|---|---|
| Panel image | `dawsh/marzneshin` | `ghcr.io/cantascendia/aegis-panel` |
| `hardening/panel/middleware.py` | ❌ 不在容器 | ✅ 加载到进程 |
| `ops/audit/*` | ❌ 不在容器 | ✅ 中间件 + 调度器在跑 |
| `app/db/extra_models.py` | ❌ | ✅ 自研 model 注册 |
| AGPL `__source__` 路由 | ❌ 404 | ✅ 200 |
| L-032 mTLS bug | 🔴 panel↔marznode gRPC 断 | 🔴 仍断（需 v0.4 修） |

---

## 8. 后续每次升级（30 秒）

仓库侧：
```bash
git tag v0.4.0
git push origin v0.4.0
```

VPS 侧：
```bash
ssh root@<vps-ip> "aegis-upgrade v0.4.0"
```

无需再走本 runbook。
