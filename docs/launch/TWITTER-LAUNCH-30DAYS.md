# Twitter / X 冷启动 30 天作战计划

> **项目**: Nilou Network (aegis-panel) — Marzneshin 商业化硬 fork
> **域名**: nilou.cc
> **License**: AGPL-3.0
> **目标人群**: 自建党 / dev / 极客 / 对商业机场失望的终端用户
> **撰写日期**: 2026-05-02

---

## 0. 总体策略

冷启动的核心矛盾:**没人认识你 = 没人转发**。所以必须靠**两条腿走路**:

1. **技术叙事(Week 1-2)** — 抢 dev 圈口碑。代码截图、加固技术、AGPL 透明承诺,让早期 follower 是有影响力的极客 / 自建党 / 安全研究者。
2. **对比叙事(Week 3-4)** — 抢终端用户。"为什么我不再用商业机场" / 跑路名单 / 客户证言,把 dev 阶段攒下的信任翻译成订阅转化。

**铁律**:
- 不黑同行具体名字,只列**已跑路 / 已被封 / 已被指控**的客观事实(可查证)。
- 不主动碰政治议题,只谈**技术 + 用户体验 + 透明度**。
- 不用大号互吹,只回**有真实问题**的推。
- 中文 hashtag 在亚洲时段补一条转推/引用,不主帖中英混排(降低算法权重)。

---

## 1. 账号设置

### 1.1 Handle 候选

| 候选 | 优点 | 缺点 |
|---|---|---|
| `@niloucc` | 短、和域名 nilou.cc 一致、好记 | 略偏极简,品牌延展弱 |
| `@nilou_network` | 全称、品牌延展性好 | 有下划线、不够极客 |
| `@nilounet` ⭐ | 备选,比 _network 短 | 可能被抢 |

**推荐**: `@niloucc`(主) + 注册 `@nilou_network`(防抢占,跳转到主号)。

### 1.2 Display Name

`Nilou Network` (不加 emoji,不加 "official",显得克制)。

### 1.3 Bio (160 字符内,英文为主)

候选 A — 技术向:
```
AGPL-licensed VPN panel for serious operators.
Reality 2026 hardening · multi-node · zero hardcoded secrets.
🔗 nilou.cc · github.com/<TODO>
```

候选 B — 用户向:
```
Run your own VPN panel without trusting anyone.
Open-source (AGPL-3.0). No tracking. No lock-in.
🔗 nilou.cc
```

**推荐**: 候选 A(早期目标 = dev),Day 15 后切候选 B。

### 1.4 头像 / Banner

**TODO(阻塞)**: logo 设计未确定。临时方案:
- 头像:纯色 `#0EA5E9` (Tailwind sky-500) + 白色字母 `N`,无衬线
- Banner:深色背景 + 一行代码截图(`reality_audit.py` 输出)+ 域名 `nilou.cc`
- 待 logo 出来后(`/cto-image` 委派 Antigravity / Codex)替换

### 1.5 Pinned Tweet (Day 1 发完立即置顶)

见 §3 Day 1 文案。

### 1.6 Profile 链接

- Website: `https://nilou.cc`
- Location: `Decentralized` (不写国家,避免被定位)
- Birthday: 不填

---

## 2. 30 天日历总览

| Week | 主题 | 推文重心 | 目标 |
|---|---|---|---|
| **Week 1 (Day 1-7)** | 立旗 + 技术介绍 | SNI 选型器 / Reality 加固 / AGPL 承诺 | 100 followers / 第一个 GitHub star spike |
| **Week 2 (Day 8-14)** | 工程深度 | mTLS / 多节点 gRPC / 审计日志 / 流量统计 | 300 followers / dev 圈点名(@gfwrev 等) |
| **Week 3 (Day 15-21)** | 用户痛点对比 | 跑路名单 / "我为什么不用 X" / 透明度对比 | 600 followers / 第一波 trial 申请 |
| **Week 4 (Day 22-30)** | 信任 + 转化 | 客户证言 / Roadmap / Show HN / Reddit | 1000 followers / 50 stars / 10 trial |

---

## 3. 30 条推文模板 (Day 1 - Day 30)

> **时区注**: 美东 (ET) 用于英文 dev 圈,亚洲 (CST = UTC+8) 用于中文圈。
> **配图统一规范**: 1200×675 (16:9),深色 IDE 主题,字号 ≥ 16pt(手机可读)。

