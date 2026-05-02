# Payment Channel Matrix — Nilou Network

> 状态:决策矩阵 + 风险评估
> 更新日期:2026-05-03
> 适用受众:operator(运营决策)+ tech lead(集成实现)

---

## 1. TL;DR

| 通道 | 商户风险 | 客户体验 | 月费 / 手续 | 状态 |
|---|---|---|---|---|
| **USDT TRC20 直收** | 🟢 0 | ⭐⭐⭐ | 0 | ✅ 已 ship(主) |
| **Cryptomus**(crypto checkout)| 🟢 0 | ⭐⭐⭐⭐ | 0.4% | ⏳ 待集成(可选,海外客户友好) |
| **OTC 引导(支付宝→USDT)** | 🟢 0 | ⭐⭐⭐(教程到位 ⭐⭐⭐⭐) | 0 | ✅ docs ship,见 `HOW-TO-BUY-USDT-FROM-ALIPAY.md` |
| EPay / 易支付 | 🔴 高 | ⭐⭐⭐⭐ | 3-5% | ❌ 商户周期性风控,**已弃用** |
| 虎皮椒 / payjs / 同类四方聚合 | 🔴 高 | ⭐⭐⭐⭐ | 3-5% | ❌ 同上 |
| Alipay 官方商户 | — | — | — | ❌ VPN 业务被拒 |
| Stripe / Komoju / PayPal | 🔴 中高 | ⭐⭐⭐⭐⭐ | 3.6% + 锁号风险 | ❌ VPN 类目限制 |

---

## 2. 为什么不直收支付宝

**支付宝官方商户**:
- 国内版需工商执照 + 大陆银行账户 + 类目审核 — VPN 业务 100% 拒
- 国际版(Alipay International)需海外法人 + ICP — 同样不开 VPN 类目

**四方 / 五方聚合**(易支付 / 虎皮椒 / payjs / BeePay 等):
- 底层接的是个人微信 / 支付宝码池
- 商户层(运营你)依赖聚合方稳定性 — 聚合方被风控 → 你的钱链断 / 资金被扣留
- 2024-2025 监管收紧后,此类聚合方平均寿命 < 18 个月
- **结论:不是工具问题,是商业模式不可持续**

**个人收款码 / 朋友代收**:
- 大陆个人卡反洗钱阈值低,大额异常交易直接冻卡
- 帮信罪刑事风险(2024 起执法收紧)
- 不能程序化(无 webhook)
- 不可 scale

---

## 3. 真正可行的方案:OTC 引导

### 工作流

```
客户在 dashboard 选 plan → checkout 显示两条路径:
  路径 A: 我有 USDT → 直接付 TRC20 地址(已 ship)
  路径 B: 我用支付宝 → 跳转「OTC 教程」(本 PR ship)
```

路径 B 教程指引客户:

1. 下载 OKX / 币安 / Bitget App
2. 注册(护照 / 大陆身份证均可,海外交易所 KYC 友好)
3. 充值人民币 → 选"P2P 交易"或"快捷买币"
4. 用支付宝 / 微信 / 银行卡向 P2P 商家买 USDT(TRC20 链)
5. 提币到 Nilou Network 收款地址(panel 给的 memo / 标签自动匹配)
6. 5-30 分钟自动到账

### 商户风险评估

| 风险点 | 评估 |
|---|---|
| 商户账户冻结 | 0(钱不经过你) |
| 反洗钱调查 | 0(USDT 入账,链上可追溯,合法 crypto 交易) |
| 帮信罪 | 0(你提供 SaaS,客户自付 USDT) |
| 资金扣留 | 0(交易所→你钱包,即时) |

### 客户痛点

- ⚠️ **首次客户**:OKX 注册 + KYC + P2P 学习曲线 ~15 分钟
- ⚠️ **小额客户**(¥30 / 月)觉得麻烦
- ✅ **大额 / 长期**(¥80 季度 / ¥240 年度)接受度高

### 转化率提升对策

1. 教程必须图文并茂(本 PR 配套 `HOW-TO-BUY-USDT-FROM-ALIPAY.md` ship 中)
2. 提供 1-on-1 微信指导(创业期红利,前 50 客户值得)
3. 推荐**年付优惠**(¥240/年送 30 天)— 一次教学,一年安心
4. TG bot 半自动化:`/buy_usdt` 命令推送教程 + 推荐 P2P 商家筛选

---

## 4. 中期(海外客户)— Cryptomus 集成

待 Phase C 海外客户出现后(英文 Twitter / HN / Reddit 引流):

- 加 `ops/billing/cryptomus_provider.py`(参考 trc20_provider 模式)
- dashboard checkout 增"国际客户"按钮 → Cryptomus hosted checkout
- 客户体验:输入邮箱 → 选币 → 扫码付 → 5 分钟到账
- 商户视角:Cryptomus webhook → panel 自动开通

未集成 reason:当前 0 海外客户,过早集成是 §32.5 反模式 #1(Vibe Shipping)。

---

## 5. 不做的事(决策记录)

- ❌ 不接易支付 / 虎皮椒 / payjs(已知周期性风控)
- ❌ 不申请 Stripe / Komoju / PayPal(VPN 类目限制 + 锁号风险)
- ❌ 不用个人微信 / 支付宝码收款(冻卡 + 法律风险)
- ❌ 不让朋友代收(帮信罪 + 友情成本)
- ❌ 不做"代购 USDT"中介服务(等于把 OTC 风险转回你身上)

---

## 6. 客户引导话术(给运营)

支付宝客户来问:

> "我没有 USDT,只能用支付宝,行不行?"

回:

> 行!支付宝可以,但要走个 OTC 流程。简单说就是你用支付宝在交易所买 USDT,5 分钟就到账。我有详细图文教程发你 → [`HOW-TO-BUY-USDT-FROM-ALIPAY.md` 链接]
>
> 我们不直接收支付宝是因为机场行业监管特殊,直接收会让我们(也让你)有风险。USDT 链上付款合法可追溯,反而最安全。
>
> 你要是头一次操作我可以微信带你走一遍,15 分钟搞定。

---

## 7. 引用

- `ops/billing/trc20_provider.py` — 现有 USDT 实现
- `docs/launch/HOW-TO-BUY-USDT-FROM-ALIPAY.md` — 客户教程(本 PR ship)
- `docs/launch/CUSTOMER-FAQ.md` — 客户面 FAQ
- `LAUNCH-week2-trc20-only.md` — TRC20 上线 checklist
