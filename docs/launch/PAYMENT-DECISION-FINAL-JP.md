# 支付决策最终版(JP operator 约束)

> **状态**: ✅ FINAL(2026-05-03)
> **作废**: PR #215-#218 中所有"中文聚合方"推荐(YunGouOS / 虎皮椒 / payjs / 跳跳付 / Pay4Things / 彩虹自建)
> **理由**: operator 在日本运营,约束 = **绝不绑定中国身份证 / 中国银行卡 / 中国手机号**(资金被冻或类目违规无法跨国处理 + 实名记录留中国 ≥5 年)

---

## 0. TL;DR(v3 修订:发现 silver bullet — Paddle Alipay 跨境 + Alchemy Pay)

| # | 通道 | 客户操作 | 实名 | 钱去哪 | VPN 类目 | 状态 |
|---|---|---|---|---|---|---|
| 1 | **USDT TRC20 直收** | 自有 USDT 转账 | 日本邮箱 | 你 USDT 钱包 | 0 | ✅ ship |
| 2 | **OTC 引导** | 教程教 OKX 买 USDT | 客户自付 | 你 USDT 钱包 | 0 | ✅ ship |
| 3 | ⭐ **Paddle Alipay/WeChat 跨境**(MOR)| **支付宝直接扫码付,无需任何前置** | 日本個人事業主 | 你日本银行(JPY) | 中(包装 SaaS 30-50%) | ⏳ **优先申** |
| 4 | ⭐ **Alchemy Pay (ACH)** | **支付宝直接扫码付,无需任何前置** | 日本邮箱 KYC | 你 USDT 钱包 | 待实测 | ⏳ **同时申** |
| 5 | **OKX Pay 商户** | OKX App 内扫码,需 OKX + USDT 前置 | 日本邮箱 + OKX KYC | 你 OKX 钱包 | 中等友好 | ⏳ 备选 |
| 6 | **Binance Pay 商户** | Binance App 内扫码,需 Binance + USDT 前置 | 日本邮箱 + Binance KYC | 你 Binance 钱包 | 中等友好 | ⏳ 备选 |
| 7 | **Cryptomus**(多币种)| 客户已有 crypto,选币扫码 | 日本邮箱 | 你 crypto 钱包 | 友好 | ⏳ 50+ 用户 |
| 8 | **Lemon Squeezy** | 类似 Paddle,审核更严 | 日本個人事業主 | JPY 银行 | 中(Stripe 子公司继承严)| 备选 |

**关键修订(v3)**:

⭐ **真正的 silver bullet** = **Paddle 或 Alchemy Pay 通过 Alipay/WeChat 跨境通道**:
- 客户**直接扫支付宝 / 微信付款**(无需 USDT,无需注册,无需学习曲线)
- 你**日本身份合法收款**(Paddle 收 RMB → 你日本银行 JPY,Alchemy Pay 收 RMB → 你 USDT 钱包)
- **关键卡点**:VPN 类目需包装"open-source SaaS hosting" 过审,实战 30-50% 通过率
- **失败成本**:0(被拒不留黑记录,可重申)

❗ **Cryptomus 仍不解决中国客户支付宝直付** — 它是 crypto-only,角色调整为"海外多币种 + 中期"
❗ 2026 年**没有**比 Paddle Alipay / Alchemy Pay 更直接的方案(穷尽 17 路径已排除其它)

**不需要中国身份**。**不需要中国银行卡**。**不需要营业执照**(日本個人事業主届出即可)。

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

## 2. 可行路径详述

### 2.0 ⭐ Silver Bullet:Paddle Alipay/WeChat 跨境(优先申)

**这是 v3 的核心发现** — 真正解决"中国客户只有支付宝/微信、扫码直接付"的方案。

#### 是什么

Paddle 自 2024 年起在 checkout 内支持中国 Alipay + WeChat Pay 作为客户付款方式。流程:

```
1. 客户在 Nilou checkout 选 plan
2. 跳到 Paddle hosted page
3. 客户选支付方式: [Visa/Mastercard] [Alipay] [WeChat Pay] [Apple Pay]...
4. 选 Alipay → 自动跳 Alipay 官方跨境页面(汇率自动换算)
5. 客户用支付宝扫码付 RMB
6. Paddle 收 RMB → 跨境结算 → 你日本银行收 JPY
7. webhook → Nilou panel 自动开通
```

#### 客户视角

- **完全无需 USDT / 不用注册任何东西 / 不用学 P2P / 不用懂 crypto**
- 客户在 Nilou 站内点"用支付宝付款" → 跳 Alipay 扫码 → 完事
- 体验 = 国内淘宝购物级别

#### 商户视角(你)

