# VPS Provider 采购指南(2026-05 当前价)

> 给运营者:从 0 到多节点机场,该买哪些 VPS。
> 配 [`ROADMAP-launch-B-to-C.md`](../ai-cto/ROADMAP-launch-B-to-C.md) 阶段规划使用。
> 价格 / region 截至 **2026-05-01**,每季度 review 一次(下次 review:2026-08-01)。
> 创建:2026-05-01 | 状态:LIVE

---

## TL;DR — Week 2 立即买什么

如果你刚开始(0-10 用户、有 1 台 Vultr Tokyo 已在跑),按以下顺序买:

1. **Hetzner Helsinki CX22**(€4.5/月)— 新 panel 主控,数据面分离首选
2. **Akamai Linode Osaka Nanode**($5/月)— marznode-2 容灾
3. (现有)**Vultr Tokyo NRT** — 改纯 marznode,不再跑 panel

**首月预算**:€4.5 + $5 + 现有 ≈ **¥110/月**(按 1 EUR ≈ 7.8 CNY / 1 USD ≈ 7.2 CNY,2026-05 估算)

> ⚠️ 汇率与价格均为 2026-05-01 估算,下单时以官网实时报价为准。Hetzner / Akamai / Vultr 都可能随时调价或调换实例命名。

详细 7 家 provider 对比见下。

---

## 7 家 Provider 完整对比

### 一表速览(按推荐度排序)

| # | Provider | Region(本项目相关) | 推荐 plan | 月价(估)| 月流量 | ASN | 支付方式 | 推荐度 | 主要用途 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Hetzner** | Helsinki / Falkenstein / Nuremberg | CX22(2 vCPU / 4 GB / 40 GB SSD)| **€4.5** | 20 TB | AS24940 | Visa / Mastercard / PayPal / Apple Pay / SEPA | ⭐⭐⭐⭐⭐ | panel 主控(分离首选)|
| 2 | **Akamai (Linode)** | Osaka / Tokyo 2 | Nanode 1 GB(1 vCPU / 1 GB / 25 GB)| **$5** | 1 TB | AS63949 | Visa / Mastercard / PayPal / Google Pay | ⭐⭐⭐⭐⭐ | marznode 日本容灾首选 |
| 3 | **Vultr** | Tokyo NRT / SJC / Singapore | Cloud Compute Regular($5)| **$5** | 1 TB | AS20473 | Visa / PayPal / 加密货币 / 支付宝(地区性)| ⭐⭐⭐⭐ | marznode 主力 |
| 4 | **Krypt** | 香港 CN2 / 美西洛杉矶 | KVM-1(1 vCPU / 1 GB / 20 GB)| **¥35**(约 $5)| 500 GB | AS35908 | 支付宝 / 银联 / USDT / Visa | ⭐⭐⭐⭐ | 香港低延迟 + 支付宝友好 |
| 5 | **Akamai (Linode) Singapore** | Singapore | Nanode 1 GB | **$5** | 1 TB | AS63949 | 同 Akamai | ⭐⭐⭐⭐ | 东南亚出口 |
| 6 | **DigitalOcean** | NYC1 / SFO3 / SGP1 | Basic Droplet | **$6** | 1 TB | AS14061 | Visa / PayPal | ⭐⭐⭐ | 美东 / 美西备选 |
| 7 | **OVH** | Frankfurt / Strasbourg / Warsaw | VPS Starter(eco)| **€4** | 不限流量 / 1 Gbps 端口 | AS16276 | Visa / PayPal / SEPA | ⭐⭐⭐ | 欧洲价格王(IP 段中国封过,慎用)|

### 为什么是这个排序?

**Hetzner 排第一**:全行业最便宜的稳定 EU VPS,€4.5/月给到 2 vCPU + 4 GB 是其他家两倍配置。AS24940 IP 段干净,中国未批量封;panel 走 CF Tunnel,即使 IP 抖动用户感知不到。唯一缺点是中国直连 ~250 ms,但 panel 不需要低延迟。

**Akamai 排第二**:Osaka 节点 ASN(AS63949)与 Vultr Tokyo(AS20473)**不同 ASN**,这是容灾的关键 — 一旦 GFW 批封一个 ASN,另一个仍活。Akamai 全球 1 TB 流量、$5 起、节点遍布东亚 / 东南亚 / 美西,是机场刚需。