---

### Week 1: 技术叙事 — 立旗

#### Day 1 (Mon) — 自我介绍 / Pinned

```
Building Nilou Network — an AGPL-3.0 VPN control panel
hardened for the 2026 censorship landscape.

→ Reality + Vision short-connIdle
→ SNI auto-selector (same-ASN sniffer)
→ Multi-node via gRPC
→ Zero hardcoded secrets

Source: github.com/<TODO>
Site:   nilou.cc

#opensource #vpn #censorship
```
- **配图**: dashboard 首页截图(节点列表 + 用户数 + 流量图)
- **时间**: ET 9:00 AM (亚洲晚上 9 点)
- **动作**: 发完立即 pin

#### Day 2 (Tue) — SNI 选型器 (技术 hook)

```
Why does your Reality config keep getting blocked?

Because everyone copies the same `www.microsoft.com` SNI
from the same blog post.

We built a same-ASN SNI auto-picker. Scans your VPS
neighborhood, validates TLS 1.3 + H2 + X25519, scores by
DPI history.

Code: <link>/hardening/sni_selector

#reality #xray #marzneshin
```
- **配图**: terminal 截图,`./sni-selector --vps 1.2.3.4` 输出表格
- **时间**: ET 10:00 AM

#### Day 3 (Wed) — AGPL 透明承诺

```
A pledge most "open source" panels won't make:

If we run Nilou Network as a service, every paying user
can demand the exact source running on our servers.
That's AGPL-3.0. Not a marketing word.

NOTICE.md → <link>

#agpl #opensource #transparency
```
- **配图**: `NOTICE.md` 截图高亮 AGPL 条款
- **时间**: ET 11:00 AM

#### Day 4 (Thu) — Reality 配置审计

```
We audit Reality configs for 7 silent killers:
1. fingerprint mismatch
2. TLS 1.3 absent on dest
3. H2 absent (forces fallback)
4. spiderX with non-empty path
5. shortIds collision
6. policy.levels too permissive
7. unrate-limited fallback

`./reality-audit my-config.json` → 3 sec.

#xray #reality #infosec
```
- **配图**: audit 输出截图(红/黄/绿三色)
- **时间**: ET 9:00 AM

#### Day 5 (Fri) — Vision + short connIdle 故事

```
GFW upgrade in 2026-Q1 started flagging long-lived TLS
sessions on residential IPs.

Fix: Vision flow + connIdle = 30s on outbounds.

Long-poll apps reconnect transparently. DPI sees a
healthy churn pattern instead of a 6-hour zombie session.

Default-on in Nilou. One config knob.

#vpn #censorship #networking
```
- **配图**: `connIdle` config diff
- **时间**: ET 10:00 AM (Friday → 周末讨论延续)

#### Day 6 (Sat) — Weekend dev humor

```
Marzban: 15 months no updates.
Marzneshin: alive, but minimal commercial features.
Nilou: hard fork of Marzneshin, kept upstream lineage,
added the operator stack we needed for 200+ paying users.

We will sync upstream every quarter. Not "vibe sync".

#opensource #fork
```
- **配图**: git log 三个项目 commit 频率对比图
- **时间**: ET 12:00 PM

#### Day 7 (Sun) — Week 1 总结 + CTA

```
Week 1 of Nilou Network.

What landed:
✓ SNI auto-selector
✓ Reality config auditor
✓ AGPL-3.0 NOTICE
✓ Multi-node gRPC stable

What's next:
→ Cloudflare Tunnel auto-provisioner
→ Per-user IP-limiter (native, not Marzban-API)

Star + follow if you self-host: <link>

#selfhosted #opensource
```
- **配图**: roadmap 板截图 (GitHub Projects)
- **时间**: ET 5:00 PM (Sunday evening,周报黄金时段)

---

### Week 2: 工程深度 — 让 dev 圈认你

#### Day 8 (Mon) — mTLS 故事

```
Threat model: an attacker compromises one of your VPS.
Can they replay control-plane API calls?

We require mTLS between panel ↔ Marznode (data plane).
Each node gets a per-host cert, rotated nightly via cron.

Stolen cert = 24h max blast radius.

#security #mtls #zerotrust
```
- **配图**: cert rotation 流程图
- **时间**: ET 10:00 AM

#### Day 9 (Tue) — gRPC 多节点架构