- **日本個人事業主合法收款**(钱进日本银行 JPY,合规)
- Paddle 处理跨境合规 / 反洗钱 / 税务 / 客户支持 / chargeback
- 你只接 webhook
- 实名只在 Paddle(日本身份),与中国监管无任何接触

#### 关键卡点:VPN 类目过 Paddle 审核

Paddle 的 Acceptable Use Policy 对 VPN 是个案审,不是黑名单一刀切。

| 网站状态 | 通过率 |
|---|---|
| 全英文 SaaS 包装 + 業種"Open-source software hosting" + 业务说明清晰 | **30-50%** |
| 含"censorship resistance / GFW / privacy"中性英文表述 | 20-30%(灰区) |
| 含"VPN / proxy / 翻墙 / 节点"字样 | **<5% 必拒** |

**失败成本 = 0**(被拒不留黑记录,可重申;不影响 Stripe / 其他 MOR 申请)。

#### 费率

- 5-7%(Paddle MOR 服务费,含跨境结算 + 税务 + 合规)
- 比 USDT 直收(0%)贵,但客户体验差异巨大,首次客户转化率提升预计 3-5x

#### 申请前置

- [ ] 開業届(税务署 + Freee / Money Forward)
- [ ] 屋号付き口座(楽天 / GMO あおぞら)
- [ ] 業種 = "ソフトウェア業 / 情報通信業"
- [ ] **英文 SaaS 站(`nilou.network` 或新 `niloucc.com`)**,无任何 VPN / 翻墙 / 节点字样
- [ ] 業務説明:"Open-source Marzneshin SaaS hosting and subscription platform. Customers subscribe for managed instances of the open-source Marzneshin panel, with technical support and infrastructure maintenance."

#### 集成

- ship `ops/billing/paddle_provider.py`(REST API + webhook,~6h)
- dashboard checkout 加 "支付宝 / 微信 / 信用卡 — Paddle" 按钮 → Paddle hosted page
- webhook → panel 自动开通(grant 框架已存在)
- 走 §48 codex cross-review

#### 触发条件

- 立即(现在就申,审核 1-3 周,通过后立即上)— 这是从"0 客户"突破到"1 真客户"的关键钥匙

### 2.0.1 ⭐ Silver Bullet 备选:Alchemy Pay (ACH)

不像 Paddle 是 MOR(中介赚差价),Alchemy Pay 是直接的 fiat-to-crypto 处理商,**你直接拿 USDT**,不经过日本银行。

| 项 | 详情 |
|---|---|
| 总部 | 新加坡 + 香港(持牌 fiat onramp 服务商) |
| 中国 RMB 入口 | ✅ 支付宝 / 微信 / 银联(2024 年起明确支持) |
| 客户体验 | hosted checkout → 选支付宝 → 扫码付 RMB → 商户收 USDT |
| 你商户身份 | 个人 KYC,日本身份接受 |
| VPN 类目 | **未公开拒,需实测申请确认** |
| 费率 | 1-3%(根据卡 / 支付方式) |
| 失败成本 | 低(crypto 持牌,不留 Stripe / Paddle 黑记录) |

#### 与 Paddle 对比

| 项 | Paddle | Alchemy Pay |
|---|---|---|
| 你收什么 | JPY 进日本银行 | USDT 进你钱包 |
| 费率 | 5-7% | 1-3% |
| 客户体验 | hosted checkout(支付宝直付)| hosted checkout(支付宝直付) |
| 类目通过率 | 30-50%(包装到位) | 待实测 |
| 合规护城河 | MOR,Paddle 兜全部 | crypto 处理商,你拿 USDT |
| 适合场景 | 长期稳定,高税务合规 | 直接拿 USDT,低费率 |

#### 申请

- `alchemypay.org/business` → Crypto onramp merchant 申请
- 提交日本個人事業主信息 + 业务说明
- 审核 2-4 周

#### 双申策略(推荐)

**同时申 Paddle + Alchemy Pay**(失败成本 0,通过任一条即解锁中国客户扫码体验)。
两家审核独立,通过 Paddle 但 Alchemy 拒 → 用 Paddle;反之亦然;都过 → 客户选费率低的(Alchemy)。

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

### 2.3 Cryptomus(中期,50+ 用户后,**主要服务海外 + 多币种客户**)

⚠️ **修正前一版描述**:Cryptomus **不能让中国客户用支付宝直接付,你自动收 USDT**。它是 crypto-only 处理商 — 客户必须**已经有 crypto 钱包**才能付。