**Vultr 排第三**:已知量,你已有 1 台。NRT 节点中国直连质量不错,但单 ASN(AS20473)风险大,需要 #2 容灾。

**Krypt 排第四**:**唯一真正中国友好支付的国际靠谱厂**,接支付宝 + USDT。香港 CN2 节点对中国延迟极低(~50 ms),但价格略贵 + 流量限。适合做"流媒体专线"或"低延迟出口"。

**Linode Singapore**:东南亚客户多了再上,排在 Krypt 后是因为 SG 直连中国不如 HK。

**DigitalOcean**:贵 20%、流量同 1 TB、ASN 干净,但 IP 段近年中国封过几次 ranges,做美东 / 美西备选可,不做主力。

**OVH**:€4 不限流量看起来无敌,但 AS16276 在中国 GFW 黑名单概率高,且 OVH 长期被滥用方惯坏(挖矿 / 钓鱼),IP 信誉差。仅当欧洲节点必须、且能接受随时换 IP 时考虑。

---

## 详细对比 — 每家一节

### 1. Hetzner(德国 / 芬兰)— ⭐⭐⭐⭐⭐

**价格(2026-05 估)**
- CX22:€4.51/月 + €0.006/h(2 vCPU / 4 GB RAM / 40 GB NVMe / 20 TB)
- CX32:€7.55/月(4 vCPU / 8 GB / 80 GB)
- 流量超额:€1/TB(便宜到不像话)

**优点**
- 业界最便宜的稳定 EU VPS,€4.5 价位无人能及
- IP 段 AS24940 中国未批量封(panel 走 CF Tunnel 也不直接暴露)
- 30-60 秒开通,API 完善
- 多种支付:Visa / Mastercard / Apple Pay / PayPal / SEPA
- 有免费 IPv6 + 免费快照(每月 €0.012/GB)

**缺点**
- 中国直连延迟 ~250 ms(panel 用途无影响,但**不要**用作 marznode 给中国客户)
- 不接 USDT(只接 fiat)
- 注册首充可能要求护照 + 信用卡双因素验证(中国持卡人偶发风控)
- 客服只英 / 德文

**注册 tips**
- 用境外手机号或 Google Voice;邮箱用 Gmail / ProtonMail
- 第一次充值 €10-20 试水,不要一开始就充 €100(易触发风控)
- 选 `Cloud Server`,不要 `Dedicated`(后者面向企业)
- 实例选 Helsinki(更新机房,延迟稳)或 Falkenstein(老机房,价格偶有 promo)

**适用**:**panel 分离主控(本项目首选)**,或欧洲落地节点

---

### 2. Akamai (Linode) Osaka — ⭐⭐⭐⭐⭐

**价格(2026-05 估)**
- Nanode 1 GB:$5/月(1 vCPU / 1 GB / 25 GB SSD / 1 TB)
- Linode 2 GB:$12/月(1 vCPU / 2 GB / 50 GB / 2 TB)
- 流量超额:$0.005/GB

**优点**
- ASN AS63949 与 Vultr 不同,**做日本节点容灾的天然选择**
- Osaka 节点对中国延迟 ~40-60 ms,质量与 Tokyo 相当
- 全球 11 region(Tokyo 2 / Osaka / Singapore / SFO / NYC / Mumbai 等)— 一家覆盖全球扩张
- DDoS 抵御靠 Akamai 主网,行业最强
- 1-Click 部署 / Stack Scripts / API 友好

**缺点**
- $5 入门规格只有 1 GB RAM,跑 marznode + xray 够用,但**不要**装 panel
- 部分中国 ISP(尤其北方电信)对 Linode 出口偶尔卡 — 要测后再大规模上
- 不接支付宝;USDT 限部分地区

**注册 tips**
- 注册账号选 `Personal`,不要 `Business`(后者要发票公司号)
- 首次充值会预扣 $5 验证卡,1-3 天退还
- 启用 2FA 后可领 $100 / 60 天试用 credit(2026 仍在,但额度 / 时长可能变)
- Osaka region 在控制台叫 `os-osa`,不要选成 Tokyo `ap-northeast`

