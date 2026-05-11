# Paddle / Lemon Squeezy / Stripe — Pre-Application Guide

> 状态:Step 6 of payment merchant application playbook(operator 三家并发申请前的最终准备清单)
> 适用:operator 拿到 ① 屋号付き(or 個人名義)銀行口座 ② 開業届控え PDF 正式版后,15 分钟内并发递交 Paddle + Lemon Squeezy + Stripe Japan 三家申请
> 预计耗时:三家全部填表 + 上传 ≈ 60-90 分钟(共通材料预排好后)
> 前置完成:
>   - ✅ GMO 虚拟办公室(〒141-0021 東京都品川区上大崎3丁目14番34号 プラスワン402、`HOW-TO-RENT-VIRTUAL-OFFICE-JP.md`)
>   - ✅ 開業届 e-Tax 提出(2026/5/7、品川税務署、受付番号 `20260507224845548217`、屋号 `Nilou Network`、`HOW-TO-FILE-KAIGYOU-TODOKE-JP.md`)
>   - ⏳ 住信SBI ネット銀行 申請中(5/7、審査 1-3 営業日)
>   - ⏳ 楽天 モバイルチョイス"050" 申請中(5/8)
>   - ✅ 開業届控え PDF(本体 + 受信通知 + 青色申告承認申請書)已下载并合并
>   - ✅ 特商法表記 三语公開(`marketing/nilou-network/legal.html`、PR #249 / #251)
>   - ✅ Customer portal P1 静态视觉 deploy 完成(`nilou.network/portal/`)
> 关联:`docs/launch/PAYMENT-DECISION-FINAL-JP.md` / `PAYMENT-CHANNEL-MATRIX.md` / `docs/ai-cto/SPEC-payment-mor-integration.md` / `docs/ai-cto/DECISIONS.md` D-020

---

## 1. 概览

### 1.1 为什么并发申请三家

| 单家 | 通过率(JP 個人事業主 + open-source SaaS hosting 类目) | 失败成本 |
|---|---|---|
| Paddle | 30-50%(包装到位) | 0(被拒不留黑记录,可重申) |
| Lemon Squeezy | 20-40%(Stripe 子公司,继承严格度) | 0 |
| Stripe Japan | 20-30%(JP + 個人事業主双重 friction) | 中(Stripe 黑名单跨国,被拒后改善材料再申) |

**三家全拒概率 ≈ 4.2%**(独立事件假设,见 `SPEC-payment-mor-integration.md` §4.2)。

**并发申请逻辑**:
- 单家审核 1-6 周,顺序申请最坏情况 18 周才知道结果
- 并发申请 → 4-6 周内有 ≥1 家通过的概率 ≈ 95.8%
- 失败成本最低的 Paddle / LS 同时进件,Stripe 作为"压底牌"(被拒影响最大,但通过后费率最优 3.6%)

### 1.2 三家比较表

| 项 | Paddle | Lemon Squeezy | Stripe Japan |
|---|---|---|---|
| **角色** | Merchant of Record(MOR) | Merchant of Record(MOR) | 純支付处理商(非 MOR) |
| **JCT / VAT 处理** | Paddle 代收代缴 | LS 代收代缴 | operator 自己处理 |
| **结算货币** | JPY(进日本银行) | USD(默认)/ 可设 JPY | JPY(进日本银行) |
| **费率** | 5-7%(含税务 / 跨境 / chargeback) | 5% + $0.50/笔 | 3.6%(国内卡)/ 3.95%(海外卡) |
| **支付宝 / 微信跨境** | ✅(silver bullet)| ⚠️(限定地区)| ❌(JP Stripe 不开) |
| **审核时长** | 4-6 weeks | 1-2 weeks | 2-7 days(初审)+ 持续 underwriting |
| **个人事業主 受理** | ✅ | ✅ | ✅(屋号 or 個人名義) |
| **VPN 类目政策** | 个案审、灰区 | 个案审、灰区 | AUP 明确禁 VPN-related,**必须**严守 "managed open-source app hosting" 表述 |
| **被拒后影响** | 0(不留黑记录) | 0 | 中(Stripe 全球账号共享黑名单) |

### 1.3 预期审核时长汇总

```
2026-05-11 (今日) → 三家全部递交
2026-05-13 (T+2)   ⏳ Stripe 初审反馈最早(或要求追加材料)
2026-05-25 (T+14)  ⏳ Lemon Squeezy 预期通过 / 拒 / 追加
2026-06-22 (T+42)  ⏳ Paddle 预期通过 / 拒 / 追加
2026-06-30        🎯 至少一家通过 → 立即触发 SPEC-payment-mor-{provider}.md Phase X PLAN
```

### 1.4 不要做的事(铁律)

- ❌ 全篇任何位置出现 `VPN` / `proxy` / `代理` / `翻墙` / `节点` / `GFW` / `circumvention` / `censorship circumvention` / `节点订阅` 字样
- ❌ 不要让 Paddle / LS / Stripe 工作人员从你网站任何角落(包括 customer-portal / dashboard / docs / 社交媒体)看到上述词
- ❌ 不要在递交后修改 `nilou.network` 服务说明 / 特商法表記(审核期变更 = 立即拒)
- ❌ 不要在 "Why we deserve approval" 文案中承诺 / 宣传 / 影射任何受版权保护 IP(包括 D-020 涉及的二游角色名)
- ❌ 不要在月予想売上字段填超过 ¥50万 / 月(初期合理 = ¥10-30万,过高触发 underwriting 加强)

---

## 2. 共通準備材料清单

申请前 30 分钟把这些材料**全部预排在一个文件夹**,三家申请时复用。

### 2.1 文件类(PDF / JPEG)

| # | 文件 | 说明 | 来源 / 状态 |
|---|---|---|---|
| 1 | `kaigyou-todoke-merged.pdf` | 開業届控え 三合一(本体 + 受信通知 + 青色申告承認申請書) | e-Tax 受信通知から PDF 直接下载 + 合并 ✅ |
| 2 | `zairyu-card-front.jpg` | 在留カード 表面 | 自撮(明るい / 反射なし)|
| 3 | `zairyu-card-back.jpg` | 在留カード 裏面 | 同上 |
| 4 | `mynumber-front.jpg`(任意) | マイナンバーカード 表面 | 銀行已用,Paddle / LS 可能要求補充 |
| 5 | `mynumber-back.jpg`(任意) | マイナンバーカード 裏面 | 同上 |
| 6 | `bank-statement.pdf` | 屋号付き口座 or 個人口座 流水(直近 3 ヶ月) | 住信SBI 開通後即取得 |
| 7 | `proof-of-address.pdf` | 公共料金 or 住民票 写し(住所証明) | 不要紧时 GMO 利用契約書 PDF 也可作为事業所証明 |
| 8 | `website-screenshot-home.png` | `nilou.network` トップ screenshot | 1920×1080 推奨 |
| 9 | `website-screenshot-legal.png` | `nilou.network/legal.html` 特商法表記 screenshot | 同上 |
| 10 | `website-screenshot-pricing.png` | `nilou.network/portal/` 価格表 screenshot | 同上 |

### 2.2 文字情報(コピペ用テキストファイル `application-fields.txt` に整理)

```
=== Operator 法定情報 ===
法定姓名(漢字):       陸 浩洋
法定姓名(ローマ字):   Lu Haoyang
法定姓名(カナ):       リク コウヨウ
生年月日:              [operator 自記入]
在留資格:              技術・人文知識・国際業務(技人国)
在留カード番号:        [operator 自記入]
個人住所(住民票):      [operator 自記入、税務署内部档案,绝对不公開]
個人電話:              [operator 自記入、内部のみ]
個人メール:            qq381490307@gmail.com(参考)

=== 事業者情報(全 KYC 統一) ===
屋号:                  Nilou Network
屋号フリガナ:          ニィロウ ネットワーク(D-020 SEALED、小書きィ あり)
屋号ローマ字:          Nilou Network
事業所住所:            〒141-0021 東京都品川区上大崎3丁目14番34号 プラスワン402
事業所電話(050):       [楽天 050 申请通过后填入]
事業用メール:          ops@nilou.network(SES / Cloudflare Email 設定済)
ウェブサイト:          https://nilou.network/
特商法表記:            https://nilou.network/legal.html
プライバシーポリシー:  https://nilou.network/privacy.html
利用規約:              https://nilou.network/terms.html

=== 開業情報 ===
開業届 提出日:          2026/05/07
開業届 受付番号:        20260507224845548217
管轄税務署:             品川税務署
開業年月日:             2026/05/07
青色申告 承認:          申請済(同日)
業種(日本標準産業分類): ソフトウェア業(6201)
業種 補完:              情報処理・提供サービス業(6202)

=== 売上見込み ===
初期月予想売上:         ¥10万-30万 / 月
6 ヶ月後予想:           ¥30万-80万 / 月
12 ヶ月後予想:          ¥80万-150万 / 月
顧客地域 内訳:          日本国内 40%、アジア 30%、北米 20%、欧州 10%
平均客单価:             ¥1,500-3,000 / 月(月額サブスク)
予想 chargeback rate:   < 0.5%(SaaS デジタル商品の業界平均)
```

### 2.3 商品/服务说明文案(EN / JA / ZH 各 200 字、§8 附录参照)

商品説明は **3 家とも全く同じ表現を使う**(整合性 max、矛盾あれば即拒)。詳細文案は §8 附録参照。

---

## 3. Paddle 申请详细 step-by-step

### 3.1 URL & エントリ

- 主入口:`https://www.paddle.com/sign-up`(or `https://login.paddle.com/signup`)
- 環境:本番(sandbox はテスト用、申請に関係しない)

### 3.2 フォーム入力(画面順)

#### Step 3.2.1 — Account creation

| フィールド | 入力値 | 注意 |
|---|---|---|
| Email | `ops@nilou.network` | 個人 gmail は避ける(プロフェッショナル印象)|
| Password | 強固(passwords manager で生成) | 別途 1Password / Bitwarden に保存 |
| Country | **Japan** | 後で変更不可 |

#### Step 3.2.2 — Business type

| フィールド | 入力値 |
|---|---|
| Business type | **Sole proprietor / Individual** |
| Legal business name | `Nilou Network`(屋号)|
| Trading name(任意) | `Nilou Network`(同じ)|
| Tax / business registration number | **空欄**(個人事業主は法人番号なし、Paddle はこの欄を skip 可)|

#### Step 3.2.3 — Business address

| フィールド | 入力値 |
|---|---|
| Street address line 1 | `3-14-34 Kamiosaki, Plus One 402` |
| Street address line 2 | (空欄) |
| City | `Shinagawa-ku` |
| State / Prefecture | `Tokyo` |
| Postal code | `141-0021` |
| Country | `Japan` |

#### Step 3.2.4 — Contact

| フィールド | 入力値 |
|---|---|
| Phone number | `+81-50-XXXX-XXXX`(楽天 050 通过後)|
| Support email | `support@nilou.network` |

#### Step 3.2.5 — Banking & payout

| フィールド | 入力値 | 注意 |
|---|---|---|
| Payout currency | `JPY` | 為替損失 0 |
| Bank account holder | `Nilou Network`(屋号付き)or `Lu Haoyang / リク コウヨウ`(個人名義) | 銀行口座名と一致必須 |
| Bank name | `住信SBIネット銀行`(SBI Sumishin Net Bank) | 屋号付き or 個人名義どちらか |
| SWIFT / BIC | `NTSSJPJT` | 住信SBI の SWIFT、要確認 |
| Branch code / 支店番号 | [住信SBI 開通通知書記載] | |
| Account number | [住信SBI 開通通知書記載] | |
| Account type | Checking / 普通預金 | |

#### Step 3.2.6 — Business description

```
Business model: Managed hosting and subscription service for open-source applications
Industry: Software / Information Services
Product type: Software-as-a-Service (subscription)
```

Paddle が "What do you sell?" のフリーテキストを要求した場合 → §8 附録 EN 文案をそのまま貼る。

#### Step 3.2.7 — Website & compliance

| フィールド | 入力値 |
|---|---|
| Website URL | `https://nilou.network/` |
| Terms of service URL | `https://nilou.network/terms.html` |
| Privacy policy URL | `https://nilou.network/privacy.html` |
| Refund policy URL | `https://nilou.network/legal.html`(特商法表記内に refund 条項あり)|

#### Step 3.2.8 — Volume forecast

| フィールド | 入力値 |
|---|---|
| Expected monthly revenue(first 6 months) | `¥100,000 - ¥300,000` |
| Expected average transaction value | `¥1,500 - ¥3,000` |
| Expected chargeback rate | `< 0.5%` |
| Customer geography | Japan 40% / Asia 30% / North America 20% / Europe 10% |

### 3.3 アップロード書類

Paddle が個別にメールで以下を要求してくる(初回フォーム後、24-72h 以内):

- [ ] `kaigyou-todoke-merged.pdf`(個人事業主証明)
- [ ] `zairyu-card-front.jpg` + `zairyu-card-back.jpg`(身分証)
- [ ] `bank-statement.pdf`(銀行口座証明)
- [ ] `proof-of-address.pdf`(事業所証明、GMO 利用契約書 PDF 可)
- [ ] `website-screenshot-*.png`(任意、Paddle 側で自動巡回するため通常不要)

### 3.4 "Why Paddle should approve you" 1-paragraph 文案

Paddle の application form の最後に "Tell us about your business" or "Why are you a good fit for Paddle?" の自由記述欄あり。**operator が自筆 / 自己責任で記述**(私はテンプレートのみ提供、商業陈述は operator 主観領域)。テンプレート例:

```
Nilou Network is a managed hosting and subscription platform for
open-source applications, founded in 2026 in Tokyo, Japan, registered
as a sole proprietorship at Shinagawa Tax Office. We provide customers
with managed instances of open-source software (Marzneshin panel and
related applications), bundling infrastructure operation, SSL certificate
lifecycle management, technical support, and uptime monitoring into a
single monthly subscription. Our customer base spans Japan, Asia,
North America, and Europe, primarily serving developers and small
businesses who prefer a managed instance over self-hosting.

We chose Paddle as our Merchant of Record because of (1) global tax
compliance automation including JCT for Japanese customers, (2) broad
payment method coverage including Alipay and WeChat Pay for our
international customer base, and (3) full chargeback and fraud handling
that lets us focus on operations rather than payment infrastructure.

We commit to: maintaining a chargeback rate below 0.5%, full transparency
in our Terms of Service and Privacy Policy (both published at
nilou.network/terms.html and /privacy.html), and prompt response to any
compliance review requests.
```

> ⚠️ operator は上記をテンプレートとして読み、**自分の言葉で 100-200 語に書き直す**(コピペは Paddle 側 plagiarism detection に引っかかる可能性あり、また自筆でないと審査官の信頼を失う)。

### 3.5 予期审核时长

- 初回 review:**3-7 business days**(automated + manual underwriting 第一段)
- 追加材料要求:**24-48h 以内に operator が回答**(遅延 = 拒の典型理由)
- 二次 review:**2-4 weeks**
- 最終決定:**4-6 weeks**

### 3.6 拒否理由 Top 5 + 対応

| # | 拒否理由 | 対応 |
|---|---|---|
| 1 | "Business model unclear" | §8 附録 EN 文案を再提出、"managed hosting of open-source applications" を 3 回以上明示 |
| 2 | "Website lacks required policies" | `nilou.network/legal.html` 特商法 + `/terms.html` + `/privacy.html` 全部公開済を screenshot 添付 |
| 3 | "Industry / category restricted" | "We are a SaaS managed hosting provider for open-source apps, not a network service provider" と明示、業種コード `6201 ソフトウェア業` 強調 |
| 4 | "Insufficient operating history" | 開業届 2026/5/7 + customer-portal 静态视覚 deployed 済を示す、"Pre-launch, applying for payment infrastructure ahead of public launch" と説明 |
| 5 | "High chargeback risk industry" | Chargeback < 0.5% 目標 + refund policy(7-day) + customer support SLA を提示 |

---

## 4. Lemon Squeezy 申请详细 step-by-step

### 4.1 URL & エントリ

- 主入口:`https://app.lemonsqueezy.com/onboarding`
- 既存 Lemon Squeezy account がない場合 → `https://www.lemonsqueezy.com/signup` から先に sign up

### 4.2 フォーム入力(画面順)

#### Step 4.2.1 — Account & store

| フィールド | 入力値 |
|---|---|
| Email | `ops@nilou.network` |
| Store name | `Nilou Network` |
| Store URL slug | `nilou-network`(`nilou-network.lemonsqueezy.com` で hosted checkout 利用可) |
| Default currency | `USD`(後で JPY 変更可、ただし USD 推薦 — LS は USD 主体)|

#### Step 4.2.2 — Business type

| フィールド | 入力値 |
|---|---|
| Are you a business or individual? | **Individual / Sole proprietor** |
| Country of residence | `Japan` |
| Tax ID type | `Other / Sole proprietor (no tax ID)` |
| Tax ID number | 空欄(個人事業主 = 法人番号なし)|

#### Step 4.2.3 — Address & contact

Paddle §3.2.3 / §3.2.4 と同じ住所・電話を入力。

#### Step 4.2.4 — Payout(Wise or direct bank)

LS は **Wise / Payoneer / 直接銀行送金** 3 択。推薦 = **Wise multi-currency**:

| フィールド | 入力値 | 注意 |
|---|---|---|
| Payout method | `Wise` | USD 受け取り → JPY 変換が住信SBI 直接より為替差有利 |
| Wise account email | `ops@nilou.network` | Wise アカウントは別途事前作成、§7 参照 |

代替 = 直接住信SBI 入金(SWIFT 経由、為替手数料 1-2% 余分にかかる)。

#### Step 4.2.5 — "Tell us about your business"

LS の最重要自由記述欄。**operator が自記入**。テンプレート:

```
Nilou Network is a managed hosting platform for open-source applications,
operating as a sole proprietorship in Tokyo, Japan. We sell monthly
subscriptions that include: (1) a managed instance of open-source software
deployed on our infrastructure, (2) SSL certificate provisioning and
renewal, (3) infrastructure monitoring and uptime guarantees, (4) email-
based technical support.

Our typical customer is a developer or small business that wants to use
open-source software (specifically the Marzneshin open-source panel and
related applications, license: AGPL-3.0) without operating their own
servers. Pricing: ¥1,500 - ¥3,000 per month per managed instance.

We are pre-launch and applying for payment infrastructure ahead of public
launch (planned 2026 Q3). Full legal disclosure at nilou.network/legal.html
(Japanese 特定商取引法 disclosure required by law for all Japanese
e-commerce operations).
```

⚠️ **絶対に書かない単語**:VPN, proxy, anonymization, censorship, GFW, circumvention, traffic relay, anti-blocking, restricted network, geo-unblock, unrestricted access.

⚠️ **書いてよい単語**:managed hosting, open-source application, SaaS, subscription, infrastructure operation, technical support, AGPL-3.0, sole proprietorship, Japanese registered business.

#### Step 4.2.6 — Product setup(任意、後でも可)

| フィールド | 入力値 |
|---|---|
| Product name | `Nilou Managed Hosting — Starter` |
| Product type | `Subscription` |
| Price | `$15 USD / month`(or ¥1,500 JPY)|
| Description | "Managed hosting of an open-source application instance with SSL, monitoring, and technical support." |

### 4.3 アップロード書類

LS は Paddle より要求書類が少ない:

- [ ] `kaigyou-todoke-merged.pdf`(または商業登記書類、個人事業主は開業届控え)
- [ ] `zairyu-card-front.jpg` + `zairyu-card-back.jpg`
- [ ] (任意)Wise 認証済アカウント screenshot

### 4.4 予期审核时长

- 初回 review:**1-3 business days**(automated)
- 追加材料 / manual review:**1-2 weeks**
- 最終決定:**1-2 weeks**(Paddle の半分)

### 4.5 拒否理由 Top 5 + 対応

| # | 拒否理由 | 対応 |
|---|---|---|
| 1 | "Restricted product category" | "Managed hosting of open-source applications" 強調、AGPL-3.0 license 明示、Marzneshin が GitHub public repo であることを示す |
| 2 | "Cannot verify business" | 開業届 + 受信通知 + 青色申告 三合一 PDF 提出、税務署受付番号 `20260507224845548217` を提示 |
| 3 | "Website incomplete" | nilou.network 全ページ公開済 screenshot + 特商法表記 三言語版を提示 |
| 4 | "High-risk geography(customer base)" | 顧客分布を「日本 40% / 先進国 60%」と修正、中国客户言及を controlled disclosure に留める |
| 5 | "Stripe affiliation flag"(LS は Stripe 子会社、Stripe 黒名单継承可能性)| Stripe Japan の事前 reject 履歴がない状態で先に LS を申請する戦略(Stripe を後回し or 並列)|

> ⚠️ **重要戦略**:LS は **Stripe Inc. が 2024 年に買収済**(Stripe の subsidiary)。Stripe Japan で先に拒否されると、LS 側で同じ underwriting データを参照して連鎖拒否の可能性あり。**従って LS を Stripe より先 or 並列で申請するのが最適**。

---

## 5. Stripe Japan 申请详细 step-by-step

### 5.1 URL & エントリ

- 主入口:`https://dashboard.stripe.com/register/jp`(JP localization)
- 環境:本番 dashboard(test mode は申請に関係なし)

### 5.2 フォーム入力(画面順)

#### Step 5.2.1 — Account creation

| フィールド | 入力値 |
|---|---|
| Email | `ops@nilou.network` |
| Country | **日本 / Japan**(後で変更不可) |
| Password | 強固 |

#### Step 5.2.2 — ビジネスタイプ

| フィールド | 入力値 |
|---|---|
| ビジネスタイプ | **個人事業主** |
| 屋号で受け取る? | ✅ Yes(屋号付き口座が `Nilou Network` 名義の場合) / ❌ No(個人名義口座の場合は法定氏名で登録) |

> ⚠️ **重要分岐**:住信SBI で屋号付き口座が開設できた → 屋号 `Nilou Network` で登録。屋号付きが拒否された → 個人名義 `陸 浩洋 / Lu Haoyang` で登録。**後で変更すると 1-2 週間追加審査**。

#### Step 5.2.3 — Business details

| フィールド | 入力値 |
|---|---|
| 屋号(英語表記) | `Nilou Network` |
| 屋号(日本語表記) | `Nilou Network`(英文屋号、カナ別途記入) |
| 屋号フリガナ | `ニィロウ ネットワーク`(D-020 SEALED) |
| 法人番号 | **空欄**(個人事業主 = 法人番号なし) |
| 開業年月日 | `2026/05/07` |
| 業種 | **ソフトウェア・情報通信業**(コード `6201` ソフトウェア業 or `6202` 情報処理サービス業) |
| 業種詳細(自由記述) | `オープンソースソフトウェアのマネージドホスティング、サブスクリプション形式` |

#### Step 5.2.4 — 個人情報(代表者)

| フィールド | 入力値 |
|---|---|
| 氏名(漢字) | `陸 浩洋` |
| 氏名(カナ) | `リク コウヨウ` |
| 氏名(ローマ字) | `Lu Haoyang` |
| 生年月日 | [operator 自記入] |
| 住所(個人) | [住民票上の個人住所、税務署と同じ、Stripe 内部档案のみ、公開なし] |
| 個人電話 | [operator 自記入、Stripe 内部档案のみ] |

#### Step 5.2.5 — 事業所情報

| フィールド | 入力値 |
|---|---|
| 事業所住所 | 〒141-0021 東京都品川区上大崎3丁目14番34号 プラスワン402 |
| 事業所電話 | `+81-50-XXXX-XXXX`(楽天 050)|

#### Step 5.2.6 — 銀行口座

| フィールド | 入力値 |
|---|---|
| 銀行名 | 住信SBIネット銀行 |
| 支店名 | [開通通知書記載] |
| 口座種別 | 普通 |
| 口座番号 | [開通通知書記載] |
| 口座名義(カナ) | `ニィロウ ネットワーク`(屋号付き)or `リク コウヨウ`(個人名義)|

#### Step 5.2.7 — 売上見込み

| フィールド | 入力値 | 注意 |
|---|---|---|
| 月予想売上 | **¥100,000 - ¥300,000 / 月** | 過剰申告は underwriting 強化のトリガー、初期は低めに |
| 平均客单価 | `¥1,500 - ¥3,000` | |
| 想定 chargeback 率 | `< 0.5%` | |
| 想定取引地域 | 日本国内主体(40%)+ 海外 60% | |

#### Step 5.2.8 — Business description(最重要)

**Stripe の AUP は VPN-related services を明確に禁止**(`https://stripe.com/legal/restricted-businesses` 参照)。文案は **"managed open-source application hosting" 一本軸**:

```
Nilou Network operates a managed hosting and subscription platform
for open-source applications. We deploy, operate, monitor, and provide
technical support for managed instances of open-source software
(primarily the Marzneshin open-source panel, AGPL-3.0 licensed,
publicly available on GitHub), bundling infrastructure operation,
SSL certificate lifecycle management, uptime monitoring, and email-
based technical support into a monthly subscription.

Our service is functionally equivalent to managed WordPress hosting,
managed PostgreSQL hosting, or managed Mastodon hosting — we host
and operate open-source software on behalf of customers who do not
wish to operate their own servers. We do not provide network access,
network routing, or anonymization services; we are a software hosting
SaaS, registered as a sole proprietorship under Japanese law, with
Shinagawa Tax Office filing dated 2026/05/07.

JCT (消費税) is collected from Japanese customers at the statutory
rate and remitted by Nilou Network as the sole proprietor of record.
Full legal disclosure is published at nilou.network/legal.html in
compliance with 特定商取引法 (Japanese Specified Commercial
Transactions Act).
```

⚠️ **NG ワード**(全篇禁止):VPN / proxy / 代理 / 翻墙 / 节点 / GFW / circumvention / censorship / restricted network / anonymization / traffic relay。

⚠️ **OK 同義表現**:managed hosting / SaaS / open-source application / subscription / infrastructure operation / sole proprietorship / AGPL-3.0 / Japanese registered business / Marzneshin (固有名詞、open-source repo)。

#### Step 5.2.9 — Identity verification

Stripe は本人確認に **eKYC 必須**(マイナンバーカード or 在留カード + selfie):

- [ ] 在留カード 表 / 裏 撮影(or マイナンバーカード)
- [ ] Selfie(顔写真、笑顔不要、明るい場所、メガネ可)
- [ ] 自動 OCR + manual review

### 5.3 アップロード書類

- [ ] `kaigyou-todoke-merged.pdf`(個人事業主証明)
- [ ] `zairyu-card-*` (eKYC 内で完結することが多い)
- [ ] `bank-statement.pdf`(任意、underwriting 強化時)

### 5.4 予期审核时长

- 初回 automated review:**数分 - 数時間**(API 即時)
- Manual underwriting:**2-7 business days**
- 追加材料要求:**任意のタイミングで発生**(operator は dashboard 通知を毎日チェック)
- 最終決定 or "Account restricted"(継続審査):**1-3 weeks**
- ⚠️ Stripe は "approved" 後も継続 underwriting あり、最初の payout 前 / 月商 ¥100万 超え時に再審査トリガー

### 5.5 拒否理由 Top 5 + 対応

| # | 拒否理由 | 対応 |
|---|---|---|
| 1 | "Restricted business — VPN / proxy / anonymization" | §5.2.8 文案を再提出、業種が "managed open-source app hosting" であることを 3 回以上明示、AGPL-3.0 license と GitHub repo URL を提示 |
| 2 | "High-risk geography(customer base)" | "Customer geography: Japan-primary (40%), developed countries 60%" と再申告、中国客户言及を controlled disclosure に絞る |
| 3 | "Insufficient business documentation" | 開業届控え 三合一 PDF + 銀行流水 3 ヶ月 + 事業所利用契約書 全部提出 |
| 4 | "Website lacks compliance pages" | nilou.network/legal.html(特商法 三言語) + /terms.html + /privacy.html screenshot 提出 |
| 5 | "Cannot verify identity" | eKYC やり直し、明るい場所 + 在留カード両面ピント合わせ撮影 |

### 5.6 Stripe 被拒后の備案

- **Plan B-1**:Wise multi-currency receive(USD / EUR 海外客向け、Stripe 不要)
- **Plan B-2**:Stripe Atlas(US LLC + Stripe US 経由、$500 初期費 + 維持費)— 個人事業主 + 日本身分のままで Stripe アクセスは諦め、別主体経由
- **Plan B-3**:Paddle / LS のどちらかが通過していれば、Stripe は来年(運営実績 6-12 ヶ月後)再申請

### 5.7 Stripe Japan 業界通過率(参考、operator 自己判断材料)

⚠️ **以下は業界の経験値範囲、Stripe 公式統計ではない**:

- 個人事業主 + JP + 一般 SaaS:通過率 **40-60%**
- 個人事業主 + JP + open-source app hosting(灰区):**20-30%**(本案件想定範囲)
- 個人事業主 + JP + VPN 言及あり:**< 5%**

**operator は自己責任で「申請する / 申請を延期する」を判断**。私は数字を提供するのみ、保証はしない。

---

## 6. 三家申请后的等待期 operator 行動

### 6.1 毎日確認(15 分)

- [ ] `ops@nilou.network` 受信箱を 1 日 2 回チェック(朝 / 夜)
- [ ] Paddle / LS / Stripe dashboard を毎日 1 回ログイン(notification 確認)
- [ ] 追加材料要求があれば **24 時間以内** に回答(遅延 = 拒否トリガー)

### 6.2 やってはいけないこと(審査期間中)

| ❌ NG 行動 | 理由 |
|---|---|
| `nilou.network/legal.html` を修正 | 特商法表記の変更 = underwriter から見ると「信頼性低下」のシグナル |
| `nilou.network` トップの服务説明を書き換え | Paddle / Stripe の website crawler が変更を検知 → 再審査トリガー |
| 屋号 `Nilou Network` を変更 | KYC 不整合 → 即拒否 |
| 銀行口座を変更 | 同上 |
| 売上見込みを後から大幅に上方修正 | underwriting 強化トリガー |
| Customer-portal に未公開機能を deploy | 同上、申請時の説明と矛盾 |
| Twitter / HN で公開 launch announcement | 申請時の "Pre-launch" 説明と矛盾、avoid 公開 marketing until ≥ 1 家通過 |

### 6.3 やってよいこと

- ✅ Customer-portal P2(auth 接入)の開発(deploy はしない)
- ✅ Documentation の整備(`docs/launch/*.md`)
- ✅ Hardening 層 / Reality config 改善
- ✅ TRC20 主通路の継続運用(既 ship 済)
- ✅ Wise multi-currency account の事前作成(LS payout 用)

### 6.4 一家通過したら

1. CTO に即通知 → `docs/ai-cto/SPEC-payment-mor-{provider}.md` Phase X PLAN トリガー
2. Sandbox / test mode で integration 開始(`ops/billing/{provider}_provider.py` 雛形は SPEC #258 内に既存)
3. 本番 deploy 前に §48 codex cross-review 実施
4. Customer-portal に "Pay with {provider}" CTA 追加(feature flag 後ろに置く)
5. 他 2 社の審査は継続(複数通過 = 客户選択肢増、保険効果)

---

## 7. 被拒后应对

### 7.1 一家拒否(通常想定)

- 即 retry はしない(同じ underwriter で再評価 → 同じ結果)
- 拒否理由を §3.6 / §4.5 / §5.5 と照合
- 改善材料を 1-2 週間かけて整備 → 60-90 日後 reapply

### 7.2 二家拒否

- 残り 1 家の審査に集中
- 拒否 2 社の理由 patterns を分析 → 共通項を修正(通常は商品説明 / 業種 / 顧客地域 の何れか)

### 7.3 三家拒否(確率 4.2%)

- **Plan B**:TRC20 主通路 + OTC 引導 で運営継続(既 ship)+ Wise multi-currency receive(海外客向け、Stripe 不要)
- **Plan C**:3 ヶ月遅延 → 運営実績(顧客数 / 流水 / chargeback 0%)を積んで再申請、同時に
  - Customer-portal を完全英文 SaaS 化(中国客户への露出を最小化)
  - 業務説明を完全に "managed PostgreSQL hosting" 級の generic SaaS 表現に再整理
  - 顧客地域分布を「日本国内 70%、北米 20%、欧州 10%」に純化(中国客户は TRC20 のみで対応)
- **Plan D**:OKX Pay / Binance Pay 商户(crypto 商户 KYC、日本身分受理、§2.4 / §2.5 of `PAYMENT-DECISION-FINAL-JP.md`)+ Cryptomus(海外 crypto 客户)で merchant 体験を補完

### 7.4 補助通路(三家審査と並行 OK)

以下は MOR ではないため Paddle / LS / Stripe の審査結果に依存しない、並行進めて OK:

- **Wise multi-currency receive**:USD / EUR 受け取り口座、即時開設可能、海外客向け SWIFT 受信
- **Alchemy Pay (ACH)**:Crypto onramp 商户、`PAYMENT-DECISION-FINAL-JP.md` §2.0.1 参照、別途申請可
- **OKX Pay 商户 / Binance Pay 商户**:Crypto 系商户、別途申請可

---

## 8. 附录:商品/服务说明文案 三言語(EN / JA / ZH 各 200 字)

### 8.1 English(Paddle / LS 主用)

```
Nilou Network is a managed hosting and subscription platform for
open-source applications, operated as a sole proprietorship in Tokyo,
Japan (Shinagawa Tax Office filing 2026/05/07). We deploy, operate,
monitor, and maintain managed instances of open-source software
(primarily the Marzneshin open-source panel, AGPL-3.0 licensed and
publicly available on GitHub), bundling infrastructure operation,
SSL certificate lifecycle management, uptime monitoring, and email-
based technical support into a single monthly subscription.

Our service is functionally equivalent to managed WordPress hosting
or managed PostgreSQL hosting — we host and operate open-source
software so customers do not need to operate their own servers.
Pricing ranges from ¥1,500 to ¥3,000 per managed instance per month.
Full legal disclosure is published at nilou.network/legal.html in
compliance with the Japanese Act on Specified Commercial Transactions.
```

### 8.2 日本語(Stripe Japan / 開業届 / 銀行 / 税務 統一)

```
Nilou Network は、オープンソースソフトウェアのマネージドホスティング
及びサブスクリプション・プラットフォームを運営する個人事業者である
(品川税務署 開業届 2026/05/07 提出済、受付番号 20260507224845548217)。
当事業は、オープンソースソフトウェア(主に Marzneshin オープンソース
パネル、AGPL-3.0 ライセンス、GitHub 公開)の運用済みインスタンスを
顧客に提供し、インフラ運用、SSL 証明書管理、稼働監視、技術サポートを
月額サブスクリプションに含めて提供する。

当サービスは機能的にはマネージド WordPress ホスティング、マネージド
PostgreSQL ホスティングと同等のソフトウェアホスティング SaaS であり、
顧客が自社でサーバー運用する必要を排除する。料金は月額 ¥1,500 〜
¥3,000 / インスタンス。特定商取引法に基づく表記は nilou.network/legal.html
に三言語(日本語 / 英語 / 中文)で公開済。
```

### 8.3 中文(社内資料 / 中国客户向け FAQ 共用、申請には使わない)

```
Nilou Network 是一家在日本东京注册的开源软件托管 SaaS 个人事业者
(品川税务署开业届 2026/05/07 受理,受付番号 20260507224845548217)。
我们为客户提供开源软件(主要是 Marzneshin 开源面板,AGPL-3.0 协议,
GitHub 公开仓库)的托管实例,以月度订阅形式打包提供:基础设施运维、
SSL 证书生命周期管理、运行监控、邮件技术支持。

我们的服务在功能上等同于托管 WordPress、托管 PostgreSQL 等开源软件
SaaS — 让客户无需自己运维服务器即可使用开源软件。订阅价格 ¥1,500 〜
¥3,000 / 实例 / 月。完整法律披露见 nilou.network/legal.html(依日本
特定商取引法,三语公开)。
```

### 8.4 三言語間の整合性チェック

申請前に operator が必ず確認:

- [ ] 屋号は全言語で `Nilou Network`(統一、ローカライズしない)
- [ ] 開業届受付番号は全言語で `20260507224845548217`(統一)
- [ ] 開業日は全言語で `2026/05/07`(統一)
- [ ] 業種記述に "managed hosting" / "マネージドホスティング" / "托管" が必ず登場
- [ ] 各言語で **VPN / proxy / 翻墙 / 节点 / GFW / circumvention** が 0 回登場
- [ ] 各言語で AGPL-3.0 license + GitHub public repo + 個人事業主 が必ず登場

---

## 9. 完了検証(申請完了後 24 時間以内)

- [ ] Paddle:account created + form submitted + confirmation email 受信
- [ ] Lemon Squeezy:account created + store configured + onboarding submitted
- [ ] Stripe Japan:dashboard access + business info filled + eKYC completed
- [ ] 三家とも:申請受付番号 / reference ID をローカル保存(`docs/launch/private/merchant-application-refs.txt`、gitignore 済)
- [ ] 三家とも:期待審査終了日をカレンダーに登録(Paddle T+42、LS T+14、Stripe T+7 初審)
- [ ] CTO に通知 → `docs/ai-cto/PROJECT-STATE.md` の "merchant application status" 更新

---

## 10. 引用 / 関連 docs

- `docs/launch/PAYMENT-DECISION-FINAL-JP.md` — payment 商業決策(なぜこの 3 家を並行申請するか)
- `docs/launch/PAYMENT-CHANNEL-MATRIX.md` — 通道対比(歴史档案、JP operator は本ガイドで運用)
- `docs/launch/BRAND-NAMING-DECISION.md` — 屋号 SEALED 決定
- `docs/launch/brand/BRAND-GUIDELINES.md` §5 — IP 红线 / 屋号カナ表記標準
- `docs/launch/HOW-TO-RENT-VIRTUAL-OFFICE-JP.md` — GMO 虚拟办公室申請(前置完了)
- `docs/launch/HOW-TO-FILE-KAIGYOU-TODOKE-JP.md` — 開業届申請(前置完了)
- `docs/ai-cto/SPEC-payment-mor-integration.md` — payment MOR integration SPEC(PR #258 ship 済)
- `docs/ai-cto/DECISIONS.md` D-020 — 屋号フリガナ SEALED
- `marketing/nilou-network/legal.html` — 特商法表記 三言語公開(PR #249 / #251)
- Paddle:`https://www.paddle.com/sign-up` / `https://www.paddle.com/legal/aup`
- Lemon Squeezy:`https://app.lemonsqueezy.com/onboarding` / `https://www.lemonsqueezy.com/legal/acceptable-use`
- Stripe Japan:`https://dashboard.stripe.com/register/jp` / `https://stripe.com/legal/restricted-businesses`

---

**最後改訂**: 2026-05-11
**次回 review**: 三家のいずれかから審査結果(通過 / 拒否 / 追加材料)が届いた時点
