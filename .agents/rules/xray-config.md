---
name: xray-config
description: Xray/Reality/VLESS 配置生成与审计规则(Marzneshin fork 核心护城河)
activation: glob
globs:
  - "**/xray*.json"
  - "**/*xray*.py"
  - "app/marznode/**"
  - "hardening/sni/**"
  - "hardening/reality/**"
---

# Xray / Reality 配置规范

这是项目护城河。任何 Xray / Reality / VLESS 配置的生成、存储、下发,必须满足下列硬指标(出自 `compass_artifact_*.md` Reality 2026 加固清单)。

## Reality serverName(SNI)硬指标

任何自动生成或用户手填的 Reality `serverName` 必须满足:

1. ✅ 目标站支持 **TLS 1.3**
2. ✅ 目标站支持 **HTTP/2**
3. ✅ 目标站支持 **X25519** 曲线
4. ✅ 目标站**不是跳转域**(例如 `yahoo.com` 会 302 到 `www.yahoo.com`,必须用 `www.yahoo.com`)
5. ✅ 目标 IP 与 VPS 在**同一数据中心或同一 ASN**(加分项,但商业化机场必须)
6. ❌ **禁止** `speedtest.net`(Iran MCCI 已重点 DPI 盯上)
7. ❌ **禁止** `www.google.com`(中国不可达,回落失败被识别)
8. ✅ 地区匹配:日本 VPS 优先 `www.tiktok.jp`/`www.amazon.co.jp`;韩国 `static.naver.net`/`www.kakao.com`;美区 `swdist.apple.com`

`hardening/sni/selector.py` 必须在返回候选 SNI 前跑完 1-4 验证,失败立即拒绝。

## uTLS 指纹与 Vision 流控

- `fingerprint` 默认 `chrome`(与 XTLS-Vision + Reality 兼容)
- 同一订阅/用户组所有客户端**用同一指纹**,混用 chrome+safari 是异常模式
- **禁止** `chrome_pq`(后量子 ClientHello):`nil ecdhe_key` bug 未修(sing-box issue #2084)
- **禁止** `randomized` / `HelloChrome_106_Shuffle`:每次唯一 = 独特特征,Iran 已识别
- 裸 TCP 传输 Reality 必须启用 `flow: xtls-rprx-vision`(XHTTP/gRPC 传输可省略)

## 回落与策略

- **禁止**启用回落限速(`bytesPerSec`):本身就是指纹
- Xray `policy.levels.0`:`connIdle: 120`、`handshake: 2`(让僵尸连接尽快释放,提高 IP 计数准确度)
- 不同用户建议分配不同 `spiderX` 路径或不同 `shortId`,让日志级区分更干净

## 端口选择

- 避免 443 被扫:推荐非标准端口 **8443、2053**(Cloudflare 友好端口)
- 商业化机场多节点:每节点端口不同减少指纹关联

## 禁止行为(配置生成代码中)

- ❌ 硬编码 UUID / PrivateKey / ShortId
- ❌ 硬编码某个 serverName 为默认(必须由 SNI 选型器运行时决定)
- ❌ 把 `.env` 的 JWT_SECRET 用作 Xray 的 PrivateKey(完全无关的两个 secret,不能复用)
- ❌ 把 Xray config 整份 commit 到 repo(走 `/var/lib/marzneshin/` 或 `/var/lib/marznode/`,gitignore 已覆盖 `*-custom.json` 等)

## 验证工具

- 部署时用 `xray tls ping <domain>` 或 `RealiTLScanner` 扫 VPS /24,直接挑邻居 IP 的证书 SAN 作为 serverName
- `hardening/sni/selector.py` 在 CI 里跑一次,验证候选域名全部过上面 1-6 条

## Marznode 侧注意

- Marznode(数据面)直接读 `/var/lib/marznode/xray_config.json`
- 控制面(本 repo)通过 gRPC push 配置时,**必须**先本地跑配置验证(启动一个临时 Xray 进程 dry-run),不能直接下发
- 节点失联时,控制面不得停机,必须降级(该节点标记 unhealthy,路由到其他节点)

## 审计检查点

`hardening/reality/audit.py` 必须实现以下检查,CI 时跑:

1. 所有用户的 serverName 均在 whitelist 中(whitelist 由 SNI 选型器周期性刷新)
2. 所有用户的 fingerprint 均 = `chrome`(或人工批准的其他指纹)
3. 无用户启用 `bytesPerSec` 回落限速
4. `policy.levels.0` 包含 `connIdle<=120 && handshake<=2`
5. Xray config 中无硬编码明文 secret(正则扫描 UUID / base64 key 模式)

违反任一,输出告警,不合并分支。

## 参考资料

- `compass_artifact_wf-5103cc40-b39f-4d20-9217-61987475be44_text_markdown.md` — 原始清单
- sing-box issue #2084 — chrome_pq bug
- Xray-core 官方文档 Reality 协议部分