**适用**:**marznode 日本容灾首选**;长期可作为美西 / 新加坡节点扩展

---

### 3. Vultr Tokyo NRT / SJC — ⭐⭐⭐⭐

**价格(2026-05 估)**
- Cloud Compute Regular $5:1 vCPU / 1 GB / 25 GB / 1 TB
- High Frequency $6:同规格但 NVMe + 更新 CPU(推荐 +$1)
- 流量超额:$0.01/GB

**优点**
- 你已经有 1 台,流程熟
- NRT 机房中国直连质量稳定(尤其联通 / 移动)
- 32 region 覆盖全球,一家可铺开
- 接 加密货币(BTC / USDT)+ 支付宝(部分地区)+ Google Pay
- 1 小时计费,实验友好

**缺点**
- AS20473 在 GFW 已知名单内,IP 偶有抖动 — 单点风险高
- Tokyo NRT 库存周期性紧张,有时新增实例要排队
- 客服响应慢(平均 24-48 h)

**注册 tips**
- 你已注册过,直接 +1 instance 即可
- 用同一账号开实例可以共享 snapshot / firewall group
- 推荐 plan:**High Frequency $6**(NVMe 更适合 xray-core 高 IOPS),不要图便宜选 Regular $5
- 如果做容灾,**第二台开在 SJC(美西硅谷),不要再开 Tokyo** — 同 region 同 ASN 等于没容灾

**适用**:**marznode 主力**(已有);US West 备份节点

---

### 4. Krypt(美西 / 香港)— ⭐⭐⭐⭐

**价格(2026-05 估)**
- KVM-1 香港 CN2:¥35-39/月(1 vCPU / 1 GB / 20 GB / 500 GB)
- KVM-2 香港 CN2:¥75/月(2 vCPU / 2 GB / 40 GB / 1 TB)
- 美西洛杉矶价格略低 ¥5-10

**优点**
- **唯一真正中国友好支付的国际靠谱厂**:支付宝 + 银联 + USDT 全接
- 香港 CN2 GIA 线路对中国延迟 ~30-50 ms,媲美国内 ECS
- 中文客服(qq / 工单)+ 支持微信沟通
- Netflix HK / 港服游戏解锁好

**缺点**
- 价格比 Hetzner / Akamai 贵 30-40%(为中国友好支付付的溢价)
- 流量限 500 GB-1 TB,超额 ¥1/GB,不如海外厂
- 商业稳定性中等(运营 10+ 年但规模小,跑路风险 > Hetzner / 但 < 国内小厂)
- 香港机房 IP 段对部分被墙网站(如某些日本流媒体)有反爬

**注册 tips**
- 官网 cloud.krypt.com,注册要中文手机号
- **先开月付**,跑通 30 天再上季 / 年付(避免一次充太多)
- 选 `KVM 香港 CN2 GIA` 不要 `KVM 香港优化`(后者是普通线路)
- 配置选 Ubuntu 24.04 LTS(他家 CentOS 镜像不维护)

**适用**:**香港低延迟出口**(流媒体 / 港服游戏 / 低延迟付费用户);**支付宝 only 客户**的备用支付通道

---

### 5. Linode (Akamai) Singapore — ⭐⭐⭐⭐

**价格(2026-05 估)**
- Nanode 1 GB:$5/月(同 Osaka 规格)
- Linode 2 GB:$12/月

**优点**
- 同 Akamai 全球网络,与 Osaka 共享账号 / API
- SG 节点对东南亚客户延迟低(20-40 ms 到马来 / 印尼 / 越南 / 泰国)
- 解锁部分 SG 流媒体(Disney+ SG / SPOTV)

**缺点**
- 中国直连延迟 ~80-100 ms,逊于 HK / NRT
- SG 政府对内容监管更严,长期合规风险略 > 日本

**注册 tips**
- 与 #2 Akamai Osaka 共用账号,无需重新注册
- region 选 `ap-south`(Singapore),不要 `ap-southeast`(已废弃)

**适用**:**东南亚客户多了再上**(B 后段 / C 阶段),不是首批必买

---

### 6. DigitalOcean — ⭐⭐⭐