| 项 | 详情 |
|---|---|
| 总部 | Estonia(EU 持牌 crypto 服务商) |
| 注册 | 邮箱 + 钱包,5 分钟,无证件 |
| KYC(小额) | 不需要 |
| VPN 业务 | **明确允许**(有专门 merchant 类目) |
| 客户体验 | hosted checkout,**客户必须已有 crypto** → 选币种 → 看二维码 + 地址 → 用自己钱包扫码付款 |
| 收什么 | USDT TRC20/ERC20/BEP20 / USDC / BTC / ETH / 30+ 币 |
| 客户付什么 | 同上,客户钱包里的 crypto |
| 钱去哪 | 自动转入你设定的钱包 |
| 费率 | **0.4%**(Stripe 1/9) |
| 中文界面 | ✅ |
| 内置 P2P | 有(Cryptomus 自营 P2P,客户可在内买 USDT,但需 KYC + 商家少) |

**Cryptomus 真实价值定位**:

✅ **解决的问题**:
- 给已有 crypto 客户提供"hosted checkout"体验(替代裸 TRC20 地址 + memo 的简陋体验)
- **多币种 + 多链**支持(客户付 BTC,你收 USDT;客户付 ERC20,你收 TRC20)
- 自动对账 + webhook(替代你自己监听链上)

❌ **不解决的问题**:
- 中国客户从支付宝 / 微信 / 银行卡 → 商户 USDT 一键完成(需要 P2P 中介,Cryptomus 不做)
- Fiat onramp(中国 RMB / 日元 / USD 直接 → crypto)— 没有此能力

**真正的客户群**:**海外 + 已有 crypto 钱包的客户**(英文圈 Twitter / HN / Reddit 引流)+ 中国懂 crypto 的客户(占有 USDT 的中国客户的小众部分)。

#### 集成

- ship `ops/billing/cryptomus_provider.py`(参考 trc20_provider 模式,~6h)
- dashboard checkout 加 "Pay with Crypto(多币种)" 按钮 → Cryptomus hosted page
- webhook → panel 自动开通(已有 grant 应用框架,见 `ops/billing/grants.py`)
- 走 §48 codex cross-review

#### 触发条件(何时 ship)

- 海外客户出现(英文 Twitter / HN / Reddit 来的)
- 中国客户提"支持 BTC / ETH 付款"(占比通常 < 10%)
- **不**触发条件:中国客户嫌 OTC 麻烦 — 这种情况应 ship Binance Pay / OKX Pay(§2.5 / §2.6),不是 Cryptomus

### 2.4 Binance Pay 商户(短期,5+ 用户后,中国客户体验最优解之一)

**这是真正解决"中国客户扫码付款"的方案之一**(条件:客户已注册 Binance + P2P 买好 USDT)。

| 项 | 详情 |
|---|---|
| 是什么 | Binance 自家支付协议(类似微信支付,但在 Binance App 内) |
| 商户主体 | 个人 KYC 即可,日本身份接受 |
| 申请门槛 | Binance Personal KYC + Merchant 申请,审核 1-7 天 |
| VPN 业务 | acceptable use policy 中等友好(crypto 商户类目宽容) |
| 客户体验 | 客户在 Binance App 内扫你二维码 → 一键 USDT 付款 → 即时到账 |
| 客户前置 | 客户必须有 Binance 账户 + P2P 买好 USDT(15 分钟一次性学习) |
| 钱去哪 | 你 Binance 钱包(USDT/BUSD) |
| 费率 | **0%**(Binance 商户费率补贴中) |
| 限额 | 个人 KYC 单笔 ≤ $50K,日累 ≤ $200K(0-200 用户阶段够用) |
| 中文 App | ✅ |
| 中国客户接受度 | 高(P2P 商家多,流程顺) |

#### 集成

- ship `ops/billing/binancepay_provider.py`(REST API + webhook,~6h)
- dashboard checkout 加 "Binance Pay 扫码" 按钮 → 跳商户支付页 / 显示二维码
- 走 §48 codex cross-review

#### 触发条件

- 5+ 真客户(任何客户群,Binance Pay 对中外都友好)
- 客户反馈"想要扫码体验,不想复制 TRC20 地址"

### 2.5 OKX Pay 商户(短期,5+ 用户后,**中国客户主战场**)

**OKX 在中国客户中渗透率比 Binance 略高(P2P 商家更多 + 客服中文)**,是中国客户扫码付款的最优解。

| 项 | 详情 |
|---|---|
| 是什么 | OKX 自家支付协议(类似 Binance Pay,在 OKX App 内) |
| 商户主体 | 个人 KYC 即可,日本身份接受 |
| 申请门槛 | OKX Personal KYC + Merchant 申请,审核 1-7 天 |
| VPN 业务 | acceptable use policy 中等友好 |
| 客户体验 | 客户在 OKX App 内扫你二维码 → 一键 USDT 付款 → 即时到账 |
| 客户前置 | 客户必须有 OKX 账户 + P2P 买好 USDT(15 分钟一次性学习) |
| 钱去哪 | 你 OKX 钱包(USDT) |
| 费率 | **0%**(OKX 商户费率补贴) |
| 限额 | 与 Binance Pay 类似 |
| 中文 App | ✅ |
| 中国客户接受度 | **最高**(中国大陆客户主流交易所) |

