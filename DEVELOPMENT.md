# 开发指南(DEVELOPMENT)

> 目标读者:本项目贡献者。运维/部署文档在 `deploy/README.md`。
> 项目身份与愿景见 `CLAUDE.md` 与 `docs/ai-cto/`。

---

## 前置

- Python **3.12**(严格,SQLAlchemy 2.0 typed mappings 依赖)
- Node.js 20+ 与 **pnpm**(dashboard 专属)
- Docker + Docker Compose(本地跑 postgres/redis 最简)
- 推荐编辑器:VS Code + Pylance + Biome 扩展

## 本地启动(最小路径)

```bash
# 1) 后端依赖
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) 环境变量
cp .env.example .env
# 编辑 .env:至少设置 SQLALCHEMY_DATABASE_URL,默认 SQLite 即可开跑

# 3) DB 迁移 + 启动后端
alembic upgrade head
python main.py
# 默认监听 127.0.0.1:8000(无 SSL 时强制 localhost,这是安全特性,勿改)

# 4) 前端开发(另一终端)
cd dashboard
pnpm install
pnpm run dev
# 默认 http://0.0.0.0:3000/dashboard,通过 VITE_BASE_API 指向 http://0.0.0.0:8000/api/
```

## 快捷命令(makefile)

```bash
make start            # alembic upgrade + python main.py
make test             # 后端 pytest + 前端 vitest
make test-backend     # 仅后端
make test-dashboard   # 仅前端
make lint             # ruff + biome
make format           # ruff format + biome format
make db-reset         # 删除 SQLite + 重跑迁移(破坏性,仅本地)
make dashboard-deps   # pnpm install
make dashboard-build  # 生产构建到 dashboard/dist
make dashboard-dev    # Vite dev server
```

## Docker(含 Marznode 数据面)

```bash
docker-compose up -d          # 根目录开发 compose(upstream 保留)
docker-compose logs -f
# 生产 compose 未来在 deploy/compose/docker-compose.prod.yml
```

### 可选服务:PostgreSQL 16 + Redis 7

Round 1 起,`docker-compose.yml` 包含两个**可选 profile**。默认启动**不会**拉起它们,SQLite-only 部署零改变。

```bash
# 同时启 PG + Redis
docker compose --profile postgres --profile redis up -d

# 只启 PG(无 Redis,rate-limit 功能禁用)
docker compose --profile postgres up -d

# 退回默认
docker compose up -d
```

**切换到 PostgreSQL**(必须在启动 `marzneshin` 前设好 `.env`):

```env
POSTGRES_DB=aegis
POSTGRES_USER=aegis
POSTGRES_PASSWORD=<32-char random>
SQLALCHEMY_DATABASE_URL=postgresql+psycopg://aegis:<同上>@127.0.0.1:5432/aegis
```

迁移:

```bash
alembic upgrade head
```

**启用 Redis**:

```env
REDIS_URL=redis://127.0.0.1:6379/0
# REDIS_POOL_SIZE=20  # 可选,默认 20,>1000 req/s 再调
```

Redis 未配置时,`app.cache.redis.get_redis()` 会抛 `RedisDisabled`,依赖 Redis 的功能(如下方的 admin 速率限制)会**拒绝启用**,**不会**让 app 启动失败。

### 启用 admin 登录速率限制

默认关。开启前 **必须** 先配好 `REDIS_URL`。

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_ADMIN_LOGIN=5/minute  # 可选,默认值
```

开启后若 `REDIS_URL` 缺,启动直接抛 `RateLimitMisconfigured` 并终止。这是故意的 —— 多 worker 部署下,内存计数器会让每个 worker 独立限流,相当于没限。

**反代情况下**(CF Tunnel / Nginx / Caddy):默认按 `request.client.host` 取 IP,反代后会取到反代节点 IP(所有请求看起来都来自同一 IP,要么 0 限速要么全 429)。解决:

- Uvicorn 启动加 `--forwarded-allow-ips='*'`(或具体反代 IP)
- 或在 `app/marzneshin.py` 的 Uvicorn `Config` 里加 `forwarded_allow_ips`
- 真正治本:在 Round 2 的 `hardening/panel/` 下加一个 `TrustedProxyMiddleware` 读 `X-Forwarded-For` 的倒数第 N 个值,由 `.env` 配置可信反代层数

当前 Round 1 不处理反代,文档里标清楚。

健康检查:`docker compose ps` 应该看到 `postgres` 和 `redis` 都是 `healthy`。

### 从 SQLite 迁移到 PostgreSQL

官方未提供 in-place 迁移。现有操作:

1. 在旧 SQLite 部署上跑 `marzneshin-cli` 导出用户 / 订阅 / 节点
2. 切 `.env` 到 PostgreSQL URL
3. `alembic upgrade head` 建表
4. `marzneshin-cli` 导入

期间面板下线。如果数据量大、停机不可接受,在 `deploy/README.md` 规划的 Ansible playbook 里会有一个蓝绿流程,Round 2 落地。

### SNI 智能选型器(hardening/sni)

新节点的 Reality `serverName` 候选自动选型,把原本 30-60 分钟的手工流程(TLS 1.3/H2/X25519 验证 + 同 ASN 邻居确认 + DPI 黑名单规避)压到一次命令。详见 `hardening/sni/README.md` 和 `docs/ai-cto/SPEC-sni-selector.md`。

```bash
# 从全球种子池选 10 条候选(默认区域 auto)
python -m hardening.sni.selector --ip <vps-egress-ip> --count 10