**价格(2026-05 估)**
- Basic Droplet $6/月:1 vCPU / 1 GB / 25 GB / 1 TB
- $12/月:1 vCPU / 2 GB / 50 GB / 2 TB

**优点**
- 文档质量行业 top 1,新手友好
- 全球 14 region(NYC / SFO / SGP / FRA / TOR 等)
- 1-Click Apps 多;Spaces 对象存储 $5/月起
- 接 PayPal / Visa,支付简单

**缺点**
- 同规格比 Akamai / Vultr 贵 20%
- AS14061 IP 段近 2 年中国批封过几次 ranges,做主力风险高
- 不接加密货币 / 支付宝
- 小流量超额贵($0.01/GB)

**注册 tips**
- 通过 referral 链接注册可领 $200 / 60 天 credit(自行 Google "DigitalOcean referral 200")
- 启用 2FA 后送 free $5 credit
- 选 region:NYC1(美东主流)或 SFO3(美西最新机房)

**适用**:**美东 / 美西备选**;不做主力,做 cross-region 备份(防 Akamai / Vultr 全 ASN 被封)

---

### 7. OVH — ⭐⭐⭐

**价格(2026-05 估)**
- VPS Starter:€3.99/月(1 vCPU / 2 GB / 40 GB / 不限流量 / 250 Mbps)
- VPS Value:€6.99/月(2 vCPU / 4 GB / 80 GB / 1 Gbps)

**优点**
- **欧洲价格最王**,€4 不限流量行业仅有
- 1 Gbps 端口跑满 = 月吞吐 300+ TB,跑高流量节点经济
- 免费 anti-DDoS Game
- 法国 / 德国 / 英国 / 波兰 / 加拿大多 region

**缺点**
- AS16276 长期被滥用,IP 段在中国 GFW 黑名单概率高
- 客服臭名昭著(响应慢 + 法语优先)
- 注册风控严:中国持卡人首次注册被拒概率 ~50%
- 控制面板老旧,不如 Hetzner / Vultr 现代

**注册 tips**
- 注册时国家**不要选中国**(直接 reject),选 Hong Kong / Singapore
- 用 PayPal 比 Visa 通过率高
- 拿到账号后,先开 €3.99 Starter 跑 7 天看 IP 是否能正常连中国 — 不行立刻退(7 天内可全退)

**适用**:**欧洲备选**(年付高流量场景);**不做首批**

---

## 注册流程速查(每家 5 步走)

### Hetzner 注册
1. 访问 https://www.hetzner.com/cloud → 右上 `Login` → `Register`
2. 填邮箱 + 密码 + 姓名地址(地址用真实)
3. 验证邮箱(收件箱点链接)
4. 进控制台 `Billing` → `Add Payment Method` → 绑卡(预扣 €1 验证)
5. `Cloud Console` → `New Project` → `Add Server` → 选 `CX22` + `Helsinki` + `Ubuntu 24.04` + 上传 SSH key → Create

### Akamai (Linode) 注册
1. 访问 https://login.linode.com/signup
2. 填邮箱 + 密码,验证邮箱
3. `Account` → `Billing Info` → 绑卡(预扣 $5,1-3 天退)
4. 启用 2FA,领新户 credit(如有)
5. `Linodes` → `Create Linode` → 选 `Nanode 1GB` + `Osaka, JP` + `Ubuntu 24.04 LTS` + 设 root 密码 + SSH key → Create Linode

### Vultr 注册
1. 你已注册过,直接登录 https://my.vultr.com
2. 顶部 `Deploy` → `Deploy New Server`
3. 选 `Cloud Compute - High Frequency`(推荐)+ `Tokyo` 或 `Silicon Valley`
4. 选 `Ubuntu 24.04 x64` + 添加 SSH key + label 取名(如 `aegis-marznode-2`)
5. 点 `Deploy Now`,2 分钟后拿到 IP

### Krypt 注册
1. 访问 https://cloud.krypt.com → 注册(中文手机号 + 邮箱)
2. 实名认证(姓名 + 身份证后 4 位即可,合规要求)
3. 充值 ¥50(支付宝 / 微信 / USDT 三选一)
4. 控制台 `产品` → `云服务器` → 选 `KVM 香港 CN2 GIA` + `KVM-1` + `Ubuntu 24.04` + 月付
5. 等开通(通常 5-15 分钟,IP 邮件发送)

