# hardening/panel/ — 面板自身加固

**状态**: ⏳ 部分(v0.1 P0 + v0.2)

**范围**: 面板**自身**不被打穿(区分于"节点抗封")。

## 模块

| 模块 | 阶段 | 说明 |
|---|---|---|
| `jwt_secret.py` | v0.1 | 从 `.env` 读 HMAC_SECRET,禁止库存储(AUDIT.md ④ 🔴) |
| `rate_limit.py` | ✅ v0.1(PR #5) | slowapi + Redis 令牌桶,已装在 `/api/admins/token` 和 `/api/nodes/sni-suggest`。默认关,`RATE_LIMIT_ENABLED=true` 启用,**必须** 配 `REDIS_URL`,否则启动 fail-loud |
| `middleware.py` | ✅ v0.1+v0.2 | `apply_panel_hardening(app)` 一键装 Limiter + 429 handler + SlowAPIMiddleware + **自研 routers**(SNI endpoint 等),与 upstream `app/marzneshin.py` 耦合面仅一行 |
| `cors_policy.py` | v0.1 | 从 `.env` 读 CORS 白名单,禁止 `*` + `allow_credentials=True` 组合 |
| `dashboard_path.py` | v0.2 | 随机化 `DASHBOARD_PATH`,避免扫描器命中默认 `/dashboard/` |
| `cf_tunnel_wizard/` | v0.2 | CF Tunnel + Access 配置生成 + 一键下发 |

## 设计约束

- 不魔改 `app/marzneshin.py` 中间件链 —— 通过 `include_router` 或
  `app.add_middleware()` 在 `main.py` 启动时注入
- 所有策略参数走 `.env`,禁止硬编码

## 相关模块

- **节点侧抗封**:`hardening/sni/` —— Reality `serverName` 智能选型(6 条硬指标)。
  面板加固保护**面板本身**不被打穿;SNI 选型保护**节点**不被 DPI 识别/封锁。
  两层互补:面板走 CF Tunnel 隐蔽,节点走冷门 SNI 混入真实流量。
  详见 `hardening/sni/README.md` 与 `docs/ai-cto/SPEC-sni-selector.md`。
- **合规配置审计**:未来 `hardening/reality/` —— 基于 SNI 选型结果审计
  现网配置漂移(Skill: `.agents/skills/reality-config-audit/SKILL.md`)。
