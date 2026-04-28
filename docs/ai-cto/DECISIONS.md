# 决策记录(DECISIONS)

> 格式:每条决策 = (编号 + 日期 + 决策 + Why + How to apply + 推翻条件)
> 倒序排列,最新在上

---

## D-017 | 2026-04-28 | 差异化 #4(一体化部署)首件工具 = AGPL §13 自检脚本(`agpl-selfcheck.sh`),把 "合规验证" 从 doc-only 升到可执行

**决策**:差异化 #4("一体化部署 / 运营加固")的第一件 ship 工具是 `deploy/agpl-selfcheck.sh`(PR #88,302 LOC bash),**不是** install.sh / Ansible / CF Tunnel 自动化。这条排序固定下来,后续工具按下方"工具序列"推进,不打乱。

**Why**:

- **AGPL §13 是 fork 的 day-1 合规义务**,从 2026-04-21 fork 起就背着这个长悬 audit gap。Marzneshin / Marzban 上游均无原生 AGPL §13 自检工具,本 fork 第一件工具就把这个 gap 关闭,等同于把"合规自动化"作为差异化的开局亮相。运营客户看一眼 README 就知道这个 fork 比 Marzneshin 上游更靠谱(后者跑了 5 年也没原生自检)
- **一体化部署的工具序列**应该按"风险递减"排:agpl-selfcheck < install.sh < Ansible playbook < CF Tunnel 自动化。前者出错只是 false-warn(运营手工核账),后者出错可能炸全节点(install.sh 错配)/ 重复 OS 配置(Ansible)/ 泄露 token(CF API misuse)。先 ship 低风险的把工具链规范跑通,再上高风险的
- **bash 选择 vs Python 选择**:agpl-selfcheck 是部署侧脚本,运营 VPS 上不一定有 Python 3.12,bash 4+ 几乎无环境依赖,适合"一键校验"场景;后续 install.sh / CF Tunnel 同思路 bash;Ansible playbook 是 YAML(Ansible 自带 Python runner)。Python 工具留给"在 panel 进程内"跑的(billing scheduler / Reality audit endpoint)
- **"compliance-as-feature"设计意图**:把合规当差异化卖点,不当成纯成本中心。AGPL 原本是"约束 fork 必须开源",我们反过来把"自动校验合规"包装成产品价值 —— 这是面向商业化机场客户(他们也是 AGPL 下游)的额外好处

**How to apply**:

- `deploy/agpl-selfcheck.sh` 是模板,后续 deploy 工具可参考其结构(顶部 banner / 颜色 / 子检查函数 / 退出码契约 / NOTICE / 文档段)
- 工具序列按 "agpl-selfcheck → install.sh(D.1)→ Ansible(D.4 or D.2)→ CF Tunnel" 推进,**不并行,不调序**(降低 S-D 复杂度,sibling agent 一次推一个)
- 每件工具 ship 前后必须更新 `deploy/README.md` 索引段(类似 OPS-* runbook 索引)
- 每件工具必须有"零依赖运行" + "退出码契约 0/1/2" + "支持 `--help` 输出"三条 invariant
- 日历提醒(本批次未做):2026-07-28 评估差异化 #4 整体进度,如果 install.sh / Ansible / CF Tunnel 还没 ship,触发优先级提升

**推翻条件**:
- 客户真实反馈把 install.sh 看得比 AGPL 自检更重要(数据点 ≥ 3 个客户) → 重排工具序列
- 上游 Marzneshin 自己出了 AGPL 自检 → 我们的差异化优势消失,转而做更复杂的 deployment audit(广义合规审计)
- AGPL 在某主权法域被强制注释化 / 替换 → 本工具变成历史代码,差异化 #4 整个重构

---

## D-016 | 2026-04-28 | A.4 商业化前端 = admin-on-behalf-of-user checkout(BRIEF option A),不另起 user portal 子项目

**决策**:A.4 用户购买 UI(`dashboard/src/modules/billing/admin-checkout/`)flip-on 路径选 **BRIEF-billing-user-auth-blocker.md option A**:把 A.4 重定位为管理员代下单代付的 admin-on-behalf-of-user checkout 工具,**不**为终端用户建独立 SPA / web auth / 自助门户。