### Linode (Akamai) Singapore 注册
- 同 Akamai Osaka,只需第 5 步把 region 改为 `Singapore` (`ap-south`)

### DigitalOcean 注册
1. 通过 referral 链接访问(有 $200 credit)→ Sign Up
2. 验证邮箱 + 绑卡($1 验证)
3. 启用 2FA(送 $5)
4. `Create` → `Droplets` → `Basic` + `Regular Intel` + `$6 / 1 GB` + `NYC1` 或 `SFO3` + `Ubuntu 24.04`
5. SSH key + Hostname → Create Droplet

### OVH 注册
1. 访问 https://www.ovhcloud.com/en/vps/(语言切英文)
2. 选 `VPS Starter` → `Configure`,**国家选 Hong Kong / Singapore**(不要选 China)
3. 注册账号 + PayPal 支付(中国卡通过率低)
4. 等开通邮件(可能 1-24 h,有时审核)
5. 进 manager,改 root 密码 + 绑 SSH key

---

## 不推荐的 Provider(避坑)

### 这些不要买

- **AWS / GCP / Azure**:贵 3-5 倍 + 中国线路烂 + IP 段太大易被批量封 + 严格 ToS(检测 VPN 用途封号)
- **Bandwagon Host**:小机场首选过,但 CN2 GIA 流量贵($30 起 / 1 TB)+ 价格已涨 2 倍 + 库存常年缺货
- **RackNerd / GreenCloudVPS / 各类 LowEndBox 促销小厂**:稳定性差,长期跑路率高,价格便宜但 1-2 年内出问题概率 >30%
- **国内 ECS / 阿里云 / 腾讯云 / 华为云**:**违规 + 实名上报 + 不能跑机场**,法律风险红线,绝对不碰
- **OneProvider / Kimsufi(OVH 子品牌)**:同 OVH 缺点 + 客服更差

### 国内"中转"代理(慎)

- **某些"国内中转代理商"**:有时是境外节点用支付宝代付(中介 markup 30-50%)
- 检查 IP 实际 ASN(`whois <IP>`),不在 IP 黑名单且不是国内 ASN 才用
- 跑路风险高于直购,**永远不年付**

---

## 支付坑 + 解决方案

### Visa / Mastercard
- 中国发的卡(招行 / 中信 / 民生 visa)在 Hetzner / Vultr / Linode 通过率 70-80%
- 失败时重试方法:换 1 张行,或用 PayPal(把卡绑 PayPal 再付),或用境外发的卡(WildCard / Onekey 虚拟卡)
- 触发风控征兆:卡支付成功但账户被锁 — 联系客服发护照解锁

### 支付宝(优势:中国通道)
- **Krypt** 接(¥35/月起,fiat 价更高但无汇率损失)
- 部分**国内代理商**接(自查 ASN 真假)
- Vultr 有时接,有时不(地区性,不稳)

### USDT TRC20
- **Akamai / Vultr / Krypt** 接(2026 已普及)
- **优点**:无 KYC + 不留信用卡记录(国内运营商不知你买了 VPS)+ 手续费便宜(~¥7/笔)
- **缺点**:链上转账有 2-5 分钟延迟;转错链(发 ERC20 到 TRC20 地址)= 钱没了

### PayPal
- Hetzner / DigitalOcean / OVH 接
- 中国账号注册难,需要境外手机号 + 境外地址,但一旦绑好稳定性最高

---

## 升级路径(用户数 vs 节点配置)

| 用户数 | 配置 | 月度成本估 | 时间窗 |
|---|---|---|---|
| **0-10**(now)| 1× Vultr Tokyo NRT | ¥30 | 现有 |
| **10-50** | + Hetzner panel + Akamai Osaka | ¥110 | Week 3-5(B 阶段中)|
| **50-100** | + Krypt 香港 + Vultr SJC | ¥200 | Week 8-10 |
| **100-200** | + Linode Singapore + 1 备份 | ¥280 | Week 12+(B 阶段尾)|
| **200-1000**(C 阶段)| 6-8 节点 + panel × 2 容灾 | ¥500-800 | Q3 2026+ |

