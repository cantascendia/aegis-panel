# hardening/ — Reality 2026 加固层(自研)

**职责**: 把 Marzneshin 从"能跑"推到"抗封 + 抗共享"。所有模块与 `app/` 解耦,
upstream 同步时冲突面最小。

**License**: 默认 AGPL-3.0(与上游一致)。子模块若与 upstream 代码零衍生,可在
该子目录下声明独立 `LICENSE`(Apache-2.0 / MIT),参见 `NOTICE.md`。

---

## 子模块规划

| 子目录 | 状态 | 职责 | 关联路线图 |
|---|---|---|---|
| `sni/` | ⏳ 待建 | SNI 智能选型器:同 ASN 扫描 + TLS1.3/H2/X25519 验证 + DPI 黑名单 | v0.2 差异化 #1 |
| `reality/` | ⏳ 待建 | Reality 配置审计器:`shortIds` 熵、`xver`、`spiderX` 一致性校验 | v0.2 |
| `iplimit/` | ⏳ 待建 | 原生 IP 并发限制(订阅 Marznode Xray stats,不依赖 Marzban API) | v0.3 |
| `panel/` | ⏳ 待建 | 面板加固:CF Tunnel/Access 向导、Dashboard Path 随机化、JWT 时效器 | v0.1 P0 + v0.2 |
| `fallback/` | ⏳ 待建 | XHTTP / Hysteria2 备用通道配置下发 | v0.3 |

## 为什么独立目录

1. **Upstream 同步零冲突**:改这里不动 `app/`,`git fetch upstream` 后合并面极小
2. **可裁剪**:商业运营方若只需 SNI 选型器,可不部署 `iplimit/`
3. **license 灵活**:新算法可走 Apache-2.0,便于未来向生态回馈

## 新增子模块时

1. 在本表登记(状态、职责、关联路线图阶段)
2. 子目录内至少包含 `README.md` + 单元测试目录
3. 若脱离 AGPL-3.0,补 `LICENSE` + `NOTICE` 头
4. 对 `app/` 的调用必须经显式接口(不直接 import 业务实体),便于后续抽象