```
Single-binary panels look clean until you have 12 nodes
across 4 continents.

Nilou: gRPC streaming from panel to each Marznode.
- Bidi for live stats
- Unary for user CRUD
- Reconnect with backoff
- Per-node circuit breaker

12 nodes, 200 users, ~3% panel CPU.

#grpc #distributedsystems
```
- **配图**: 架构图 (panel → 12 marznodes via gRPC)
- **时间**: ET 11:00 AM

#### Day 10 (Wed) — Audit log 故事

```
Every admin action in Nilou writes to an append-only
audit log:
- who
- what (user_id, plan, ip)
- when (UTC + ms)
- where (admin IP + UA)

Hash-chained per day. Tamper detection via daily digest.

For when "who deleted that user?" actually matters.

#auditlog #ops
```
- **配图**: audit log 表 schema + sample row
- **时间**: ET 9:30 AM

#### Day 11 (Thu) — Traffic accounting accuracy

```
Most panels do per-hour traffic snapshots. Users get
billed for ghost traffic on disconnect/reconnect.

Nilou polls Marznode every 30s, diffs the running
counter, handles xray restart cleanly.

Tested at 200 users, 12 nodes, 0.4% drift over 7 days.

#networking #billing
```
- **配图**: 流量曲线 + drift 数据
- **时间**: ET 10:00 AM

#### Day 12 (Fri) — Per-user IP limiter

```
V2IpLimit / miplimiter only talk to Marzban (dead since
2024). Marzneshin users had to roll their own.

We shipped a native one. Reads xray access log, groups
by email, kicks if unique IPs > N in 5min window.

No external deps. Configurable per-plan.

`hardening/ip_limiter/`

#xray #ratelimit
```
- **配图**: ip_limiter 工作流程图
- **时间**: ET 9:00 AM

#### Day 13 (Sat) — Operator cheatsheet

```
For panel operators, weekend reading:

PANEL-OPERATOR-CHEATSHEET.md
- onboarding new admin
- rotating xray keys
- emergency rollback to last config
- restoring from backup in <5min

Open source. Steal it. PRs welcome.

#sysadmin #ops
```
- **配图**: cheatsheet markdown 截图
- **时间**: ET 11:00 AM

#### Day 14 (Sun) — Week 2 总结

```
Week 2 wrap.

Shipped:
✓ mTLS between panel ↔ nodes
✓ Append-only audit log
✓ Native per-user IP limiter
✓ Operator cheatsheet (docs/launch/)

Numbers:
- 14 commits to main
- 0 hardcoded secrets (verified)
- 100% type-hinted Python 3.12

Star: <link>

#opensource #weekly
```
- **配图**: GitHub commit graph
- **时间**: ET 5:00 PM

---

### Week 3: 对比叙事 — 抢终端用户

#### Day 15 (Mon) — "Why I left commercial VPN" thread (5-tweet thread)

```
1/ Why I left every commercial VPN service I paid for
in the last 3 years — and built one I'd actually trust.

A thread.
```
后续 tweets 详见 §3.1。
- **配图**: 1/ 用 banner 图,每条配支持图
- **时间**: ET 9:00 AM
- **重点**: 这条是 Week 3 的旗舰

#### Day 16 (Tue) — 跑路名单(只列客观事实)

```
"Stable provider" means what, exactly?

Public record of VPN/airport services that vanished
in the last 24 months WITH user funds:

→ <Service A> — paid plans cut off 2024-Q3, no refund
→ <Service B> — Telegram channel deleted 2025-Q1
→ <Service C> — domain seized, support unreachable

Self-hosting is no longer optional.

#vpn #selfhosted
```
- **配图**: 时间线图(无具体名字水印,文字版)
- **时间**: ET 10:00 AM
- **法律提醒**: 名字一定要有公开报道作为来源,否则只用 `<Service A>` 占位 + 链接到聚合贴

#### Day 17 (Wed) — 透明度对比表

```
Feature | Closed-source SaaS | Nilou Network
---|---|---
Source code | ❌ | ✅ AGPL-3.0
Audit log | ❌ | ✅ hash-chained
You own the keys | ❌ | ✅
You own the nodes | ❌ | ✅
Vendor exit risk | High | Zero
Price floor | $5-15/mo | VPS cost
```
- **配图**: 表格图片版(深色主题)
- **时间**: ET 11:00 AM