> 成本占营收比目标:< 15%。月营收 ¥3000 时基础设施 < ¥450(目前规划合规);月营收 ¥30000(C 阶段)时基础设施 < ¥4500。

---

## 一句话决策

**今天买**:Hetzner Helsinki CX22 + Akamai Linode Osaka Nanode = €4.5 + $5 ≈ **¥75/月**。Vultr 现有 Tokyo 改纯 marznode。剩下的(Krypt HK / Linode SG / 备份)等 Week 8 再加。

---

## 参考

- 阶段规划:[`docs/ai-cto/ROADMAP-launch-B-to-C.md`](../ai-cto/ROADMAP-launch-B-to-C.md)
- 客户视角(用户最在乎哪些 region):[`CUSTOMER-FAQ.md`](./CUSTOMER-FAQ.md) Q17-Q25
- 部署 runbook:`docs/ai-cto/OPS-deploy-runbook.md`
- 一键 install:`deploy/install/install.sh`(Ubuntu 24.04 + 2 vCPU + 2 GB RAM 最小)

---

## 下次更新本文档的触发条件

- 任一家 provider 调价 ≥ 20% / 改套餐结构
- 新 region 上线(如 Akamai 开 Hong Kong / Vultr 开 Taiwan)
- 现有任一家 IP 段被批量封(立即标 ⚠️ 告警)
- 每季度 review(下次:**2026-08-01**)

---

## 附录 A:下单后第一小时必做的 8 个检查

新 VPS 一开通,**立刻**跑这 8 项,不合格的当天退(多数 provider 7 天内可全退)。

### A.1 IP 可达性
```bash
# 从你国内主力网络 ping 新 IP
ping -c 20 <NEW_IP>
# 看丢包:< 1% 合格,> 5% 立刻退
# 看延迟:Tokyo / HK 应 30-80ms,EU 应 200-280ms
```

### A.2 IP 黑名单查询
- https://check.spamhaus.org/results/?query=<IP> — Spamhaus 列表
- https://www.abuseipdb.com/check/<IP> — abuse 报告数
- https://ipinfo.io/<IP> — 看 ASN / org 是否符合

**红线**:Spamhaus 已列 / AbuseIPDB > 50 reports / org 显示是 "VPN / Hosting" 但你买的是住宅 IP — 立刻换。

### A.3 GFW 黑名单实测
```bash
# 在国内主力网络从浏览器访问 https://<IP>:443(自签证书 OK,看是否 TCP 通)
curl -v -k https://<IP>:443 --connect-timeout 10
# 通 = 当前未被墙;timeout / RST = 已封
```

### A.4 端口 443 / 80 是否被滥用方提前封过
- `nmap -p 443,80,22 <IP>` 看响应 — `filtered` 或 `closed` 但 ssh 通 = 上一手用户挖矿被运营商端口封禁
- 这种 VPS **不能用**,要 provider 换 IP 或退

### A.5 反向 DNS / WHOIS 信息
```bash
dig -x <IP>
whois <IP>
```
- 反查应是 provider 的通用域(如 `*.your-server.de`)
- 不应反查到任何"VPN" / "Proxy" / "Tor"关键字 — 否则 IP 信誉差

### A.6 流媒体解锁实测(如目标客户在乎)
- 装个 docker 跑 https://github.com/lmc999/RegionRestrictionCheck
  ```bash
  bash <(curl -L -s https://raw.githubusercontent.com/lmc999/RegionRestrictionCheck/main/check.sh)
  ```
- 看 Netflix / Disney+ / YouTube Premium 是否解锁 region

### A.7 实际带宽实测
```bash
# speedtest CLI
curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python3 -
# 期望:Tokyo / HK / SG 节点应能到 500+ Mbps;EU 节点 200+ Mbps
```

### A.8 系统盘 IO 实测
```bash
# 写入 1 GB 测 IOPS
dd if=/dev/zero of=/tmp/test bs=1M count=1024 conv=fdatasync
# 期望:NVMe 盘 > 500 MB/s;SSD > 200 MB/s;< 100 MB/s 退
rm /tmp/test
```