- 复用 admin sudo 路径(已有 panel auth)+ 加 UserSelector debounced search(`/users?username=<typed>`)+ 接真 `POST /api/billing/cart/checkout` admin endpoint
- sidebar 路径:`Billing → Checkout`(SudoRoute 包裹)
- 路径改名:`dashboard/src/modules/billing/user/` → `dashboard/src/modules/billing/admin-checkout/`(PR #89 命名清理)
- 删除 mock-gate / `MyInvoiceRow` / `InvoicePollSnapshot` 等用户侧专用代码(admin invoices 页 #35 已覆盖)

**Why**:

- **Marzneshin upstream 现状**:VPN 用户**没有**panel web auth;现有用户认证只针对管理员(`Admin` 表 + JWT)。给最终用户做 web 自助意味着新建 user 表 / 注册流程 / 邮箱验证 / 密码重置 / OAuth(可选)/ 会话管理 / RBAC 边界划分 —— 等同新起一个 user portal 子项目,工程量 2-4 周,且会引入新攻击面(暴力撞库 / 重置流程钓鱼 / 会话劫持等),与"商业化机场 MVP" 时间盒不匹配
- **现实运营观察**:中国小型机场实际运营都是 Telegram 群人工开单(运营方在群里收用户付款截图,手工延期或开新订阅);自助 SPA 即使做出来,真实使用率也低,客户不会感激
- **组件 90% 复用**:cart summary / plan card / payment method picker / checkout flow 在 admin checkout 路径下功能相同,只换 auth 入口 + 加 UserSelector
- **决策对齐架构哲学**:A.4 完结让商业化(A.x)5/5 端到端跑通(数据模型 + Admin UI + EPay 后端 + TRC20 后端 + admin checkout UI),关键路径不依赖未建的 user portal;真实业务侧"用户自助"诉求成熟时(数据点 ≥ 3 个客户问)再开 SPEC-user-portal,不被这次决策锁死
- **完整 BRIEF 在 `docs/ai-cto/BRIEF-billing-user-auth-blocker.md`**(PR #86)— 决策上下文 + option A/B/C 对比 + 选 A 的具体理由 + 后续打开 user portal 的硬条件全在那

**How to apply**:

- A.4 后续动作收口:今后所有 "用户购买 UI" 工作只指 `dashboard/src/modules/billing/admin-checkout/` 这一处
- 路由导出:`billing.purchase.lazy.tsx`(SudoRoute),sidebar `Billing` 组追加 "Checkout"(append-only,SESSIONS.md 冲突地带表已记录)
- 删除已弃用代码:`my-invoices` route / mock-gate / `MyInvoice*` types(已在 #87/#89 完成)
- i18n 子树:`page.billing.purchase.*`(en/zh-cn 已加,其他 4 语言走 i18next defaultValue fallback,符合 L-012 防线)
- **不写**任何 user-side auth / register / login 代码;真有人提此请求 → 引用本决策驳回,要求先开 SPEC-user-portal

**推翻条件**:

- ≥ 3 个真实客户独立请求"让用户自助充值",且**无管理员愿代办**(现实数据点,不是脑补) → 开 SPEC-user-portal,A.4 之上加 user-side checkout layer,本决策升级为 D-NNN-user-portal-launch
- Marzneshin upstream 引入原生 user web auth → 本 fork 直接消费 upstream 的 auth 而非自建,本决策的"无 web auth"前提不再成立
- 法律 / 合规要求 PoP(proof-of-purchase by user)签字必须用户本人完成 → admin-on-behalf 路径在该司法管辖区作废,需重新设计

---

## D-015 | 2026-04-26 | 链上支付匹配策略 = "memo > exact-amount + window";拒绝模糊;cents-dither 解并发;rate 操作员锁定

**决策**:在 A.3 TRC20 落地中固化三条配套政策:

1. **匹配策略**:
   - **优先 memo 匹配**(HMAC-SHA256 8 字符 salt 化,`O(1)` 不模糊)
   - **退回精确金额 + 时间窗口匹配**(对付 strip 掉 memo 的钱包 ~50%)
   - **没有第三种**:不做"差不多" / "近似" / "前后 X 分钟内任意金额"
2. **欠付 / 超付都不补偿**:用户付了 0.999 USDT 而账单 1.000 USDT → 不匹配,用户必须重发。**不**自动给个折扣(防"故意少付"的滥用),**不**自动留差额做 credit(防 operator 欠用户钱)。审计干净 = 钱不出错。
3. **cents-dither 解并发**:`expected_amount_millis += invoice_id % 1000`。1000 个分散值,假设 operator 同一时刻 < 1000 个 awaiting_payment 直收发票(实际 < 几个),collision 概率忽略。**不用** UUID / random / 时间戳 dither —— 为了重启幂等可重算。
4. **rate 操作员锁定**:`BILLING_TRC20_RATE_FEN_PER_USDT` 是 env 锁的,不自动 fetch CoinGecko / Binance。理由 = 多一个外部 API 依赖 = 多一个故障面 + 市场波动期匹配歧义(用户点 checkout 时 7.20,实际付款时 7.30 = 多付 / 少付都尴尬)。Operator 周复盘 + 设 env + 重启,1-2% 偏差 < ticker outage 风险。
5. **`MIN_CONFIRMATIONS=1` 默认**:Tron 3 秒块时,`confirmed=true` ≈ 不可逆。Bitcoin 那种 6 / 12 confirmation doctrine 不适用。Paranoid operator 可调 19(Tron SR round)。

**Why**:
- 模糊匹配的诱惑很大("用户少付几分,给个面子让通过"),但开了这个口子之后无法收尾 —— 客户会试探 "9.95 也通过,9.5 呢?";审计 trail 失去精确性;refund 流程变成模糊判断
- 链上没有 chargeback,用户付错就只能让他重发或申请人工退款。**这是协议本身的特性,我们不该去模糊化它**;就像信用卡能 chargeback 是协议特性,我们不该假装没有
- cents-dither 用 `invoice_id % 1000` 而不是 random:**幂等**。重启 panel,memo 还是同 memo,dithered amount 还是同 amount,poller 重新读链可以自洽。Random 化 = DB 必须存 dither 值,重启风险面变大
- rate 锁定是经典"少一个 API 少一个故障点"原则;用户体验 1-2% 偏差感知度极低(都是中国用户对 USDT 价格不敏感)

**How to apply**:
- `ops/billing/trc20_matcher.py` 模块 docstring "Why no proximity / partial match" 段是这条政策的代码版
- `ops/billing/trc20_config.py` 模块 docstring "Why ``BILLING_TRC20_RATE_FEN_PER_USDT`` is operator-set" 段是 rate 锁定的理由
- 14 个 matcher 测试覆盖所有 reject 情况(under-pay / over-pay / 窗口外 / unconfirmed / 小数额),pin 这条政策
- 未来加新支付通道(BTC / ETH / TON 等)时,先回到 D-015 看适不适用;以太坊有 EIP-1559 gas dance 和 chargeback-via-revert 边角,可能需要 D-NNN 单开决策

**推翻条件**:
- 运营调研发现 50%+ 用户会因金额不精确放弃 → 重审欠付政策(可能加"≤ 1¢ 偏差自动放行")
- 真接一家 Tronscan 替代发现 confirmation 模型不一样 → 重审 MIN_CONFIRMATIONS 默认
- USDT 转换为 USD-pegged 但脱锚 → rate 锁定政策需重审(可能要加 max_deviation_pct env 防超偏离)

---

## D-014 | 2026-04-26 | 计费 grant 应用 = `pricing.py` / `grants.py` 双模块分离;`expire_strategy` 升级政策固化

**决策**:在 A.5 scheduler 落地中固化两条配套政策:

1. **模块边界**:`ops/billing/pricing.py` 是**预付**层(纯函数,无 DB,产 `UserGrant`);`ops/billing/grants.py` 是**后付**层(改 `User.data_limit` / `User.expire_date` / `User.expire_strategy`,持有 grant-application policy)。两者互不 import,scheduler 是唯一胶水。
2. **`expire_strategy` 升级政策**:
   - `FIXED_DATE` 用户买 duration grant → 从 `max(now, expire_date)` 起延长 `days`(lapsed 用户 re-anchor 到 now,避免前 24h 已过期)
   - `NEVER` 用户买 duration grant → 升 `FIXED_DATE`,anchor 到 `now + days`
   - `START_ON_FIRST_USE` 用户买 duration grant → 同上,升 `FIXED_DATE`,anchor 到 `now + days`,且**清空** `usage_duration` / `activation_deadline`(对 `FIXED_DATE` 无意义,留着会让 admin UI 显示混乱)
3. **`data_limit` policy**:bytes-additive,`NULL` 视为 0 baseline。"无限用户买 5GB 流量包" → 变成有限 5GB(运营者别这么卖,UI 层防住)。

**Why**:
- pricing/grants 分离让 cart-checkout(预付,UI 调)不必 import SQLAlchemy `User`,降低 import 图复杂度。同时 grant-application 的 policy 决策(lapsed re-anchor / strategy promotion)集中在一处,future audit / debug 不必 grep 多文件
- `max(now, expire_date)` 这条没人会一开始想到,但是真实运营中**必踩**:用户付了款几小时后才意识到,或者 cron 任务延迟,如果不 re-anchor 就实际损失了几小时窗口,客户理论上能投诉。这里把规则写死在代码 + DECISIONS,等同合同条款
- promote `NEVER` / `START_ON_FIRST_USE` 到 `FIXED_DATE` 是必然(他们付钱了,该计时);清 `usage_duration` 是收尾,不清不会出错,但是会让 admin 看不懂"为什么这个 fixed_date 用户还有 usage_duration 字段"

**How to apply**:
- `ops/billing/grants.py` 的模块 docstring 长版讲了三条政策
- `tests/test_billing_grants.py` 11 个测试逐条验证(`test_grant_extends_lapsed_fixed_date_user_from_now_not_past` 是最关键的"合同条款"测试)
- 未来调整 grant 政策(比如运营要支持 trial-to-paid 平滑过渡)→ 改 `apply_grant_to_user` + 加测试 + 更新本决策

**推翻条件**:
- 运营改用"扣费式"(用户欠款不延期)模型 → 全套重写
- 引入按月订阅(recurring)而非按次购买 → grants.py 政策需扩展
- expire_strategy 表结构变更(upstream 加新策略)→ 重审 promotion 规则

---

## D-013 | 2026-04-26 | `v2share==0.1.0b31` 保留 + vendor 备胎规划,**不**主动替换

**决策**: Round 1 leftover "v2share beta 替代评估" 结论 = **保持现状**:

- `requirements.txt` 继续 pin `v2share==0.1.0b31`(就是 PyPI 当前最新)
- `app/utils/share.py` 不动
- 触发 vendor-into-repo(选项 C)的硬条件写入 `docs/ai-cto/RESEARCH-v2share-evaluation.md`
- 半年(2026-10-26)日历复评 + 任意硬条件命中即触发

**Why**:
- v2share 与上游 Marzneshin 命脉绑定(同一作者 `khodedawsh`)。Marzneshin 仍
  在 2025-10 发版,v2share 间接继续受益;拆开等于双重负担
- "beta" 是作者版本号习惯,**不存在 stable 0.1.0 可升**。"升到稳定版" 不是
  一个真选项
- v2share 覆盖 xray + sing-box + clash 三协议订阅生成,**没有同等替代 Python
  lib**。自己实现 = 1-2 周开发 + 长期协议 schema 跟踪负担,投入产出比最差
- License 缺失风险通过"维护者归属推断"软处理(作者其他 repo 全 AGPL-3.0),
  生产 license audit 时单独标注;短期可接受
- CVE 由 `pip-audit` CI 自动覆盖;14 个月无 commit ≠ 高 CVE 风险(代码量小、
  无网络层、纯字符串/JSON 生成)

**How to apply**:
- `requirements.txt` 在 `v2share==0.1.0b31` 上方加 8 行注释,解释 beta 不是
  临时选择,指向 RESEARCH-v2share-evaluation.md(本 PR)
- LESSONS / 之后 STATUS leftover 该项标 ✅ 已结案,链接到 D-013
- 半年后(2026-10-26)由 S-O 触发复评 — 把 PyPI / GitHub 数据再抓一次,
  delta 写到 RESEARCH 文件底部
- 触发条件命中(repo archive / xray-singbox 跨大版本 6 个月无适配 / 我们
  自己发现 bug 上游不响应)→ 立即开 vendor PR,把 `khodedawsh/v2share` 内
  容拷进 `vendor/v2share/` 并改 import,同时在仓库根 LICENSE 区交代清楚

**推翻条件**:
- v2share 上游恢复活跃且发 1.0 稳定版 → 升级 pin,本决策完成历史使命
- 我们决定 fork 为 `aegis-share`(选项 D)→ 开新决策 D-NNN 取代本条
- Marzneshin 上游被 archive → 整个 fork 战略要重审,v2share 只是其中一条线

---

## D-012 | 2026-04-26 | Reverse-proxy 信任 = per-feature `*_TRUSTED_PROXIES` CIDR env,不做 panel-wide middleware

**决策**: 任何 IP-aware feature(rate limit / billing webhook / 未来 iplimit allowlist 的边缘用例 / 任何端点级 IP 白名单)各自挂一个 `<FEATURE>_TRUSTED_PROXIES` env,**不要**写一个 panel-wide `TrustedProxyMiddleware`。模板代码已经在 `ops/billing/config.py:BILLING_TRUSTED_PROXIES` + `ops/billing/checkout_endpoint.py:_peer_is_trusted_proxy`,下个 IP-aware feature 直接 copy。

**Why**:
- **反代信任假设是 per-deploy**:同一 panel 可能 billing webhook 走 Nginx-on-same-host(只信 127.0.0.1)而 iplimit 边缘用例走 CF Tunnel(只信 CF egress 段)。一个全局 middleware 强行让所有 feature 共享同一个 trusted-proxy 列表,把 "管什么 IP 算客户端" 这个 per-feature 决策粗化掉
- **错配在功能边界 fail 比在全站 fail 好**:billing trusted_proxies 错配 → billing webhook 失败,运营立即看到;panel-wide middleware 错配 → 所有 IP-aware 行为静默错位,可能几天才发现
- **渐进迁移友好**:每个 feature 自带 env,启用一个不影响其他;global middleware 上线即影响所有,推不动新 feature 加 IP 信任时只能"一起改"或"一起不改"
- **直接公网部署的默认 = 空 = 不信 XFF**(L-019 防线),global middleware 找不到这种"分通道默认值"的位置
- 现实数据点:之前 Round 1 STATUS 列了"TrustedProxyMiddleware"作为待补,但**到 Round 3 mid 唯一真正需要它的 feature 是 billing webhook**;其他四个 IP-aware feature(rate-limit / iplimit / sni / admin)目前没有 reverse-proxy 信任需求,做 panel-wide 等于**为 0 个真实使用者写抽象**

**How to apply**:
- IP-aware feature 起新代码时,直接 copy `ops/billing/config.py` 的 `_parse_trusted_proxies` + `<FEATURE>_TRUSTED_PROXIES` 解析模式
- env 命名固定后缀 `_TRUSTED_PROXIES`,`.env.example` 必须有解释段(L-019 模板)
- feature 的"获取客户端 IP"helper 必须做 trusted-proxy gate:peer 是 trusted = 信 XFF,否则用 transport peer
- 测试套必须有 spoofing 反例(peer untrusted + spoofed XFF → 拒绝),模板见 `tests/test_billing_checkout_webhook.py:test_webhook_ip_allowlist_ignores_spoofed_xff_when_peer_untrusted`
- **不要**改 `app/marzneshin.py` 加全局 middleware

**推翻条件**:
- **4 个或以上** feature 各自有 `*_TRUSTED_PROXIES` env 且**配置内容完全一致**长达一个轮次(说明 panel 有了固定反代拓扑) → 那时再抽 `app/middleware/trusted_proxy.py` 让 feature opt-in 信全局,对应 L-019/D-012 收编
- 出现"一个端点的请求会被多个反代链路打到"且 panel 必须知道完整链路而非只信 X-Forwarded-For 第一段(例如要做 anti-fraud) → 那时改用 `Forwarded` RFC 7239 头 + 链路全解析,逻辑超出 per-feature env 能力

---

## D-011 | 2026-04-23 | 多会话并行的裁判台机制:SESSIONS.md + worktree 隔离 + append-only 冲突地带表

**决策**: 随 Round 3 mid 进入多会话并行期(Claude Code × N 实例 + Codex + Antigravity/未来 Gemini),引入**三件套**作为并行协作契约:

1. **`docs/ai-cto/SESSIONS.md` 裁判台**:每个 session 开 PR 前必须在活跃表登记编号 / 工具 / 模型 / **独占地盘** / 当前 PR / 状态
2. **冲突地带表 + append-only 规则**:跨 session 必然触碰的公共文件(`hardening/panel/middleware.py` 的 `include_router`、`app/db/extra_models.py` 的 import、`dashboard/src/features/sidebar/items.tsx` 的 sidebar 组、两大 locale JSON、`dashboard/package.json` devDeps、`.github/workflows/*.yml`、`dashboard/src/routeTree.gen.ts`)一律 append-only,后 merge 方 rebase 处理
3. **worktree 隔离铁规则**(#52 固化):每个并发 Claude session 必须有独立 git worktree(`C:/projects/aegis-{B,D,R,X,O}`)或独立 repo 克隆;主 repo 留给 session 0(审阅 + merge 裁判);**禁止在同一个工作目录并发跑 2+ Claude session** —— 违反会造成 branch 切换撞车 / stash 污染 / PR 挂错分支(L-018 全套事故)

**Why**:

- Round 3 opener 之后观察到一个指数级 risk:多个 session 若任意一个动 `app/db/migrations/env.py` 或 `hardening/panel/middleware.py` 都会冲突;SPEC-level 分工不够细,必须到**文件级 append-only 契约**
- 过去靠口头 / PR 描述里写"我动了啥"的做法在 3+ session 并行时不可持续,必须有一份共同看齐的 source of truth
- S-O 作为 part-time 独立 session 而不是混入其他 session,避免让 feature session 分心于文档压缩;铁律 #6 才能真的执行
- **worktree 必要性的直接证据**:S-O 第一次触发时在主 repo 上改 docs,被其他 session 的 `git checkout` 反复吃掉;切到 `aegis-O` worktree 后立即稳定 —— L-018 不是理论,是运营事实

**How to apply**:

- **启动一个新 session**:
  1. 主 repo 跑 `bash tools/setup-session-worktrees.sh`(幂等,首次会建 aegis-B/D/R/X)
  2. S-O 单独建:`git worktree add C:/projects/aegis-O docs/session-O-home`(脚本未覆盖 O,按需手建)
  3. 新 Claude session 第一条消息粘 `cd C:/projects/aegis-{letter}`
  4. Session 自己 `git checkout -b feat/<specific-task>` 切到真工作分支
- **冲突地带改动**:必须 append-only(新段组 / 新 import 行 / 新 sidebar 组);`dashboard/src/routeTree.gen.ts` 禁手改,后 merge 方重跑 `npx tsr generate`
- **PR body 模板**新增两行:`I touch:` / `I don't touch:`,链接到 `SESSIONS.md`
- **S-O 刷新流程**:cd 到 `aegis-O` → `git checkout -b docs/ai-cto/round-N-<milestone>-refresh` → 改 STATUS/LESSONS/DECISIONS/ROADMAP/rules → 独立 PR → 合入后删分支 + 清 worktree
- S-O 触发时只刷 `docs/ai-cto/**`(非 SPEC-*)+ `.agents/rules/**`;如需动代码 → 停,让对应 session 处理

**推翻条件**:
- 并行 session 数回到 ≤ 1(单主 session 推进所有 scope),裁判台变冗余,worktree 规则也可弱化
- 仓库引入 monorepo 工具(Nx/Turborepo/Bazel)提供强隔离的包边界,冲突面自动收拢到包清单
- SESSIONS.md 本身变成冲突点(多人同时追加)—— 这意味着裁判台也要拆,可能的下一步是 per-session charter 文件(`docs/ai-cto/sessions/S-B.md`)

---

## D-010 | 2026-04-22 | 计费 MVP 支付策略:易支付 + TRC20 双轨,放弃 Stripe

**决策**: Round 2 path A(计费 MVP)只做两个支付通道:

1. **易支付(EPay)协议** 作为**主通道**,对接中国码商。面板实现通用协议适配器(兼容 SSPanel / Xboard / v2board 生态中的标准 易支付 接口),管理员在后台填 `merchant_code` + `merchant_key` + `gateway_url` 即启用,支持多家码商并行
2. **USDT TRC20 自建轮询** 作为**副通道**,零第三方依赖,运营方只配置一个公开收款地址,后端每 30 秒轮询 Tronscan 公开 API 匹配订单
3. **明确放弃**:Stripe、NOWPayments 等需要实体/KYC 的支付通道。**不写 stub**

**Why**:

- 运营方条件:**无公司实体、无启动资金、中国用户占多数(~70%)**(见本轮用户确认)
- 中国普通用户 70%+ 无法持有 USDT(2021 "924 通知" 后 fiat-on-ramp 基本关闭,剩余路径对普通用户门槛过高)→ 没有 易支付 通道 = 直接失去大多数市场
- 易支付 是 Chinese 机场生态的**事实标准**,一套适配器 = 兼容数十家码商,可根据需要随时切换运营方
- TRC20 直付作为副通道提供两层价值:(a) 对懂 crypto 的用户提供无中介选项,(b) 当主通道(码商)被冻或跑路时的保险机制
- Stripe 无实体 = 永不可启用。写 stub 让代码假装有选项 = **误导性代码**,有人会以为快启用就试,腐烂没人维护。未来真有实体再专门开一个 PR 加 Stripe,比延续一年半旧 stub 干净

**How to apply**:

- `ops/billing/providers/epay.py` 实现通用 易支付 协议
- `ops/billing/providers/trc20.py` 实现 Tronscan 轮询 + 订单匹配
- `BasePaymentProvider` 抽象封装,未来 BTCPay Server / NOWPayments / Stripe 追加不影响状态机
- 配置硬约束:`BILLING_TRC20_ENABLED` + `BILLING_EPAY_ENABLED` 独立默认关,不启用则对应通道不暴露给用户
- 面板 checkout UI 展示两个 tab(易支付默认、USDT 第二),**不是选单**,让用户明确看到"还有一条路"
- 收款资金路径由用户在**码商后台**选 USDT 结算 → 汇到运营方 TRC20 钱包 → 运营方手动 OTC 换 JPY(见 `OPS-jpy-cashout.md`)
- 码商选择与合作规范见 `OPS-epay-vendor-guide.md`
- Aegis Panel 代码只管"到 USDT 为止";JPY 换汇是**运营过程**不是产品功能,不进代码

**推翻条件**:
- 运营方注册了日本法人且 Stripe 批准了商业类目(极罕见,VPN 类目 AUP 明令禁止) → 追加 Stripe provider(独立 PR)
- 中国码商生态集体崩溃 / 易支付协议变更 → 重新评估通道策略
- 运营方转目标市场(例:转欧洲) → 重新从零设计通道(本决策不再适用)

---

## D-009 | 2026-04-21 | CI 门禁:自研目录扫,upstream 不扫;pip-audit 非阻塞但可视

**决策**: 本项目 CI 的三档硬门禁:

1. `ruff check` + `ruff format --check` **只扫** `hardening/` `deploy/` `ops/` `tests/`。`app/` / `dashboard/` 走 upstream 自己的风格,我们不擅自格式化
2. `pytest` 跑全量 22 个测试,任何 fail 阻塞合并
3. `pip-audit` **step 级** `continue-on-error: true`:job 整体 report 绿,但日志保留发现。继续让 CVE 可见不让它阻塞日常 PR

**Why**:
- 反例:Round 1 第一轮 PR 里 `ruff check .` 扫 upstream 刷出 218 个错误,瞬间不可合。扫自研 = 严格,扫 upstream = churn 战争
- `pip-audit` job 级 `continue-on-error` 会让 PR UI 继续红,对强迫症不友好。step 级 + step 失败等于 `exit 0` job 报绿
- 真的要阻塞 CVE,用 Dependabot / Renovate 自动开 PR,不用门禁打人

**How to apply**:
- 新增自研目录(未来的 `ops/billing/` 等),按相同惯例加到 CI
- upstream 合并后若新增 upstream 代码格式化风格,本项目不强行对齐
- 当下 pip-audit 非阻塞;哪天我们真的要 "新代码禁止引入新 CVE 依赖",单独加一个 job 只扫 diff 的包

**推翻条件**: 我们决定主动接管 `app/` 代码风格(有独立格式化 sweep PR 了),或 CVE 密度突然爆炸需要强门禁。

---

## D-008 | 2026-04-21 | Redis 客户端契约:可选 + lazy + 类型化 disabled

**决策**: `app/cache/redis.py` 的三条硬契约:

1. **可选**:`REDIS_URL` 为空 == 功能禁用。`is_redis_configured()` 返回 False
2. **lazy**:`get_redis()` 首次调用才建连接池,不在 import 时建。startup 不 crash
3. **类型化 disabled**:需要 Redis 的调用方拿到 `RedisDisabled` 异常(dedicated class)而不是 generic `RuntimeError`。调用方按"必需"/"可选"分层选择 fail-loud 或 graceful skip

**Why**:
- 很多 Python 项目的 Redis 客户端 import-time connect → 一处 Redis 下线整个 app 起不来。拒绝这个陷阱
- generic `RuntimeError` 无法让调用方区分"配置没设"和"Redis 挂了"。前者是运维策略决定(刻意禁用),后者是 incident。同名不同因就是 bug magnet
- 配置 Redis 是二阶段:启用 → 提供 URL。两者分离让升级路径平滑

**How to apply**:
- 需要 Redis 的特性(rate limit / 未来的缓存 / session store)**必须** `if not is_redis_configured(): raise FeatureRequiresRedis(...)` 或类似
- 可以降级的特性(opportunistic cache)**必须** `if is_redis_configured(): try_use(...)` 且失败也不影响主路径
- 新增 Redis 消费者时,导入 `from app.cache import get_redis, is_redis_configured, RedisDisabled`

**推翻条件**: 改用别的 KV 存储(比如 etcd)替代 Redis,或产品决定 Redis 从"可选"变"必须"(那时把 `REDIS_URL` 设为必填,删 `RedisDisabled` 代码路径)。

---

## D-007 | 2026-04-21 | compose 可选服务用 profile,upstream-sync 冲突面控制在零

**决策**: PostgreSQL 16 + Redis 7 通过 Docker Compose 的 `profiles: [postgres]` / `profiles: [redis]` 挂在根 `docker-compose.yml`,而不是新开 `docker-compose.prod.yml`。

**Why**:
- upstream `docker-compose.yml` 目前只有 `marzneshin` + `marznode` 两个服务,再加服务的冲突面小到几乎零
- `profiles` 是 Compose 原生机制,没 profile 标志就像服务不存在,零行为变化给 SQLite-only 部署
- 开新 `docker-compose.prod.yml` 会让 "启动命令 + 环境切换" 翻倍,新人容易走错文件

**陷阱**(Round 1 里踩过,经 user 修复):
- Compose 变量展开 (`${VAR:?error}`) 在 **profile 过滤前**发生。对可选 profile 服务的"必需"变量用 `:?err` 会让不启该 profile 的部署直接 parse 失败
- 修法:用 `${VAR:-}` 空默认,运行时启动 postgres 容器自身会因无密码退出,fail 时机正确转移到 startup 而非 parse

**How to apply**:
- 未来新增可选服务(如 `deploy/compose/monitoring.yml` 的 Prometheus + Grafana)继续用 profiles
- 任何 "required env" 检查,用 `:-` + 启动时验证,不用 `:?`
- 文档必须说明:用户启哪个 profile,必须设哪些 env

**推翻条件**: 生产 compose 需要跟开发 compose 本质不同的拓扑(比如生产用 overlay network + external secrets),那时分文件合理。

---

## D-006 | 2026-04-21 | 速率限制契约:opt-in + 失 Redis 即 fail-loud,禁止降级内存

**决策**: `RATE_LIMIT_ENABLED=false` 默认关;开启时 `REDIS_URL` 必须设,否则 **import 时抛 `RateLimitMisconfigured`,panel 拒绝启动**。

**Why**:
- 多 worker 部署下内存计数器让每个 worker 独立限流 = 攻击者直接 scale out 就过,等于没限
- 内存计数器的"看起来有限速"比"明确没有"更糟,是典型**误导性安全**(security theater)
- opt-in 让现有部署升级不吃 429,运维确认 Redis 可达了再翻开关

**How to apply**:
- `/api/admins/token` 已装 `@limiter.limit(ADMIN_LOGIN_LIMIT)`,默认 `5/minute` 按 IP
- 未来装更多 rate limit 的端点(比如 `/api/subscription/*` 防爬),沿用 `hardening/panel/rate_limit.limiter` 单例,别重新建一个 Limiter
- 反代场景下,必须同时配 Uvicorn `--forwarded-allow-ips` 或未来的 `TrustedProxyMiddleware`,否则所有请求看起来同 IP,要么 0 限速要么全 429

**推翻条件**: 未来某端点必须 rate limit 且可接受 per-worker 计数(比如真正本地化的限流),单独实现另一个 Limiter 不走这个单例。

---

## D-005 | 2026-04-21 | Spec-Driven 首次应用:SPEC-postgres-redis.md 作为模板

**决策**: Round 1 的 PostgreSQL + Redis PR 按 CTO handbook §18 先写 `docs/ai-cto/SPEC-postgres-redis.md`,作为未来大功能 PR 的**事实模板**:

- **What**:能做什么 / 不能做什么(scope boundaries 列 ❌ 边界)
- **Why**:引用 VISION / AUDIT / ROADMAP 的具体段落
- **How**:按数据库 / cache / infra / 依赖 / 测试 / 文档六个维度列落地
- **Risks**:风险矩阵 + mitigation
- **Acceptance criteria**:checklist 形式的完成定义

**Why**:
- 第一次用,走通了"写 SPEC → 写 PR 描述 → 写 commit 消息"的三段式,每层都能引用上一层,commit history 自带上下文
- 未来大功能(计费 / SNI 选型 / 健康度仪表盘)都需要这种尺度,现在有模板比临时发明好

**How to apply**:
- 下次 "非 trivial 新功能" PR 前,先在 `docs/ai-cto/SPEC-<kebab-name>.md` 起草,参考 postgres-redis 结构
- SPEC 提交为 PR 的第一个 commit,让后续代码 review 有背景
- SPEC 落地完成后可删(或改为 "ARCHIVED" 标记),路线图上的决策进入 `docs/ai-cto/DECISIONS.md`

**推翻条件**: 小 PR(<100 行 diff 或纯 bug 修复)不强制 SPEC;只有"新增模块/服务/架构决策"级别才走。

---

## D-004 | 2026-04-21 | Round 0 完成,Round 1 聚焦 P0 安全 + 基础测试设施

**决策**: Round 1 **不做新功能**,只做:
1. P0 安全修复(JWT secret 外置 + Admin 速率限制 + CORS 收紧 + JWT 时效收紧)
2. PostgreSQL 切换 + 迁移
3. 测试基础设施(pytest fixture + CI + 至少关键路由端点测试)
4. 目录骨架(`hardening/` + `deploy/` + `ops/` 创建 + README)

**Why**: AUDIT.md 显示安全 3/10、测试 1/10。在这两块没达标前做任何新功能都是在**不可审计的沙滩上盖楼**,每次上线都会带安全债务和回归风险。>200 用户商业场景容不得这种脆弱。

**How to apply**: Round 1 所有任务必须属于以上 4 类。新功能(SNI 选型器、计费等)推到 Round 2+。

**推翻条件**: 用户明确要求优先做 SNI 选型器或计费 demo(商业 deadline 驱动),可调整;但至少 JWT 外置和速率限制这两条必须先做。

---

## D-003 | 2026-04-21 | 商业化机场法律合规 —— 用户已知,CTO 留痕

**决策**: CTO 对用户明确提示了运营付费机场(>200 用户)在中国大陆/伊朗/俄罗斯的刑事风险,用户接受风险并继续。CTO 不再阻止,但在项目多处留下合规警示。

**Why**:
- 2023-2025 年有多起"运营翻墙收费"刑事判例
- CTO 的职责是提示和加固防御,不是代替用户做价值判断
- 留痕后若未来出问题,历史记录清晰

**How to apply**:
- `NOTICE.md` 和 `.agents/rules/security.md` "合规红线"段落已写入
- 建议(非强制):
  - 运营主体 / 支付通道 / 域名 / VPS 账单全部境外化且隔离
  - 中国大陆 IP 黑名单屏蔽
  - 管理面板访问走 CF Tunnel + Access
  - 管理员居住地非高风险司法管辖区
  - 不保留用户真实身份信息;支付走加密货币或境外 SaaS
- 任何涉及"收款"、"实名制"、"电话验证"的功能请求必须再次提醒用户合规风险

**推翻条件**: 用户明确说"只在合规法域运营 + 仅面向持牌用户",此限制可放宽。

---

## D-002 | 2026-04-21 | AGPL-3.0 合规策略 —— 保留版权 + 独立仓库 + 源码披露入口

**决策**: 采用 "hard fork + 独立仓库 + 致谢保留" 策略。

- ✅ `git clone` 上游后 `rm -rf .git && git init` 成为独立仓库,不显示 "forked from"
- ✅ **保留**原版 `LICENSE`(AGPL-3.0)和所有源文件版权头
- ✅ 新增 `NOTICE.md` 致谢 upstream 并标注 fork commit SHA
- ✅ 自研新模块(`hardening/`、`deploy/`、`ops/`)可选独立 license(Apache-2.0 / MIT,与 AGPL 兼容)
- ❌ **禁止**闭源商业化运营;必须对用户提供源码获取入口(面板 footer 或 `/source` 路由)

**Why**:
- 用户希望"不显示 upstream 来源"(不想让其他运营方看到 fork 关系)
- Hard fork + 独立 git init 能满足这个需求(不是 GitHub fork,也不显示 forked 标记)
- **但** AGPL-3.0 不允许隐藏 upstream 版权或不对用户披露源码,这两条必须坚守
- 违反 AGPL 会导致法律风险(强制开源 / 撤销使用权),这是项目生存问题

**How to apply**:
- 所有 commit 中,涉及 upstream 代码的修改必须保留原文件头 Copyright 行
- 上线前必须跑 `.agents/skills/agpl-compliance/SKILL.md` 定义的完整检查
- 面板必须在合理位置(footer、关于页、`/source` API)提供公开的 Git 仓库链接
- 自研模块若要用非 AGPL license,在该模块目录下独立声明 `LICENSE`

**推翻条件**: 只要 upstream license 仍是 AGPL-3.0,不可推翻。若未来 upstream 换 license,重新评估。

---

## D-001 | 2026-04-21 | Fork 基底:Marzneshin(不是 Marzban)

**决策**: 放弃已完成的 Marzban fork(commit `d3cf9fa`,已 `rm -rf .git` 销毁),改从 Marzneshin clone 重做。

**Why**:
- Marzban(Gozargah/Marzban)**最后活跃 2025-01-09**,15 个月无提交,官方团队已迁到 Marzneshin
- Marzneshin 是官方继任,**最近 release v0.7.4 @ 2025-10-02**,仍在活跃维护
- Marzneshin **原生多节点弹性**(control/data plane 分离 + gRPC 到 marznode),与 >200 用户 + 多节点目标完全对齐
- Marzneshin 前端是 **TypeScript + Vite + React + shadcn/ui**(比 Marzban 的 Vue2 现代);有 tests/ 骨架
- 代价:Marzban 生态的 V2IpLimit / luIP / miplimiter 等 IP 限制外挂**不兼容 Marzneshin**,我们需要改造或自研(详见 COMPETITORS.md 建议 3)

**How to apply**:
- 所有以后对"上游"的引用默认指 Marzneshin
- 不要 copy-paste Marzban 的 issue/PR 讨论作为 Marzneshin 的指导
- 季度性评估 `marzneshin/marzneshin` upstream 变更,策略性同步(不盲合)

**推翻条件**:
- Marzneshin 停更超过 12 个月 → 评估再 fork 或换基底
- 出现更优秀的活跃替代品(如 Remnawave 进入多节点阶段且生态起来)→ 重新评估

---

## 模板(新决策按此格式追加到顶部)

```
## D-NNN | YYYY-MM-DD | <一句话决策>

**决策**: <详细描述>

**Why**: <为什么这样选,而不是其他方案>

**How to apply**: <具体如何落地,哪些文件/流程受影响>

**推翻条件**: <什么情况下这条决策失效,要重新讨论>

---
```