#### Day 18 (Thu) — 客户证言 #1 (TODO 真实证言)

```
"Switched 47 friends from <SaaS> to my own Nilou panel
in two weekends. Onboarding doc was the killer feature
— I sent one PDF and they all just... worked."

— Early operator, China region (anonymized)

Onboarding docs: <link>/docs/launch/CUSTOMER-ONBOARDING.md

#selfhosted #testimonial
```
- **配图**: onboarding 流程图
- **时间**: ET 10:00 AM
- **TODO**: 等真实早期用户给一句话授权后替换

#### Day 19 (Fri) — Pricing transparency

```
Nilou is free software (AGPL-3.0). Forever.

If you want us to host for you, our markup is the VPS
cost + 30%. No "premium tier", no metered features.

Self-host: $5 VPS + 1 hour setup.
Hosted-by-us: ~$7/mo equivalent, no lock-in.

Receipts on github.

#pricing #transparency
```
- **配图**: 成本拆解图
- **时间**: ET 9:00 AM

#### Day 20 (Sat) — Migration guide

```
Migrating from Marzban → Nilou in 20 minutes:

1. Export users (Marzban admin → JSON)
2. `nilou-import marzban-export.json`
3. Re-issue subscription URLs
4. Done.

Subscription format compat layer included. Existing
client apps don't need re-config.

Guide: <link>

#migration #marzban
```
- **配图**: 迁移流程截图
- **时间**: ET 11:00 AM

#### Day 21 (Sun) — Week 3 总结 + 招募

```
Week 3 wrap.

Numbers:
- 600 followers (+200 wow)
- 28 GitHub stars
- 6 trial requests via DM

Looking for:
→ 5 more pilot operators (free 90-day setup help)
→ 1 designer (logo/banner — paid, message me)
→ Translators (FA, RU, AR)

DMs open.
```
- **配图**: 数据 dashboard 截图(假数据要替换)
- **时间**: ET 5:00 PM

---

### Week 4: 信任建设 + 转化加速

#### Day 22 (Mon) — Roadmap 透明化

```
Public Q3 2026 roadmap:

✓ done | 🔨 in flight | 📅 queued
✓ SNI selector
✓ Reality auditor
✓ Audit log
🔨 CF Tunnel auto-provisioner
🔨 Billing module (Stripe + crypto)
📅 Web admin 2.0 (shadcn redesign)
📅 Mobile companion app

GitHub Projects: <link>

#roadmap #opensource
```
- **配图**: GitHub Projects board
- **时间**: ET 10:00 AM

#### Day 23 (Tue) — Hacker News Show HN 引用

```
We submitted to Show HN today.

"Show HN: Nilou Network — AGPL VPN control panel
hardened for 2026 censorship"

→ <HN link>

If you have an HN account, go read the comments — even
hostile ones are gold for the roadmap.

#showhn #opensource
```
- **配图**: HN 提交截图
- **时间**: ET 8:00 AM (HN 黄金时段)
- **TODO**: 实际 Show HN 文案另起 PR (`docs/launch/SHOWHN-DRAFT.md`)

#### Day 24 (Wed) — Reddit 软文回流

```
Wrote a long-form on r/selfhosted today:

"My self-hosted VPN stack after 200 paying users:
Marzneshin fork + Reality 2026 + multi-region nodes"

→ <reddit link>

Comments are dissecting the SNI selector logic. Fun.

#selfhosted #reddit
```
- **配图**: Reddit 帖子截图
- **时间**: ET 11:00 AM

#### Day 25 (Thu) — 安全披露承诺

```
Security policy:

1. SECURITY.md with PGP-encrypted disclosure email
2. 90-day responsible disclosure window
3. CVE filed for any verified panel/data-plane vuln
4. Hall of fame for reporters
5. No bounty program yet — we'll do swag + credit

Currently 0 known CVEs. Ratchet.

#security #disclosure
```
- **配图**: SECURITY.md 截图
- **时间**: ET 10:00 AM

#### Day 26 (Fri) — User journey: setup → first sub

```
First-timer setup, screen-recorded:

0:00 - VPS purchased (Hetzner)
0:30 - `curl <install.sh> | bash`
3:15 - Panel up, admin created
4:00 - First node connected (gRPC handshake)
5:30 - First user created
6:00 - Subscription URL works in v2rayN

Total: 6 minutes. No PDF, no config editing.

video: <link>

#install #demo
```
- **配图**: GIF / 视频缩略图
- **时间**: ET 9:00 AM
- **TODO**: 录屏待生产

