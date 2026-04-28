# deploy/ — IaC / 一键部署引擎(自研)

**职责**:从空 VPS 到面板可访问 ≤ 15 分钟(v0.2 验收线)。幂等、可回滚、可观测。

**License**:默认 Apache-2.0(脚本/配置独立,与 AGPL 主体兼容)。子目录内可独立声明;未声明时继承根 `LICENSE`(AGPL-3.0)。

---

## 快速开始(S1 — 个人 MVP / SQLite)

> 目标用户:1 台 VPS、≤ 50 用户、不上 CF Tunnel。约 5 分钟。

```bash
# 1. 拉本仓库到 /opt/aegis/src(install.sh 假设此路径)
sudo mkdir -p /opt/aegis/src
sudo git clone https://github.com/cantascendia/aegis-panel /opt/aegis/src
cd /opt/aegis/src

# 2. 跑安装器(交互式)
sudo ./deploy/install/install.sh \
  --db sqlite \
  --domain panel.example.com \
  --cf-tunnel no
```

完成后凭据写在 `/opt/aegis/INSTALL-SUMMARY.txt`(mode 600)。

## S2 — 成长期(PostgreSQL + 同机 marznode + CF Tunnel,推荐生产)

```bash
sudo ./deploy/install/install.sh \
  --db postgres \
  --marznode same-host \
  --domain panel.example.com \
  --cf-tunnel yes
```

`--cf-tunnel yes` 在面板健康后链式调用 `deploy/cloudflare/install-tunnel.sh`(D.4 PR 单独提供)。

## S3 — 商业运营(>1 节点)

控制面用上面的 S2 流程。**节点机**用:

```bash
# (D.2 PR,本 PR 不交付):
sudo ./deploy/marznode/install-node.sh \
  --control-plane=panel.example.com \
  --node-id=2
```

多节点请用 `deploy/ansible/`(D.3,本 PR 不交付)。

---

## 安装器(`deploy/install/install.sh`)

### Flags

| Flag | 默认 | 说明 |
|---|---|---|
| `--non-interactive` | off | 全部值从 flag/env 取,Ansible 用 |
| `--from-env FILE` | — | 从已有 `.env` 继承(再跑跳问) |
| `--db {sqlite\|postgres}` | postgres | < 2 GiB RAM 时自动切 sqlite |
| `--marznode {same-host\|skip}` | same-host | skip = 不本机起数据面 |
| `--domain FQDN` | — | **必填**,订阅 URL / nginx server_name |
| `--admin-username` / `--admin-password` | random | 24 字符 URL-safe |
| `--jwt-secret` | random | 64 字节 base64 |
| `--cf-tunnel {yes\|no\|skip}` | skip | yes = 链式调 D.4 脚本 |
| `--version` | v0.2.0 | 镜像 tag |
| `--prefix` | /opt/aegis | 安装根目录 |
| `--dry-run` | off | 只校验不动文件系统 |
| `--force` | off | 跳过 tier-2 OS 警告 |

### 退出码契约(SPEC §"非交互模式下的输出契约")

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 依赖缺失(docker / docker compose v2 / curl / openssl / jq) |
| 2 | 配置非法(无 `--domain`、tier-3 OS、env 校验失败) |
| 3 | 健康检查超时(120s 内 `/api/system/info` 未 200) |
| 4 | 端口占用 / 磁盘空间不足 |
| 5 | 保留(D.4 — CF token scope 不足) |

非交互模式 stdout 输出机器可读 KV(供 Ansible `register` 解析):

```
admin_username=admin-Ab3xK9
admin_password=...
dashboard_url=https://panel.example.com/aBcD1234
subscription_url_prefix=https://panel.example.com/qWeRtY78
aegis_version=v0.2.0
db_kind=postgres
provider_asn=24940
```

### 幂等性(AC-D.1.4 / AC-D.1.5)

每个步骤完成后写 sentinel:`/opt/aegis/.install-step-{1..9}.done`。重跑时已完成步骤跳过。中断后再跑从下一步继续。

完整重置(测试用):

```bash
sudo rm -f /opt/aegis/.install-step-*.done
sudo ./deploy/install/install.sh ...   # 整个流程重跑
```

### 系统要求

- **Tier-1 (CI 测,推荐生产)**:Ubuntu 22.04 LTS、Ubuntu 24.04 LTS、Debian 12
- **Tier-2 (warning + `--force` 才装)**:Ubuntu 20.04、Debian 11、其他 Debian 系
- **拒绝**:CentOS / RHEL / Alma / Rocky / Fedora / Amazon Linux

硬件:
- RAM ≥ 2 GiB(< 2 GiB 自动切 SQLite)
- CPU ≥ 2 cores(< 2 cores 仅 warning)
- `/var/lib` ≥ 20 GiB free(< 20 GiB 直接 abort)

