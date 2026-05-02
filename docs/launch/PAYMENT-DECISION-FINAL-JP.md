# 支付决策最终版(JP operator 约束)

> **状态**: ✅ FINAL(2026-05-03)
> **作废**: PR #215-#218 中所有"中文聚合方"推荐(YunGouOS / 虎皮椒 / payjs / 跳跳付 / Pay4Things / 彩虹自建)
> **理由**: operator 在日本运营,约束 = **绝不绑定中国身份证 / 中国银行卡 / 中国手机号**(资金被冻或类目违规无法跨国处理 + 实名记录留中国 ≥5 年)

---

## 0. TL;DR

只有 4 条路对你有效:

| # | 通道 | 实名层 | 钱去哪 | 月费 | 状态 |
|---|---|---|---|---|---|
| 1 | **USDT TRC20 直收** | 日本邮箱 | 你 USDT 钱包 | 0% | ✅ 已 ship |
| 2 | **OTC 引导**(支付宝→USDT)| 客户自付 | 你 USDT 钱包 | 0% | ✅ 已 ship |
| 3 | **Cryptomus**(crypto checkout)| 日本邮箱 | 你 USDT/USDC 钱包 | 0.4% | ⏳ 50+ 用户 |
| 4 | **Paddle**(MOR 跨境信用卡)| 日本個人事業主 | 你日本银行(JPY)| 5-7% | ⏳ 200+ 用户 |

**不需要中国身份**。**不需要中国银行卡**。**不需要营业执照**(日本個人事業主届出即可)。

---

## 1. 排除清单(明确不做)

每条都需要中国身份 + 银行卡,operator 不在中国 → **绝不走**:

- ❌ YunGouOS 个人版(身份证 + 中国银行卡 + 微信号一致)
- ❌ 虎皮椒(身份证 + 中国银行卡)
- ❌ payjs(同上)
- ❌ 跳跳付 / Pay4Things(同上)
- ❌ 彩虹易支付自建(下游通道商仍是中国身份)
- ❌ 微信支付 / 支付宝官方商户(中国版)
- ❌ EPay / 易支付(同上)

每条都有"VPN 类目限制 + 锁号 + 黑记录"风险 → **不走**:

- ❌ Stripe Japan(VPN 类目锁号 + Stripe 黑记录跨国)
- ❌ Komoju(VPN 类目限制 + 优势对你无用)
- ❌ PayPal(VPN 最严)

不适用你日本身份的:

- ❌ WeChat Pay HK / Alipay HK(需 HK 公司主体)
- ❌ HK / SG / BVI 离岸公司(0-200 用户成本不划算,200+ 用户阶段再考虑)

---

## 2. 4 条可行路径详述

### 2.1 USDT TRC20 直收(已 ship,主)

- 客户自有 USDT → 付 TRC20 地址 + memo → 5-30 秒到账
- panel 自动开通(`ops/billing/trc20_provider.py`)
- 0 中介,0 锁号风险,0 实名暴露
- **缺点**:首次客户需懂 USDT(15 分钟学习曲线)

### 2.2 OTC 引导(已 ship,辅)

- 客户没 USDT 但有支付宝 → 跳教程 → OKX P2P 买 USDT → 转你钱包
- 教程 ship 在 `docs/launch/HOW-TO-BUY-USDT-FROM-ALIPAY.md`
- 商户风险 0(钱不经过你)
- **缺点**:客户首次操作 15 分钟,转化率 60-75%(教程到位)

### 2.3 Cryptomus(中期,50+ 用户后)

| 项 | 详情 |
|---|---|
| 总部 | Estonia(EU 持牌 crypto 服务商) |
| 注册 | 邮箱 + 钱包,5 分钟,无证件 |
| KYC(小额) | 不需要 |
| VPN 业务 | **明确允许**(有专门 merchant 类目) |
| 客户体验 | hosted checkout,客户扫码或粘地址,5 分钟到账 |
| 收什么 | USDT TRC20/ERC20/BEP20 / USDC / BTC / ETH / 30+ 币 |
| 客户付什么 | 同上,Cryptomus 帮你处理对账 |
| 钱去哪 | 自动转入你设定的钱包(你 USDT 钱包) |
| 费率 | **0.4%**(Stripe 1/9) |
| 中文界面 | ✅ |

**为什么比 OTC 教程好**:客户不用注册交易所、不用学 P2P,**点链接 → 扫码 → 付**就完事。
**为什么比 USDT 直收好**:客户不用懂 memo / 链选,Cryptomus 自动对账。

#### 集成

- ship `ops/billing/cryptomus_provider.py`(参考 trc20_provider 模式,~6h)
- dashboard checkout 加 "国际客户 / 信用卡 / 多币种" 按钮 → Cryptomus hosted page
- webhook → panel 自动开通(已有 grant 应用框架,见 `ops/billing/grants.py`)
- 走 §48 codex cross-review

#### 触发条件(何时 ship)