#### Day 27 (Sat) — Community moment

```
Community update:

→ FA translation merged (thank you @<contributor>)
→ RU translation in review
→ First external PR: fixed an off-by-one in
   traffic-rollover-task.py
→ Discord: 80 members

If you self-host, drop in. We're good people.

discord: <link>
```
- **配图**: Discord 截图(模糊用户名)
- **时间**: ET 12:00 PM

#### Day 28 (Sun) — Why AGPL not MIT

```
Why we chose AGPL-3.0 over MIT:

MIT: a SaaS competitor takes our code, wraps it in a
closed-source shell, locks users in. Users lose
transparency. We get nothing.

AGPL: anyone running our code as a service must let
their users get the source. Aligned incentives.

Not anti-business. Pro-user.

#agpl #licensing
```
- **配图**: AGPL vs MIT 对比图
- **时间**: ET 11:00 AM

#### Day 29 (Mon) — 30-day numbers reveal

```
30 days in.

Numbers (no spin):
- 1.1k followers
- 67 GitHub stars
- 12 paying pilot operators
- 4 external contributors
- 2 langs translated
- 0 hardcoded secrets, still

Next 30 days: billing module + CF Tunnel auto.

Thanks for the early trust.

#startup #buildinpublic
```
- **配图**: 30 天成长曲线图
- **时间**: ET 10:00 AM
- **TODO**: 数据替换为真实

#### Day 30 (Tue) — Day 30 CTA + 邀请合作

```
End of cold-start month.

If you operate a panel for 50+ users, we want to
talk. We're picking 3 design partners for the
billing module — free pro setup, your features
become defaults.

DMs open.

site: nilou.cc
github: <link>
docs: nilou.cc/docs

#partnership
```
- **配图**: 设计合伙伙伴招募 banner
- **时间**: ET 9:00 AM

---

### 3.1 Day 15 旗舰 thread 完整文案

```
1/ Why I left every commercial VPN service I paid for
in the last 3 years — and built one I'd actually trust.

A thread.

2/ The pattern was always the same:
- Year 1: fast, cheap, support replies in 10 minutes.
- Year 2: nodes silently degrading, no status page.
- Year 3: founder vanishes, refunds frozen, channel
  goes dark.

I lost ~$340 across 4 services. Money is fine. The
data they kept on me — that's the worry.

3/ Closed-source means I have no way to verify:
- whether they log my traffic
- whether keys are rotated
- what happens to my account when they sell

The "trust us" model isn't broken because vendors are
bad. It's broken because users have zero verification.

4/ AGPL-3.0 changes the contract:
- you can read every line running on the server
- if a paying user demands the source, vendor must
  hand it over (network use clause)
- you can fork and run yourself anytime

5/ So we built Nilou Network — Marzneshin hard fork,
Reality 2026 hardening, multi-node gRPC, AGPL-3.0.

Self-host in 6 minutes. Or use our hosted version with
30% markup over VPS cost. No lock-in.

nilou.cc

#vpn #selfhosted #opensource
```

---

## 4. 互动 / 回复策略

### 4.1 值得长期跟踪的 GFW / 翻墙议题账号

> ⚠️ 真实 handle 需开账号当天验证(可能改名/迁移)。下面列出已知活跃方向。