**8 项任一不合格 → 当天退款换。绝对不要凑合,VPS 是底盘,底盘烂上面什么都救不了。**

---

## 附录 B:多节点采购顺序(手把手)

如果你严格按本指南走,采购顺序应该是:

### 第一批(Week 2,B 阶段启动)
| # | Provider | Region | Plan | 用途 | 月价 |
|---|---|---|---|---|---|
| 1 | Hetzner | Helsinki | CX22 | panel 主控 | €4.5 |
| 2 | Akamai (Linode) | Osaka | Nanode 1GB | marznode 容灾 | $5 |
| 3 | (现有)Vultr | Tokyo NRT | $5 / High Freq $6 | marznode 主力 | $6 |

**小计**:≈ ¥110/月

### 第二批(Week 8,有 50+ 用户后)
| # | Provider | Region | Plan | 用途 | 月价 |
|---|---|---|---|---|---|
| 4 | Krypt | 香港 CN2 | KVM-1 | 低延迟出口 / 流媒体 | ¥35 |
| 5 | Vultr | Silicon Valley | High Freq $6 | 美西节点(GPT/Claude)| $6 |

**小计**:≈ ¥190/月

### 第三批(Week 12+,100+ 用户后)
| # | Provider | Region | Plan | 用途 | 月价 |
|---|---|---|---|---|---|
| 6 | Linode | Singapore | Nanode | 东南亚出口 | $5 |
| 7 | Hetzner | Falkenstein | CX22 | panel 备份 / 监控 | €4.5 |

**小计**:≈ ¥280/月

### C 阶段(Q3 2026+,200+ 用户)
| # | Provider | Region | Plan | 用途 | 月价 |
|---|---|---|---|---|---|
| 8 | OVH 或 DigitalOcean | Frankfurt / NYC | 8 GB | 欧美专线 | $12-€15 |
| 9 | Akamai | Mumbai 或 Sydney | Nanode | 印度 / 澳洲扩展 | $5 |

**小计**:≈ ¥500-800/月

---

## 附录 C:每季度 review checklist

每 3 个月跑一次本 checklist,更新本文档:

- [ ] 7 家 provider 当前价是否变动 ≥ 20%?
- [ ] 新增 region?(Akamai / Vultr 每年扩 2-3 个)
- [ ] 现有节点 IP 段在过去 90 天是否被批量封过?
- [ ] 你客户调研:延迟差 / 流媒体抱怨集中在哪个 region?
- [ ] 汇率波动:USD/EUR vs CNY 变动 > 5%?
- [ ] 是否有新供应商值得评(标准:中国友好 + 价格 ≤ ¥40 + ASN 干净 + 至少 5 年运营)?

review 完更新本文表格,commit 一条 `docs(launch): VPS-PROCUREMENT review YYYY-QN`。

---

## 附录 D:与现有架构的对接

下单完成后,下一步是把新 VPS 接入 aegis-panel 多节点架构。这部分参考:

- **panel 分离部署**:`docs/ai-cto/OPS-deploy-runbook.md` §"panel-only 模式"
- **新 marznode 接入**:控制台 → `Nodes` → `+ Add Node` → 填新 VPS IP + 上传 marznode 公钥
- **Reality SNI 选型**:每个新 region 跑一次 `/cto-skills sni-selector`(同 ASN 邻居不同,SNI 必须重选)
- **CF Tunnel 配置**:仅 panel 主控需要 CF Tunnel;marznode 直连用户(443 端口)
- **AGPL 自检**:新 VPS 上跑 `bash deploy/agpl-selfcheck.sh` 确认源码披露入口可达

---

## 附录 E:法律 / 合规一句话

- 你买的是境外 VPS,**租用关系合法**;在 VPS 上跑 marznode + Reality 也合法(开源软件)
- **VPS 不要登记成你公司名义**(如有公司),用个人账号
- **不要在 VPS 上同时跑明显违法用途**(挖矿暗网 / 盗版 CDN / 钓鱼)— 会被 provider 封号牵连机场
- 如有公司 / 团队,签一份 service agreement 与你 VPS 账号分离,降低连带风险

完整法律边界见 `docs/ai-cto/DECISIONS.md` D-003。