# 从日本区域池选 5 条(全球 + jp 种子合并去重)
python -m hardening.sni.selector --ip 103.x.x.x --count 5 --region jp
```

输出 JSON 到 stdout,含:

- `candidates[]` —— 按 score 降序,每条含 6 条硬指标 pass/fail + 分值来源
- `rejected[]` —— 被拒候选 + 原因(方便运营排查"为什么列表是空的")

退出码:`0` = 至少 1 个候选通过;`1` = 零候选(检查 `rejected[]`);`2` = VPS ASN 查不到(致命)。

本地跑要求 Python 3.12+(3.13 + OpenSSL 3.2+ 精确检测 X25519,3.12 走 fallback,准确度 ≥95%)。`blacklist.yaml` 和 `seeds/*.yaml` 不改代码直接编辑,加载时 fail-loud 验证。

CI 的 `test_sni_*.py`(41 个测试)完全 mock 网络,离线可跑。

## 目录速查

| 目录 | 性质 | 修改策略 |
|---|---|---|
| `app/` | upstream 同步区(Marzneshin) | 改前先 `git diff upstream/main` 评估冲突 |
| `dashboard/` | upstream 同步区 | 同上,Biome 强制 |
| `hardening/` | **自研** — 加固层 | 自由改,upstream 冲突面零 |
| `deploy/` | **自研** — IaC | 自由改,脚本为主 |
| `ops/` | **自研** — 运营层 | 自由改,含新 DB 模型 |
| `docs/ai-cto/` | CTO 项目记忆 | 仅 CTO 角色更新;私密部分放 `private/`(gitignore 覆盖) |
| `tests/` | 稀疏,待补 | Round 1 重点补齐 |

## 数据库

- **默认 SQLite**(开发便利),商业场景 v0.1 末切 **PostgreSQL 16**
- 迁移:`alembic revision --autogenerate -m "<describe>"`
- **禁止** 手改 `alembic/versions/*.py` 后不跑 `alembic upgrade head` 验证
- 多 DB 兼容:不写 `sqlite_only` 的 pragma 语句,避免 PostgreSQL 切换时返工

## 测试

当前覆盖率极低(`tests/test_migrations.py` 仅 4 行),Round 1 目标:

- backend 覆盖率 ≥ 40%
- dashboard 覆盖率 ≥ 30%
- CI 必须全绿才合并

fixture 约定(建立中):

- `tests/conftest.py` 提供 `db`, `redis`, `mock_marznode`, `mock_aiohttp`
- 集成测试走 `TestClient`(FastAPI),不起真实 Uvicorn

## 代码风格

- **Python**:Ruff(线宽 **79**,与 upstream black 一致,别随手改)+ `from __future__ import annotations` 统一开启
- **TS/React**:Biome(dashboard 已配)+ 组件 PascalCase / hooks `use*`
- **i18n**:新增 UI 文本**必须**走 i18n key,禁止硬编码中英文
- **SQL**:SQLAlchemy 2.0 `select()` 风格,禁止裸 SQL 除非迁移脚本

## 提交规范

- 分支:`feat/*` / `fix/*` / `hardening/*` / `deploy/*` / `ops/*` / `chore/*` / `upstream-sync/YYYY-MM-DD`
- Commit:Conventional Commits(`feat:` / `fix:` / `chore:` / `refactor:` / `docs:` / `test:`)
- PR 必须:CI 全绿 + 至少一条自动测试 + 关联 `docs/ai-cto/` 对应更新

## 安全红线(摘自 `.agents/rules/security.md`)

- **禁硬编码** JWT secret、DB 密码、Xray 私钥、CF 凭据 —— 全走 `.env`
- **SSL 默认安全**:无 SSL 证书时 `main.py` 强制监听 127.0.0.1,不要改
- **CORS**:生产环境禁止 `allow_origins=["*"]` + `allow_credentials=True`
- **AGPL 合规**:绝不删除 upstream 版权头,网络提供服务必须暴露源码入口

## 常见故障

| 症状 | 排查 |
|---|---|
| `alembic upgrade head` 报外键冲突 | 多半是多人同时迁移,先 `alembic heads` 看分叉,必要时 `alembic merge` |
| dashboard 开发跑不起来 | 确认 pnpm 版本 ≥ 8,删 `node_modules` 后 `pnpm install --force` |
| 面板外网访问不到 | `UVICORN_HOST` 默认 127.0.0.1(仅本机)。外网访问必须 (a) CF Tunnel / Nginx 前置反代,或 (b) 显式 `UVICORN_HOST=0.0.0.0` 且同时配 `UVICORN_SSL_CERTFILE`;`main.py` 无 SSL 时会强制覆盖回 127.0.0.1 |
| `ImportError: grpcio` | `requirements.txt` 的 grpcio 1.69 对 Python 3.13 有兼容问题,固定 3.12 |

## 更多

- CTO 手册:`C:\projects\ai-playbook\playbook\handbook.md`
- 路线图与轮次:`docs/ai-cto/ROADMAP.md` + `docs/ai-cto/STATUS.md`
- 竞品与偷学:`docs/ai-cto/COMPETITORS.md`
- AGPL 合规检查:`.agents/skills/agpl-compliance/SKILL.md`
