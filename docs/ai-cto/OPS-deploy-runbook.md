# OPS — 部署运维手册(S-D session)

> **状态**:骨架(D.5 待 flesh out)。本文件配套 `SPEC-deploy.md` 的 AC-D.5.*,
> 每个应急场景 D.5 时补齐 **检测命令 / 判定条件 / 处置步骤 / 验证命令** 四段式。
>
> 对接:[SPEC-deploy.md](./SPEC-deploy.md)、[SESSIONS.md §S-D](./SESSIONS.md)、
> compass_artifact 五件套(CF Tunnel / DASHBOARD_PATH 随机化)。

---

## 读者对象与使用方式

- **主读者**:拥有 panel 的运营者(机场主)或被授权的运维
- **辅读者**:S-D session 自己(事故复盘时校对 runbook 是否仍然准确)
- **使用场景**:故障发生时 **5 分钟内找到对应章节** → 跑检测命令 → 依处置步骤处置 → 跑验证命令闭环
- **不是**:开发教程、架构文档、SPEC(那些去 `SPEC-deploy.md`)

## 文档结构约定

每个章节(除本前言)必须含四段:

```
### <场景名>

**检测命令**:<一条可直接 copy-paste 的 shell 命令,输出判定依据>

**判定条件**:<什么输出 = 触发本场景>

**处置步骤**:<编号步骤,每步一条命令或一个决策,含预期输出>

**验证命令**:<处置完跑什么验证已恢复>
```

违反此结构的 PR 不合。

---

## 日常运维(非应急)

### D.OPS.1 — 节点迁移(VPS 换机)

> TBD(D.5):覆盖 `ansible/roles/marznode` 的迁移流程、gRPC cert 搬运、
> 订阅链接 rewrite、DNS TTL 预降、旧节点 grace period、
> 验证客户端无感切换。

### D.OPS.2 — PostgreSQL 备份与还原

> TBD(D.5):`pg_dump` 定时任务(建议 crontab 示例)、备份加密、
> 异地存放(S3 / R2)、还原 drill、ANALYZE 回表。
> 对齐 SPEC §回滚 / 升级路径的 "`/opt/aegis/backups/pre-upgrade-*`"。

### D.OPS.3 — 升级(minor / major)

> TBD(D.5):升级前 checklist(备份 / 公告 / 维护窗口)、
> `install.sh --upgrade` 使用、healthcheck 回归、
> Alembic migration 状态校验(呼应 L-015 不变性)。

### D.OPS.4 — AGPL 合规自检日常化

> TBD(D.5):`deploy/compliance/agpl-selfcheck.sh` 作为每月运维作业、
> 依赖 license 变动处置、源码披露入口 uptime 监测。

---

## 应急场景(按严重度排)

### D.OPS.E1 — CF API token 泄露(Sev 1)

> TBD(D.5):CF 后台 Revoke token → 扫 git log / CI secret scan →
> 重签 token scope 收窄 → `install-tunnel.sh` 重新 bind →
> 验证 tunnel 仍通。
> 响应 SLA:发现起 ≤ 30 分钟完成 revoke。

### D.OPS.E2 — 升级失败需回滚(Sev 1)

> TBD(D.5):`git checkout <prev-tag>` 路径 / Alembic `downgrade` 可行性
> 判定 / DB 备份还原路径 / 切回旧 tag 后 healthcheck。
> **L-015 限制**:已 merge 的 revision 不能改 `down_revision`;
> 若 downgrade 语义不干净,只能滚前不滚后。

### D.OPS.E3 — marznode 节点掉线

> TBD(D.5):gRPC 连接失败的四种根因(cert 过期 / 网络 / 端口 /
> 控制面 DB 锁)分诊树;cert 轮换(链接到 D.OPS.E5);
> 节点重启命令;grace period 配置。

### D.OPS.E4 — DASHBOARD_PATH 被扫描到(404 爆炸)

> TBD(D.5):nginx access log grep 判定;
> 立即改 `.env` 中 `DASHBOARD_PATH` 为新随机值;
> 通知管理员新 URL;
> CF WAF rate limit 临时加严(5/min → 1/min)。
> 对齐 compass_artifact "管理面板加固" 节。

### D.OPS.E5 — 证书轮换(计划内)

> TBD(D.5):`ansible-playbook cert-rotate.yml` 走位;
> 新 CA 下发 → 控制面切 → 24h grace → 清旧 CA;
> 验证所有节点 online。

### D.OPS.E6 — CF Tunnel 服务中断(CF 侧故障)

> TBD(D.5):检测 `curl $PANEL_DOMAIN` 非 200 且 CF status page 确认;
> 切换备用入口(nginx 非标端口 + IP allowlist);
> 通知管理员切本地 SSH tunnel;
> 恢复后切回。

### D.OPS.E7 — JWT secret 疑似泄露

> TBD(D.5):轮换 `JWT_SECRET` → restart panel → 旧 token 立即失效 →
> 强制所有管理员重登 → 审计日志 grep 异常 token 使用。

### D.OPS.E8 — 数据库锁死(pg long-running transaction)

> TBD(D.5):`pg_stat_activity` 查长事务 → 识别 pid → `pg_terminate_backend`
> 决策(是否等 / 是否 kill) → restart panel 场景。

### D.OPS.E9 — 磁盘满

> TBD(D.5):`df -h` 判定 → 清 docker logs(`docker system prune`)→
> 清 Xray access.log(仅旧 partition)→
> 清旧 DB backups → 扩容路径(provider 特定)。

### D.OPS.E10 — 全量故障(panel 完全不可访问)

> TBD(D.5):**最后一道防线**。SSH 到控制面 →
> `docker compose logs --tail 200` → 常见错误分类表 →
> 未知错误:`systemctl restart aegis-panel.service` + 等 120s →
> 仍不通:进入手工恢复模式(从 backup 还原)。

---

## 联络与通告

> TBD(D.5):
> - 管理员告警渠道(Telegram 群 / 邮件)
> - 用户通告模板(订阅即将切换 / 维护窗口)
> - 内部事故分级(Sev 1/2/3)与响应时限矩阵

---

## 附录:命令速查

> TBD(D.5):
> - `install.sh` flag 速查
> - `ansible-playbook` 常用 `--limit` / `--tags` 示例
> - `docker compose` / `systemd` 常用命令
> - CF API curl 速查(不含 token)
> - `alembic` 升级 / 回滚 / 状态命令

---

## 变更日志

- **2026-04-23** — 骨架建立(docs-only,S-D session 开);每节仅占位,D.5 flesh out。