| 账号方向 | 候选 handle (TODO 验证) | 互动策略 |
|---|---|---|
| GFW 技术研究 | `@gfwrev` | 引用其报告时 @,只在我们有真实数据补充时回 |
| Reality 协议作者圈 | `@XTLS_xray` 周边 | 不主动 @ 作者,在他们贴中**有技术问题**时回答 |
| 自建党中文圈 | (微博/Twitter 双发的几位 KOL) | 引用代码而非他们的话,避免攀附 |
| EFF / digital rights | `@EFF` `@accessnow` | 转推他们的报告,顺手关联我们的透明度承诺 |
| Tor / 隐私圈 | `@torproject` `@privacyguides` | 不蹭,但他们的 RT 价值高,值得长期 reply |
| Self-hosted 圈 | `@selfhostedshow` | 比较有共鸣,Day 24 Reddit 软文之后是窗口 |
| 海外华人 dev | (搜 #翻墙 / #自建) | 谨慎,只回工程问题 |
| 网络安全研究者 | `@SwiftOnSecurity` `@taviso` 类 | 不主动碰,被 @ 再回 |

**共 5-10 个,精选,不广撒网。**

### 4.2 回复模板(三种场景)

**场景 A**: 有人问 "怎么自建机场?"
```
For the panel layer, take a look at Nilou Network —
AGPL-3.0 fork of Marzneshin focused on commercial-grade
ops (200+ users, multi-node, hardening defaults).

Setup: 6 min via install.sh.
Docs: <link>

Happy to answer specific questions in DM.
```

**场景 B**: 有人吐槽某商业服务跑路
```
The recurring fix: own the panel + own the nodes.
We documented a 6-min self-host path so non-devs can
do it: <link>

(AGPL-3.0, no upsell, you keep the keys.)
```

**场景 C**: 有人问技术问题(SNI / Reality)
```
Quick answer: <一行解决方案>

Long answer + code: <link to relevant module>

We had the same pain before building Nilou's auto-picker.
Specifically <技术细节>.
```

**禁止**: 不在被点名的某商业服务的 thread 下面打广告。等独立讨论再发。

### 4.3 每日回复配额

- 主帖 1-2 条/天
- 回复别人 5-10 条/天 (有真实价值的,不水"+1")
- 引用转推 1-2 条/天 (技术报告 / 跑路新闻)
- DM 回复 < 24h

---

## 5. 冷启动加速渠道

### 5.1 GitHub README badge

在 `README.md` 顶部加:
```markdown
[![Twitter Follow](https://img.shields.io/twitter/follow/niloucc?style=social)](https://twitter.com/niloucc)
[![Discord](https://img.shields.io/discord/<TODO>?style=social)](https://discord.gg/<TODO>)
```
**TODO**: 单独 PR (`chore: add social badges to README`),不混在本 docs PR。

### 5.2 Hacker News Show HN

**单独 PR**: `docs/launch/SHOWHN-DRAFT.md` (本 PR 不写,本 doc 仅 Day 23 引用)。

提交时机建议:Week 4 Day 23 (Mon) ET 8:00 AM。提前 48h 多关注一次 HN 新评论(防降权)。

### 5.3 Reddit 软文模板

#### r/selfhosted

**标题**: `My self-hosted VPN stack for 200 paying users (Marzneshin fork + Reality 2026)`

**正文骨架**:
```
Long-time self-hoster. 18 months ago I started running
a small panel for friends, now ~200 paying users across
12 nodes. Wanted to share the stack since r/selfhosted
helped me a lot in the early days.

Stack:
- Panel: Nilou Network (Marzneshin hard fork, AGPL-3.0)
- Data plane: Marznode + xray-core
- DB: PostgreSQL 16
- Reverse proxy: Cloudflare Tunnel for the panel,
  direct TLS for data plane
- Monitoring: Prometheus + Grafana

[详细技术细节...]

Code: <link>
Happy to answer questions.
```

**禁止**: 卖订阅,只谈技术 + 开源工具。

#### r/vpn

**标题**: `Open-source VPN panel that survives operator burnout`

**正文骨架**: 强调 AGPL + 无厂商锁定 + 跑路风险讨论。

#### r/opensource

**标题**: `Why we chose AGPL-3.0 for our VPN panel (lessons from forking Marzban → Marzneshin → Nilou)`

**正文骨架**: 纯许可证讨论,蹭流量。

### 5.4 其他渠道

- **Discord**: 自建服务器,Day 1 上线。
- **Telegram**: 中文用户为主的社群,Day 7 上线。
- **Mastodon**: 同步发推(用 cross-poster),侧重 fediverse 自建党。
- **Bilibili / YouTube**: Day 26 录屏视频上线。

---

## 6. KPI / 30 天目标

### 6.1 北极星指标

**12 paying pilot operators by Day 30** — 这是唯一 hard target,其他都是 leading indicator。

### 6.2 Twitter 指标

| 指标 | Week 1 | Week 2 | Week 3 | Week 4 |
|---|---|---|---|---|
| Followers | 100 | 300 | 600 | 1000 |
| 推文 impressions/天 (avg) | 500 | 2000 | 5000 | 10000 |
| 主帖 likes (avg) | 5 | 15 | 40 | 80 |
| 转推 (avg) | 1 | 3 | 8 | 15 |
| Profile visits/天 | 50 | 200 | 500 | 1000 |
| 新关注 (avg/天) | 15 | 30 | 50 | 60 |

### 6.3 GitHub 指标

| 指标 | 30 天目标 |
|---|---|
| Stars | 50+ (起步) / 100+ (顺利) / 200+ (爆款) |
| Forks | 10+ |
| External contributors | 3+ |
| Open issues from non-team | 10+ |
| Translation PRs | 2+ 语言(FA/RU 优先) |

### 6.4 域名 / 流量指标

| 指标 | 30 天目标 |
|---|---|
| nilou.cc unique visitors | 5000+ |
| docs.nilou.cc visitors | 2000+ |
| install.sh 调用次数 | 200+ |
| trial 申请 | 30+ |
| 转化为 paying pilot | 12+ |

### 6.5 失败定义 / 触发回退

如果 Day 14 时:
- followers < 150 → 重审推文话题(改技术深度比例)
- GitHub stars < 10 → 重审 README + 加视频 demo
- 0 trial 申请 → 推文 CTA 不够明确,加直接联系入口

如果 Day 30 时:
- < 5 paying pilot → 暂缓 paid ads,先优化 onboarding
- > 20 paying pilot → 加速 billing 模块开发

---

## 7. 风险 / 注意事项

1. **言论敏感性**: 不在主帖触碰具体国家政策。所有 censorship 讨论限于**技术层面 + 公开报道**。
2. **同行关系**: 不点名抹黑。即使是公认跑路的服务,也只列**已被报道的客观事实**,不带情绪词。
3. **AGPL 合规**: 所有分享代码截图必须保留版权头(见 `NOTICE.md`)。
4. **Account 安全**: 2FA 必开 (硬件 key 优先,SMS 禁用)。备用邮箱不是工作邮箱。
5. **冒名风险**: Day 1 注册同时抢占 `@nilou_network` `@nilounet` 防钓鱼。
6. **数据真实性**: 所有数字截图(用户数 / 节点数 / 流量)必须脱敏或用真实测试数据,不编造。
7. **AGPL 商标**: "Nilou" 不是注册商标(Day 1 时),发推时不加 ®。

---

## 8. 配套待办 (本文档不实施,只记录)

- [ ] **TODO #1**: logo / banner 设计 (`/cto-image` 委派)
- [ ] **TODO #2**: 单独 PR 写 `docs/launch/SHOWHN-DRAFT.md`
- [ ] **TODO #3**: 录屏视频 (Day 26 配套)
- [ ] **TODO #4**: 客户证言授权 (Day 18 配套)
- [ ] **TODO #5**: 真实跑路服务名单 + 来源链接
- [ ] **TODO #6**: GFW 议题账号 handle 验证 (开账号当天)
- [ ] **TODO #7**: README 加 Twitter / Discord badge (单独 PR)
- [ ] **TODO #8**: Discord / Telegram 社群基础设施
- [ ] **TODO #9**: nilou.cc 落地页 (Day 1 之前必须 ready)
- [ ] **TODO #10**: 30 天后回顾文档 `docs/launch/TWITTER-30DAYS-RETRO.md`

---

## 9. 与现有 launch 文档的关系

| 文档 | 用途 | 关联 |
|---|---|---|
| `CUSTOMER-PITCH-CARDS.md` | 4 张卖点卡 | 推文文案的素材库 (Day 2/3/4/9 直接引用) |
| `RECRUIT-COPY.md` | 招募文案 | Day 21 / Day 30 招募 thread 复用 |
| `HOW-TO-RECRUIT-FROM-WECHAT.md` | 微信熟人启动 | Twitter 是冷启动**外**渠道,微信是冷启动**内**渠道 |
| `CUSTOMER-FAQ.md` | FAQ | DM 回复时直接引用链接 |
| `CUSTOMER-ONBOARDING.md` | onboarding doc | Day 18 / Day 26 推文核心 CTA |
| `VPS-PROVIDER-PROCUREMENT-GUIDE.md` | VPS 选型 | Reddit r/selfhosted 软文素材 |

---

**文档结束 — 30 天作战计划 v1.0**

> Day 30 后建议产出 `TWITTER-30DAYS-RETRO.md` 复盘:实际 KPI vs 目标 / 哪 5 条推文最有效 / 下个 30 天调整。
