# hardening/panel/ — 面板自身加固

**状态**: ⏳ 部分(v0.1 P0 + v0.2)

**范围**: 面板**自身**不被打穿(区分于"节点抗封")。

## 模块

| 模块 | 阶段 | 说明 |
|---|---|---|
| `jwt_secret.py` | v0.1 | 从 `.env` 读 HMAC_SECRET,禁止库存储(AUDIT.md ④ 🔴) |
| `rate_limit.py` | v0.1 | slowapi + Redis 令牌桶,`/api/admins/token` 必装 |
| `cors_policy.py` | v0.1 | 从 `.env` 读 CORS 白名单,禁止 `*` + `allow_credentials=True` 组合 |
| `dashboard_path.py` | v0.2 | 随机化 `DASHBOARD_PATH`,避免扫描器命中默认 `/dashboard/` |
| `cf_tunnel_wizard/` | v0.2 | CF Tunnel + Access 配置生成 + 一键下发 |

## 设计约束

- 不魔改 `app/marzneshin.py` 中间件链 —— 通过 `include_router` 或
  `app.add_middleware()` 在 `main.py` 启动时注入
- 所有策略参数走 `.env`,禁止硬编码

## 暂无实现。