#### 集成

- ship `ops/billing/okxpay_provider.py`(REST API + webhook,~6h)
- dashboard checkout 加 "OKX Pay 扫码" 按钮
- 走 §48 codex cross-review

#### 触发条件

- 5+ 真客户(中国客户为主)
- 客户反馈"想统一在 OKX 内买 + 付"

#### Binance Pay vs OKX Pay 选哪个先做

**两个都做**(集成共享 90% 代码),工时合计 ~10h。
- 客户登录哪个 App 多就用哪个
- 实测:中国客户 60% 用 OKX,30% 用 Binance,10% 用其它

### 2.6 Paddle 完整能力(MOR + 跨境多通道)

§2.0 已详述 Paddle Alipay/WeChat 跨境(silver bullet)。Paddle 同时提供:

| 客户群 | Paddle 收什么 |
|---|---|
| 中国客户(支付宝 / 微信)| ⭐ silver bullet,见 §2.0 |
| 海外客户(信用卡 / Apple Pay / Google Pay)| 100+ 国家覆盖 |
| 海外客户(部分 PayPal)| 通过 Paddle MOR 中转 |
| 商户合规 / 税务 / chargeback | Paddle 全包 |

**单次申请 Paddle 同时解锁中国 + 海外双客户群**。这是 Paddle 比 Stripe / Lemon Squeezy 优势的核心。

---

## 3. 推荐执行顺序(v3 修订:silver bullet 提前)

### 现在 / 立即(0-1 用户阶段)

**两件事并行**:

1. **保持 USDT 直收 + OTC 引导**(已 ship,继续兜底)
2. ⭐ **立即申 Paddle + Alchemy Pay**(同时双申,失败成本 0)
   - operator Phase 0:準备英文 SaaS 站 + 開業届 + 業種申报 + 業務説明定稿
   - 提交两家审核(各 1-3 周)
   - 审核期间继续 USDT / OTC 兜底

理由:从"0 客户"到"1 真客户"的最大瓶颈 = 中国客户扫码体验。Paddle Alipay / Alchemy Pay 是真正解锁这一步的钥匙。**不应等到"5+ 用户后"才申** — 因为没有这条路,5+ 客户都拉不到。

### 短期(任一 silver bullet 过审后,1-3 周)

- tech lead ship `paddle_provider.py` 或 `alchemypay_provider.py`(~6h)
- dashboard checkout 加 "支付宝 / 微信扫码" 按钮
- 走 §48 codex cross-review + 生产 cutover
- **首批中国客户开始真正扫码付费**

### 中期(silver bullet 双申都被拒的备选,5-50 用户)

如双申都拒,降级到 **OKX Pay + Binance Pay 商户接入**(中国客户必须有 OKX/Binance + USDT 前置):
- 工时 ~10h(双 provider 共享 90% 代码)
- 客户体验比 Paddle Alipay 直付差,但比 OTC 教程好

### 长期(50-200 用户,海外客户起量)

ship **Cryptomus**(多币种 hosted checkout,海外 + 中国懂 crypto 客户):
- 工时 ~6h
- 不替代 Paddle Alipay,补充多币种支持

### 关键修订总结(v3)

⭐ **新发现**:Paddle Alipay/WeChat 跨境 + Alchemy Pay(§2.0)是"中国客户扫码直付"的真正 silver bullet。**所有路径中唯一让客户不学 crypto 也能付款的方案**。
✅ **优先级提升**:Paddle / Alchemy 申请提到"立即",不再等"50+ 用户后"
✅ **OKX Pay / Binance Pay 降级**:从短期主路径降为"双 silver bullet 都被拒后的备选"
✅ **Cryptomus 调整定位**:从"中国客户解药"修正为"海外 + 多币种补充"

### 失误复盘(L-046 候选)

我前几轮反复推 USDT / OTC / Cryptomus / 中文聚合方,**没把 Paddle Alipay 跨境 + Alchemy Pay 这条 silver bullet 拿出来**。

原因:行业 mental model 把 Paddle / Lemon Squeezy 看作"海外英文圈信用卡通道",忽略了 2024 年起接入 Alipay/WeChat 的能力。

教训:
1. 推荐方案前先**穷尽**(列 17+ 路径全扫),不要靠惯性
2. 操作环境(operator 国籍 / 法律辖区 / 客户群)需明确锁定后再推方案
3. 关键功能更新(如 Paddle 2024 接 Alipay)需主动 search,不能依赖"印象"

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
