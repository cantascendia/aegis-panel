---
name: security
description: 安全基线规范(商业化机场 >200 用户,直面 DPI 封锁与撞库攻击)
activation: always
---

# 安全基线(永远激活)

商业化机场 + Reality 加固 + 法域敏感 → 安全不是 feature,是生死线。以下规则对**所有文件**生效。

## 认证与授权

- **JWT secret 必须从 `.env` 读取,绝不硬编码,绝不存 DB**(审核 AUDIT.md ④-2 标注)
- **`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` 默认必须 ≤ 60**(上游默认 1440 = 24h 泄露窗口太长)
- 管理员密码用 `bcrypt.hashpw`(rounds ≥ 12);禁止 MD5/SHA1/plain text
- 管理员账号**强密码 ≥ 20 字符**随机;弱口令在 CI 中检测
- 登录接口(`/api/admin/token` 或对应路径)必须加**速率限制**:5 次/分钟/IP
- 订阅接口也加速率限制:10 秒 5 次(防被人脚本化拉取)
- **管理员分层权限**是 Round 2+ 任务;在此之前至少分 admin / readonly 两种角色

## 传输层

- `UVICORN_HOST=127.0.0.1` 是默认/推荐(`main.py` 已经这样做,别改)
- 外部访问走:① Cloudflare Tunnel + Access(推荐给商业化)② SSH tunnel ③ Nginx/Caddy SSL 反代
- 如必须暴露 0.0.0.0:证书必须公网 CA 签发(非 self-signed),`main.py` 的 `validate_cert_and_key` 会校验
- CORS:禁止 `allow_origins=["*"]`(审核 AUDIT.md ④-4);必须 whitelist 具体域名

## 密钥管理

所有密钥 / 凭据 **必须** 分三层:

| 层 | 存储 | 例子 |
|---|---|---|
| 项目级 | `.env`(gitignore) | JWT_SECRET, DB_PASSWORD |
| 用户级 | 数据库加密字段 | 用户订阅 token, 2FA secret(未来) |
| 节点级 | 节点本地(marznode) | Xray PrivateKey, TLS cert |

**禁止**跨层:例如 JWT_SECRET 不能派生 Xray key;用户订阅 token 不能复用为 JWT。

## 输入验证

- **所有外部输入**(API 请求 body / query / header / 订阅 token)必须 Pydantic 验证
- 订阅路径接受任意 prefix(`XRAY_SUBSCRIPTION_PATH` 随机化)但必须白名单字符集 `[a-zA-Z0-9_-]{8,32}`
- 管理员 dashboard 路径同理:`DASHBOARD_PATH` 必须随机化(默认 `/dashboard/` 是扫描器首选)
- 禁止字符串拼接 SQL / shell 命令;用参数化查询 / `subprocess` with `args=[]`

## 日志与审计

- **禁止** log:用户完整订阅 token、JWT、管理员密码、Xray UUID/PrivateKey
- **必须** log(审计层):管理员登录成功/失败、用户 CRUD、节点增删、订阅生成、敏感配置变更
- 审计日志独立表 + immutable(append-only)
- 日志目标:文件轮转 + 可选发送到外部 SIEM(Sentry / Grafana Loki / ELK)

## 部署期安全

- `.env` 文件权限:`chmod 600`(仅 owner 读)
- Docker 容器不要以 root 运行(Dockerfile 需加 `USER` 指令,审核 AUDIT.md ⑥-3)
- 网络:marznode 与 marzneshin 之间用 TLS + mutual auth(grpcio 支持)
- 定期 `pip list --outdated` + `safety check` 扫 CVE;自动化成 CI 任务

## 合规红线

1. **AGPL-3.0**:通过网络提供服务必须能让用户获取源码(见 `NOTICE.md`)
2. **法域风险**:运营主体境外隔离;中国大陆 IP 黑名单屏蔽;不保留真实身份信息
3. **支付**:走加密货币或境外 SaaS;禁止国内支付通道

## 上线前安全 checklist(每次发版跑一遍)

- [ ] `.env` 中所有 secret 已填真实值,不是示例占位
- [ ] `JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 60`
- [ ] `UVICORN_HOST=127.0.0.1` 或外部走 CF Tunnel
- [ ] 管理员密码已改(不是 `admin`/`123456`/其他弱口令)
- [ ] `DASHBOARD_PATH` 已随机化
- [ ] `XRAY_SUBSCRIPTION_PATH` 已随机化
- [ ] CORS whitelist 只含生产域名
- [ ] `pip list --outdated` 无高危 CVE
- [ ] Docker 容器非 root 运行
- [ ] 审计日志开启并验证写入
- [ ] 速率限制规则已部署(登录 + 订阅接口)
- [ ] Reality 配置中 serverName 全部过 `hardening/reality/audit.py` 校验

## 事件响应

发现安全漏洞:

1. 高危(可 RCE / 泄露用户数据 / 绕过认证):
   - 立即创建 `fix/security-<short-desc>` 分支
   - 修复 + 测试 + 合入 main + 热发布
   - 通知所有节点运营方升级
   - 写入 `docs/ai-cto/DECISIONS.md` 作为历史记录
2. 中危(DoS / 信息泄露低影响):
   - 24 小时内修复
3. 低危(加固建议):
   - 下一个 release 周期修复

## 参考

- AUDIT.md 第 ④ 维(本项目具体漏洞清单)
- CLAUDE.md 铁律 #10 #11 #12
- OWASP Top 10 2021
