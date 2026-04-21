# Marzban + Reality 2026 加固清单

**最安全的组合是 VLESS + XTLS-Vision + Reality，SNI 挑选同数据中心且支持 TLS 1.3 / H2 / X25519 的冷门域名，账号共享用 iptables 级的 luIP 或 V2IpLimit 外挂工具控制，管理面板必须 127.0.0.1 + SSH 隧道或 Cloudflare Tunnel 暴露**。Marzban 面板本身不提供 TOTP 二次验证，防护只能靠网络层隔离、强口令与路径混淆。下文分四部分给出可直接落地的配置取舍。

## SNI 选择的三条硬指标与候选域名

Reality 的伪装成败几乎只取决于 serverName 这一行。官方给出的硬性条件有四个：**目标站必须支持 TLS 1.3、HTTP/2、X25519 曲线**，且域名不能是跳转域（`yahoo.com` 会 302 到 `www.yahoo.com`，因此服务端写 `www.yahoo.com` 才合法）。加分项是目标 IP 与你的 VPS 在**同一数据中心或同一 ASN**，这样探测者看到 443 握手后做反向 TCP 探测也会落到一台“真实可达”的邻居服务器；以及目标站启用 OCSP Stapling、Server Hello 后立即加密握手消息（`dl.google.com` 是教科书级样本）。

通用候选按“全球可用性 + 特征不明显”排序：`www.microsoft.com`、`www.apple.com`、`addons.mozilla.org`、`itunes.apple.com`、`gateway.icloud.com` 属于全球 CDN 级 Anycast，哪里都不太违和。**日区机器优先 `www.lovelive-anime.jp`、`www.tiktok.jp`、`www.amazon.co.jp`**；韩国机器用 `static.naver.net`、`www.kakao.com`；美区推荐 `swdist.apple.com`、`www.bing.com`。**一定要避开 `speedtest.net` 和 `www.google.com`**——前者在 Iran MCCI 已被 DPI 重点盯上且在 2024 年出现大规模封锁，后者在中国直接不可达，会导致回落失败被识别。

实际部署前跑一次 `xray tls ping <域名>` 或 RealiTLScanner 扫描 VPS 所在 /24，直接挑邻居 IP 的证书 SAN 作为 serverName，这是目前最稳的做法。启用回落限速（`bytesPerSec`）本身就是指纹，**不要开**。

## uTLS 指纹与 XTLS-Vision 的正确搭配

客户端 `fingerprint` 默认用 `chrome` 就好，与 XTLS-Vision 和 Reality 都兼容；`firefox`、`edge`、`safari`、`ios` 也可选，但要让**全家用同一指纹**以免出现一家 chrome、一家 safari 共享同一 UUID 时的异常模式。`randomized` 和 `HelloChrome_106_Shuffle` 每次生成唯一指纹，看似更隐蔽，实际上"每次不同"本身就是特征，已有报告在 Iran 被识别。**`chrome_pq`（后量子 ClientHello）与 Reality 目前仍存在 `nil ecdhe_key` bug**（sing-box issue #2084），务必避开。

Vision 流控（`flow: xtls-rprx-vision`）通过包长度填充消除 TLS-in-TLS 特征，是必须启用项；仅在 XHTTP 或 gRPC 等非裸 TCP 传输时才能省略。若追求极致抗封，可在桌面用 Browser Dialer（localhost:8080）让真实浏览器代握手，但会牺牲便利性，不适合分发给普通用户。

## 防账号共享的四层方案对比

Marzban 核心团队公开反对把 IP 限制做进面板，理由是网络抖动导致的并发 IP 计数本质上不可靠。但生产环境必须有所约束，社区主流方案有四种，各有权衡：

| 方案 | 机制 | 优点 | 缺点 |
|------|------|------|------|
| **V2IpLimit** | 解析 Xray access.log，超限禁用整个用户 | 支持 IPv4/IPv6 和 Marzban-node，Telegram 控制，可按国家过滤 | 惩罚面大，误伤合法用户切换网络场景 |
| **luIP-marzban** | WebSocket 拉日志 + iptables/UFW 拉黑新连接 | 只挡新 IP，已连用户不断线 | Node.js 栈复杂，iptables 版已不推荐 |
| **miplimiter** | Docker 化的轻量限制器 | 部署简单，YAML 声明用户上限 | 功能相对基础，社区活跃度一般 |
| **Xray policy + 短 connIdle** | `connIdle: 60-120`、`handshake: 2` | 无需额外组件 | 只能缓解不能根治，仍需外挂 |

推荐组合：**主限流用 luIP-marzban（UFW 模式）做新连接级封禁，用户级封禁用 V2IpLimit 做兜底**，并在 Xray `policy.levels.0` 设 `connIdle: 120`、`handshake: 2`，让僵尸连接尽快释放以提高 IP 计数准确度。给每个 shortId 发不同的客户端，或在 `spiderX` 为每用户分配不同路径，能让日志级区分更干净。

## 管理面板加固与 "伪 2FA" 方案

**Marzban 原生不支持 TOTP 二次验证**——GitHub 仓库至 2025 年底也未合并任何 2FA PR（issue #1510 才在讨论 API key 支持）。因此加固必须在网络层完成：

第一，`.env` 里设 `UVICORN_HOST = "127.0.0.1"` 强制面板仅本地监听，通过 `ssh -L 8000:localhost:8000 user@server` 访问。这是官方从 v0.7.0 起强推的默认形态，没有 SSL 证书就根本起不来 0.0.0.0。第二，如必须外部访问，用 **Cloudflare Tunnel + Cloudflare Access**：在 Zero Trust 里给面板域名挂一条 Access Policy，要求邮箱 OTP 或 Google SSO，等效于给 Marzban 白嫖了企业级 2FA。第三，把 `DASHBOARD_PATH` 从默认 `/dashboard/` 改成随机串（如 `/a7x9k-panel/`），能挡掉 99% 的扫描器。

**管理员账号必须用强随机密码（≥20 字符）**，并把 `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` 降到 60 以内——默认 1440 分钟（24 小时）的 token 泄露风险太高。Nginx 反代前置 Cloudflare WAF 的 Rate Limiting Rule（`/api/admin/token` 路径 5 次/分钟）可有效阻断撞库。订阅链接路径同样改为随机 prefix（`XRAY_SUBSCRIPTION_PATH`），并在 Cloudflare 上给该路径加 10 秒 5 次的速率限制，避免被人脚本化拉取分发。

## 关键风险提醒与收尾

Reality 不是银弹：2024 年 Iran MCCI 在数小时内封锁了大量以 `speedtest.net` 为 SNI 的节点，证明**"热门 SNI + 脏 IP 段"组合已进入 DPI 黑名单**。甲骨文、Vultr、Google Cloud 等重点 ASN 经常被整段封禁，搬瓦工 CN2 GIA、Hetzner、RackNerd 这类商业流量密集的段位存活率更高。把**冷门 SNI、同 ASN 邻居、非标准端口（如 8443/2053）、Cloudflare Tunnel 隐藏管理面、Vision 流控、短 connIdle 策略**五件套同时打满，才是 2026 年 Marzban 节点长期存活的底线配置。若用户基数大且监管激进，叠加 **XHTTP 或 Hysteria2 作为备用通道**，并在客户端订阅里同时下发两种协议，让用户在 Reality 被封时自动回切。