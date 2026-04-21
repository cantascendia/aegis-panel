# deploy/ — IaC / 一键部署引擎(自研)

**职责**: 从空 VPS 到面板可访问 ≤ 15 分钟(v0.2 验收线)。幂等、可回滚、可观测。

**License**: 默认 Apache-2.0(脚本/配置独立,与 AGPL 主体兼容)。子目录内可
独立声明;未声明时继承根 `LICENSE`(AGPL-3.0)。

---

## 子模块规划

| 子目录 | 状态 | 职责 | 阶段 |
|---|---|---|---|
| `install/` | ⏳ 待建 | `install.sh` — 单节点一键(apt / docker / compose / .env / migrate / up) | v0.2 |
| `compose/` | ⏳ 待建 | 生产 `docker-compose.yml`(含 postgres + redis + marzneshin + marznode + nginx) | v0.1 末 |
| `ansible/` | ⏳ 待建 | 多节点 playbook(3-10 VPS 场景) | v0.2 |
| `cloudflare/` | ⏳ 待建 | CF Tunnel + Access 自动化(Zero Trust API) | v0.2 |

## 原则

1. **幂等**:重复执行不破坏已有状态,失败可 resume
2. **可回滚**:每一步有 undo(或明确说明不可回滚)
3. **可观测**:关键步骤输出进度 + 日志路径
4. **不依赖运行时外部服务**(CF Tunnel 除外,它是卖点不是依赖)

## 与 `docker-compose.yml`(根目录)的关系

根 `docker-compose.yml` 是 **upstream 保留**的开发/演示用。生产场景使用
`deploy/compose/docker-compose.prod.yml`,二者不混淆。

## 暂无实现。
