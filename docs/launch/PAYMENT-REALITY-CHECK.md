# Step 1 Reality Check — 支付通道实测调研

> **状态**: ✅ 完成 2026-05-03
> **方法**: WebFetch + WebSearch 4 路径并行(Paddle / Lemon Squeezy / Alchemy Pay / Paddle Alipay 实测)
> **范围**: 验证 PAYMENT-DECISION-FINAL-JP.md v3 中"silver bullet"路径的真实可行性
> **结论**: 修订之前过度乐观的判断,silver bullet 改为"技术确定可用,商业准入不可保证"

---

## 1. Paddle 真实情况

### 1.1 Alipay 集成(✅ 确认)

- Paddle 自 2024 起官方支持 Alipay 作为客户付款方式
- 客户体验:desktop 扫码 / mobile 跳 Alipay App
- 启用方式:Paddle dashboard 一键开启

### 1.2 重要限制(❗ 之前未提)

| 限制 | 详情 | 对 Nilou Network 影响 |
|---|---|---|
| **客户地址必须 `address=China`** | 否则 checkout 不显示 Alipay 选项 | 你客户全部中国 ✅ OK |
| **货币必须 `CNY`** | 不能用 USD/JPY 触发 Alipay | 需要在 Paddle 配 CNY 价格档 |
| **单笔上限 1600 CNY** | 含订阅续费 | ¥30/月 ✅、¥80/季 ✅、¥240/年 ✅、**¥1600+ ❌**(不能做终身付) |

### 1.3 VPN 类目政策(❗ 比之前判断更严)

Paddle Acceptable Use Policy 明确列:
- "VPN and Proxies" = **Restricted Category #19**
- 受限类目需 enhanced due diligence(超出一般 SaaS 申请审查)
- 通过率**不可知**,实测案例少(我之前说 30-50% 无依据)

### 1.4 一般 SaaS 拒绝率本身就高

行业实际拒绝原因(非 VPN 类):
- 退款政策必须无条件 / no exceptions(Paddle 承担 chargeback)
- 网站显示的法律实体必须严格匹配 Paddle 注册实体
- 部分案例要求 3 月 payment processing history(catch-22)
- 严格只接 SaaS / 软件,services / learning platforms 拒

### 1.5 修订评估

| 维度 | v3 我的估计 | 真实(v4) |
|---|---|---|
| Alipay 集成 | ✅ 可用 | ✅ 可用 |
| 客户限制 | 未提 | 中国地址 + CNY 触发 + ¥1600 上限 |
| VPN 通过率 | 30-50% | **不可知**(#19 受限,无可靠数据) |
| 失败成本 | 0 | 0(被拒不留黑记录,可重申) |

---

## 2. Lemon Squeezy 真实情况

- Prohibited products 列表**不明确列 VPN/proxy**
- 接受:digital goods / SaaS subscriptions
- 拒:services / consulting / web design / 物理商品
- Stripe 子公司,审核继承 Stripe 严格度

**评估**:VPN-as-SaaS 灰区,通过率不可知,可能比 Paddle 略宽(没明列 VPN restricted)。

---

## 3. Alchemy Pay 真实情况

- Merchant solutions 接受 e-commerce / gaming / service providers
- 170+ 国家 / 300+ 支付方式
- 费率 1.5-3.5%
- **政策对 VPN 不公开**(需直接联系 sales 确认)
- 主要客户群:crypto exchanges / Web3 / NFT,普通 SaaS 案例少

**评估**:**不应作主依赖**,可作 c-tier 备选(申请门槛 + 政策不透明 + 客户群偏 crypto)。

---

## 4. 修订后的策略:三申并行

**之前 v3**:Paddle + Alchemy Pay 双申(silver bullet)
**修订 v4**:**Paddle + Lemon Squeezy + OKX Pay/Binance Pay merchant 三申**

### 三申理由

| 申请 | 通过率 | 客户体验 | 失败成本 |
|---|---|---|---|
| Paddle | 不可知(VPN #19 受限)| ⭐⭐⭐⭐⭐ 支付宝直付 | 0 |
| Lemon Squeezy | 不可知(VPN 不明列) | ⭐⭐⭐⭐⭐ 支付宝直付 | 0 |
| OKX Pay / Binance Pay merchant | 较高(crypto-native 友好) | ⭐⭐⭐⭐ 交易所内扫码,需 P2P 前置 | 0 |

**通过任一即解锁中国客户扫码体验**,不应等到一家被拒了再申下一家。

### 套餐定价调整(应对 Paddle ¥1600 上限)

| 套餐 | 定价 | Paddle 可用 | 备注 |
|---|---|---|---|
| trial | ¥0 / 3 天 | ✅ | 不收费 |
| m1 | ¥30 / 月 | ✅ | 远低于 ¥1600 |
| q1 | ¥80 / 季 | ✅ | 同上 |
| y1 | ¥240 / 年 | ✅ | 同上 |
| **lifetime**(候选) | ❌ 不做 ¥1600+ 套餐 | — | 有客户问就走 USDT |

---

## 5. 之前过度承诺 → 修正承诺

### 我之前说

> "Paddle Alipay 是 silver bullet,通过率 30-50%,失败 0 成本"

### 修正后说

> Paddle Alipay 是**技术上确定可用、商业准入不可保证**的路径。VPN 在 Paddle 是 Restricted Category #19,需 enhanced due diligence,通过率不可知。失败成本仍 0,值得三申之一,但**不应作为唯一依赖**。

### 教训(L-046 候选确认)

1. ✅ "穷尽路径"原则有效(找到 Paddle Alipay)
2. ❌ **没第一时间做 reality check** — 用 WebFetch / WebSearch 查官方政策应该是 v3 之前的工作,不是 v4 才补
3. ❌ 通过率数字凭"印象"给(30-50% 无依据),应该说"不可知"
4. ✅ 修订流程及时(v3 → v4 当轮修正,不拖延)

---

## 6. Sources(可追溯证据)

- [Paddle Acceptable Use Policy (Help Center)](https://www.paddle.com/help/start/intro-to-paddle/what-am-i-not-allowed-to-sell-on-paddle)
- [Paddle Alipay Developer Docs](https://developer.paddle.com/concepts/payment-methods/alipay)
- [Paddle Alternative Payment Methods Blog](https://www.paddle.com/blog/alternative-payment-methods)
- [Paddle Rejection Case Study (DEV.to)](https://dev.to/pavelbuild/paddle-rejected-my-saas-3-times-heres-what-they-check-that-isnt-in-their-docs-5dnn)
- [Lemon Squeezy Prohibited Products](https://docs.lemonsqueezy.com/help/getting-started/prohibited-products)
- [Alchemy Pay Merchant Overview](https://alchemypay.org/)
- [Alchemy Pay Gateway Guide (Bitget)](https://www.bitget.com/amp/academy/alchemy-pay-gateway)

---

## 7. 下一步

- ✅ Step 1 完成(本 doc)
- ⏳ Step 2 决策:三申(Paddle + Lemon Squeezy + OKX Pay/Binance Pay)— 等 operator 确认
- ⏳ Step 3:nilou.network 英文 landing page(本 PR ship)
- ⏳ Step 4:開業届 教程(本 PR ship)
- ⏳ Step 5:屋号付き口座(operator 操作)
- ⏳ Step 6:三家平台同步申请(等 Step 3-5 准备好后)