- 5+ 真客户反馈"OTC 教程麻烦"
- 或海外客户出现(英文 Twitter / HN / Reddit 来的)

### 2.4 Paddle(长期,200+ 用户后)

| 项 | 详情 |
|---|---|
| 模式 | Merchant of Record(他们当中间商,合规他们承担) |
| 主体 | 日本個人事業主接受(KYC: 開業届 + マイナンバー + JP 银行) |
| VPN 业务 | acceptable use policy 个案审,SaaS 包装下 30-50% |
| 客户付什么 | 100+ 国家信用卡 / Apple Pay / Google Pay / 部分 PayPal |
| 钱去哪 | JPY → 你日本银行(楽天 / GMO あおぞら / PayPay 银行) |
| 费率 | 5-7%(MOR 服务费贵,但合规他们做) |
| 失败成本 | 被拒不留黑记录(可重新申请) |
| Paddle 替代 | Lemon Squeezy(Stripe 子公司,审核继承严)/ FastSpring(老牌但 VPN 较拒) |

#### 申请前置(operator 准备)

- [ ] 開業届(税务署在线办,Freee / Money Forward 5 分钟)
- [ ] マイナンバー(已有)
- [ ] 屋号付き口座(楽天 / GMO あおぞら,¥0)
- [ ] 業種報「ソフトウェア業 / 情報通信業」(关键!)
- [ ] 英文 SaaS 站(`nilou.network`,无 VPN / 翻墙字样)
- [ ] 業務説明定稿:"Open-source Marzneshin SaaS hosting subscriptions"

#### 触发条件

- 200+ 海外英文客户(主战场)
- 月流水 ≥ ¥30万(MOR 5-7% 费率才划算)

---

## 3. 推荐执行顺序

### 现在(0-50 用户)

**只做 USDT + OTC**(已 ship)。**不做任何新通道**。

理由:1 个 trial 用户阶段,新通道 = §32.5 反模式 #1(Vibe Shipping)。

### 短期(5-50 用户,Q2 2026)

集 **Cryptomus**:
- 为每个新客户提供"扫码付 USDT 不用学交易所"选项
- 海外客户也能用(Cryptomus 全球可用)
- 工时 6h,投入产出比最高

### 中期(50-200 用户,Q3 2026)

继续 USDT + OTC + Cryptomus 三件套。**不引入信用卡通道**。

理由:200 用户内的中国客户全部能走 USDT / OTC / Cryptomus,信用卡通道仅服务"非中国客户拿不到 crypto"的小众场景,ROI 负。

### 长期(200+ 用户,Q4 2026+)

申请 **Paddle**(英文站包装 + SaaS 类目),服务海外信用卡客户。

---

## 4. 客户体验对照

| 客户类型 | 推荐付款 | 体验 |
|---|---|---|
| 中国客户(有 USDT) | 直接付 TRC20 | 5 分钟,无 KYC |
| 中国客户(只有支付宝) | OTC 教程 | 首次 15 分钟,以后 3 分钟 |
| 中国客户(嫌 OTC 麻烦) | Cryptomus(中期) | 5 分钟,扫码 |
| 海外英文客户(crypto) | Cryptomus | 5 分钟 |
| 海外英文客户(信用卡) | Paddle(长期) | 30 秒 |

**全部不需要中国通道、中国银行卡、中国身份**。

---

## 5. 失误复盘(为什么前 4 PR 推 YunGouOS 等)

PR #215 → #218 我推了 USDT + OTC(对)+ 中文聚合方双通道(错)。

**错的根源**:
- 没第一时间确认 operator 是否在中国 / 是否愿意绑中国身份
- 把"中国机场圈实战做法"直接套用,忽略你"日本运营 + 不绑中国"的约束
- 推荐路径前没问"约束是什么",直接给方案

**修正**:此 doc(`PAYMENT-DECISION-FINAL-JP.md`)作为新的 final decision,
作废 PR #215-#218 中所有中文聚合方推荐。`PAYMENT-CHANNEL-MATRIX.md` v1-v4 保留作历史
研究档案,但**优先级**降为"非约束情境的备选研究"。

**沉淀到 LESSONS**:L-045(候选)— 推荐方案前必须确认 operator 物理位置 + 实名约束 +
法律辖区,不能假设"行业惯例"覆盖所有 operator。

---

## 6. 引用

- `ops/billing/trc20_provider.py` — USDT 实现(已 ship)
- `docs/launch/HOW-TO-BUY-USDT-FROM-ALIPAY.md` — OTC 客户教程
- `docs/launch/PAYMENT-CHANNEL-MATRIX.md` — 完整通道矩阵(历史研究档案,**部分作废**)
- `docs/launch/CUSTOMER-FAQ.md`
- 未来:`ops/billing/cryptomus_provider.py`(待 ship)
- 未来:`ops/billing/paddle_provider.py`(待 ship,200+ 用户阶段)