依赖(脚本不强装,缺时打印 `apt-get install ...` 命令):
- `docker` ≥ 24
- `docker compose` v2 plugin(v1 standalone 不支持)
- `curl`、`openssl`、`jq`

---

## Compose 文件

| 文件 | 用途 | 服务 |
|---|---|---|
| `compose/docker-compose.prod.yml` | S2/S3 生产 | postgres + redis + alembic + panel + marznode + nginx |
| `compose/docker-compose.sqlite.yml` | S1 轻量 | panel + marznode + nginx(SQLite 内联迁移) |
| `../docker-compose.yml`(根) | upstream 保留,演示 | profile gating 的 pg/redis;**不在生产用** |

资源上限(默认,可在 override 文件覆盖):
- panel:1 CPU / 1 GiB
- postgres:0.5 CPU / 512 MiB
- redis:0.25 CPU / 256 MiB
- marznode:0.5 CPU / 512 MiB
- nginx:0.5 CPU / 256 MiB

日志:`json-file`,`max-size: 10m`、`max-file: 3`(避免长跑磁盘打爆)。

---

## `.env` 渲染

`install.sh` step 5 从 `install/templates/env.tmpl` 渲染到 `/opt/aegis/.env`(mode 600,`aegis:aegis`)。模板包含 compass 五件套默认值:

- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=45`(≤ 60)
- `DASHBOARD_PATH` / `XRAY_SUBSCRIPTION_PATH` 8 字符随机
- `XRAY_POLICY_CONN_IDLE=120`、`XRAY_POLICY_HANDSHAKE=2`
- `PANEL_PORT=8443`(非标)、`MARZNODE_GRPC_PORT=62051`
- `REALITY_UTLS_FINGERPRINT=chrome`、`REALITY_FLOW=xtls-rprx-vision`
- `REALITY_SNI_BLOCKLIST=www.google.com,speedtest.net`(校验默认 SNI 不命中)

`install/lib/render.sh::validate_rendered_env` 强制校验上述值,违反即 exit 2(对齐 AC-D.1.10)。

提交到仓库的 `deploy/.env.example` 是模板的占位副本(所有敏感字段为 `__RANDOMIZE_ON_INSTALL__`),手动复制时 `grep __ /opt/aegis/.env` 查漏。

---

## 后续 PR(本 PR 不含)

| PR | 目标 | 状态 |
|---|---|---|
| **D.1** | install.sh + compose + .env.example + 本 README | **本 PR** |
| D.2 | `marznode/install-node.sh`(独立数据面) | 待开 |
| D.3 | `ansible/`(common + marzneshin + marznode roles) | 待开 |
| D.4 | `cloudflare/`(tunnel + access)+ `compliance/agpl-selfcheck.sh` | **并行 PR**(姊妹 agent) |
| D.5 | `OPS-deploy-runbook.md` 完整版 | 待开 |

本 PR 也未交付:
- `deploy/install/lib/asn-blocklist.txt`(ASN 探测目前是 best-effort 记录,不命中 blocklist —— 未来 PR 补)
- `deploy/install/templates/nginx.conf.tmpl`(rate-limit zones,留 D.4)
- `deploy/pg/init.sql`(DB / role 创建,留 D.4 或合并入 alembic)

---

## 验证清单

```bash
# 静态语法
bash -n deploy/install/install.sh
bash -n deploy/install/lib/*.sh

# 帮助页
bash deploy/install/install.sh --help            # exit 0

# Compose schema(需 docker)
docker compose -f deploy/compose/docker-compose.prod.yml config --quiet
docker compose -f deploy/compose/docker-compose.sqlite.yml config --quiet

# 冒烟测试
bash tests/test_deploy_install_smoke.sh
```

## 相关 runbook(已就位 / 部分待补)

| 子系统 | runbook | 主要场景 |
|---|---|---|
| 部署主流程 | [`OPS-deploy-runbook.md`](../docs/ai-cto/OPS-deploy-runbook.md) | 节点迁移 / DB 备份 / CF token 应急 |
| IP 限制 | [`OPS-iplimit-runbook.md`](../docs/ai-cto/OPS-iplimit-runbook.md) | 时区对齐 / 误封解封 |
| SNI 选型 | [`OPS-sni-runbook.md`](../docs/ai-cto/OPS-sni-runbook.md) | 零候选通过 / blacklist 维护 |
| Reality 审计 | [`OPS-reality-runbook.md`](../docs/ai-cto/OPS-reality-runbook.md) | 全节点扫描 / 月度巡检 |

每份 runbook 默认按 "检测命令 / 判定条件 / 处置步骤 / 验证命令" 四段式。
