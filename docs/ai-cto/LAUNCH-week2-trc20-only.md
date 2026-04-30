# LAUNCH Week 2 — TRC20-only 周末上线 Checklist

> 配套 [`ROADMAP-launch-B-to-C.md`](./ROADMAP-launch-B-to-C.md) Week 2 段。**0 中介、0 保证金、0 跑路风险** 路径,周末两天可上线收 USDT。
>
> **不重复** [`OPS-trc20-runbook.md`](./OPS-trc20-runbook.md)(那是日常运维手册);本文件是 **首次上线** 操作清单,跑完一次归档不再用。
>
> 创建:2026-04-30 | 状态:LIVE | 适用阶段:**B 第一波**

---

## 决策前提(已锁定,不再讨论)

- ✅ 已用 ROADMAP-launch-B-to-C 选定 B 路径(10-200 用户)
- ✅ Week 1 基建完成(VPS / 域名 / CF Tunnel / panel 跑通)
- ✅ 选 USDT-only 起步(放弃接码商,等 B 中后期再补)
- ✅ 你 PR #79 TRC20 直收已就绪

**没完成 Week 1 → 先回去做 Week 1,本文件假设 panel 已能用**。

---

## 时间预算

```
Sat AM (~3h)  钱包准备 + panel 配置 + testnet 验证
Sat PM (~2h)  主网切换 + 自付 5 USDT round-trip
Sun AM (~2h)  第一个客户(你自己 / 媳妇 / 最熟朋友)
Sun PM (~3h)  写客户教程 + 配 Telegram 告警 + backup
─────────────
~10h 周末搞定第一个真付费客户
```

---

## Phase 1: 钱包准备(Sat 9:00-10:30)

### 1.1 选钱包(只用经过审核的)

| 钱包 | 适合 | 推荐度 |
|---|---|---|
| **TronLink**(Chrome 插件 + App)| 站长日常,**首选** | ⭐⭐⭐⭐⭐ |
| Trust Wallet(App)| 移动端备用 | ⭐⭐⭐⭐ |
| Tronscan 自带钱包 | 避免,UI 差 | ⭐⭐ |
| 交易所地址(币安/OKX) | **绝对不用** — 交易所地址会变 | ⛔ |

**选 TronLink**:Chrome 商店搜 `TronLink`,**只下载官方版本**(开发者:TronLink Team)。

### 1.2 创建运营钱包

```
1. TronLink 装好后 → 创建新钱包
2. 12 字助记词:
   ✅ 写在纸上 + 锁抽屉
   ✅ 拍照存离线 USB
   ❌ 不发微信 / iCloud / Google Drive
   ❌ 不存密码管理器(防漏)
3. 设钱包密码(强密码,不和 panel 一样)
4. 复制地址(T 开头 34 位字符)→ 这是你的"收款地址"
```

### 1.3 验证地址可用

去 [Tronscan.org](https://tronscan.org) 搜你的地址 — 应该看到 **0 TRX, 0 USDT, 创建时间为今天**。

---

## Phase 2: Panel 配置(Sat 10:30-12:00)

### 2.1 准备 6 个 env 值

```bash
# 在你 VPS 上 cd 到 panel 目录,vim .env

# === TRC20 必备 ===
BILLING_TRC20_ENABLED=true

# 你的 TronLink 地址
BILLING_TRC20_RECEIVE_ADDRESS="T<你的地址>"

# Memo salt (随机 32 字符,保密)
# 生成: python -c "import secrets; print(secrets.token_hex(16))"
BILLING_TRC20_MEMO_SALT="<生成的 32 字符>"

# 汇率快照 (每周自己更新,锁定运营方决策面)
# 看 binance / huobi USDT/CNY 价,取偏低值
# 例:USDT = ¥7.20 → fen_per_usdt = 720
BILLING_TRC20_RATE_FEN_PER_USDT=720

# Tronscan API base(主网)
BILLING_TRC20_TRONSCAN_API_BASE="https://api.tronscan.org"

# 最少确认数(主网 Tron 3s/块,1 已经够)
BILLING_TRC20_MIN_CONFIRMATIONS=1

# Poll 间隔(s)
BILLING_TRC20_POLL_INTERVAL=30
```

### 2.2 重启 panel + 验证 scheduler 上线

```bash
# 1. systemd:
sudo systemctl restart marzneshin
sudo systemctl status marzneshin

# 2. 看启动日志,应有这一行:
sudo journalctl -u marzneshin -n 200 | grep "trc20_poll_interval"
# 期望: "billing scheduler started reap_interval=Xs apply_interval=Xs trc20_poll_interval=30s"

# 3. 30s 后看是否真的在 poll(没 invoice 时只是空转,无 ERROR 即正常):
sudo journalctl -u marzneshin -f | grep -i trc20
```

**任一步失败 → 看 `OPS-trc20-runbook.md` §6 故障排查,修完再继续**。

### 2.3 创建第一个 Plan(¥30 月费)

```bash
TOKEN="<你 sudo admin 的 JWT>"

curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     https://panel.yourdomain.com/api/billing/admin/plans \
     -d '{
       "operator_code": "PRO_MONTH",
       "display_name_en": "Pro Monthly",
       "display_name_i18n": {"zh-cn": "专业版月度"},
       "kind": "fixed",
       "price_cny_fen": 3000,
       "duration_days": 30,
       "data_limit_gb": 100,
       "enabled": true
     }'

# 验证 plan 已创建
curl -H "Authorization: Bearer $TOKEN" \
     https://panel.yourdomain.com/api/billing/admin/plans | jq '.[] | {code: .operator_code, price: .price_cny_fen}'
```

---

## Phase 3: Testnet 验证(Sat 13:00-15:00)

**⚠️ 必跑测试网**,真主网踩坑 = 真亏钱。

### 3.1 切 testnet 配置

```bash
# .env 临时改:
BILLING_TRC20_TRONSCAN_API_BASE="https://api.shasta.tronscan.org"
BILLING_TRC20_RECEIVE_ADDRESS="<你 TronLink 切到 Shasta 测试网的地址>"

# 重启 panel
sudo systemctl restart marzneshin
```

### 3.2 拿测试 USDT

去 [Shasta 水龙头](https://www.trongrid.io/shasta)(Discord / Telegram)申请测试 USDT:
- 填你的 Shasta 地址
- 等 1-5 min 收到 100-1000 USDT

### 3.3 创建测试 invoice

```bash
# 用你自己的 user_id
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     https://panel.yourdomain.com/api/billing/cart/checkout \
     -d '{
       "user_id": <YOUR_USER_ID>,
       "lines": [{"plan_code": "PRO_MONTH", "quantity": 1}],
       "channel_code": "trc20"
     }'

# 响应里复制:
# - receive_address (你的钱包地址)
# - expected_amount_usdt (像 4.166...,带 cents-dither)
# - memo (8 字符 hex)
```

### 3.4 真转账(测试网)

打开 TronLink:
1. 切到 **Shasta 测试网**
2. 转 **精确金额** 到 **receive_address**
3. **Memo / Note** 字段填 invoice 响应里的 memo
4. 点确认 → 30 秒内完成

### 3.5 验证 panel 收到

```bash
INVOICE_ID=<上一步返回的 id>

# 30-60s 内变 "paid",再 30s 内变 "applied"
watch -n 5 "curl -s -H 'Authorization: Bearer $TOKEN' \
     https://panel.yourdomain.com/api/billing/admin/invoices/$INVOICE_ID | jq .state"

# 看 audit events
curl -s -H "Authorization: Bearer $TOKEN" \
     https://panel.yourdomain.com/api/billing/admin/invoices/$INVOICE_ID | jq .events

# 应有: trc20_match_found / paid / applied 三段事件链
```

**全绿 → 测试网通过,继续 Phase 4**。

**任何问题 → `OPS-trc20-runbook.md` §6.3 失败排查表**。

---

## Phase 4: 主网切换(Sat 15:30-17:00)

### 4.1 切回主网

```bash
# .env 改回主网
BILLING_TRC20_TRONSCAN_API_BASE="https://api.tronscan.org"
BILLING_TRC20_RECEIVE_ADDRESS="T<你主网地址>"

sudo systemctl restart marzneshin
sudo journalctl -u marzneshin | grep -i "trc20" | tail -5
```

### 4.2 自付 5 USDT round-trip

**用真钱跑一次,5 USDT ≈ ¥36** = 你买你自己一个月会员,不是损失。

```bash
# 创建主网 invoice
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     https://panel.yourdomain.com/api/billing/cart/checkout \
     -d '{
       "user_id": <YOUR_USER_ID>,
       "lines": [{"plan_code": "PRO_MONTH", "quantity": 1}],
       "channel_code": "trc20"
     }'
```

### 4.3 准备 USDT(选一个)

| 来源 | 时间 | 提示 |
|---|---|---|
| **币安** App → 提币 → TRC20 → 你的地址 | 2-5 min | 手续费 1 USDT |
| **OKX** App → 提币 → TRC20 → 你的地址 | 2-5 min | 手续费 1 USDT |
| **场外个人** | 5-30 min | 风险 = 你认识的人 |

**首次必须从交易所提**:链上转账可追溯,符合监管 trail。

### 4.4 真转账 + 验证

跟 Phase 3.4-3.5 相同流程,**只是用真钱**:
- 转 5 USDT 到 receive_address(精确金额)
- Memo 字段填 invoice 的 memo
- 30s 内 invoice 变 paid → 60s 内变 applied
- **截图整个流程存档**(以后客户问问题你能直接发)

### 4.5 验证 user 真拿到 grant

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://panel.yourdomain.com/api/users/<YOUR_USER_ID> | \
     jq '{username, data_limit, expire_date, expire_strategy, used_traffic}'

# 应该看到:
# - data_limit: +100 GB(100*1024*1024*1024)
# - expire_date: 比今天 +30 天
```

**全绿 = 主网 round-trip 成功,你 panel 上线 ✅**。

---

## Phase 5: 第一个客户(Sun 9:00-11:00)

### 5.1 客户人选(优先顺序)

```
🥇 第 1 候选: 你自己(已经在 Phase 4 完成)
🥈 第 2 候选: 你媳妇 / 男友 / 室友(物理上能直接帮你)
🥉 第 3 候选: 你最铁的朋友(他不会因为 bug 跟你翻脸)

⛔ 不要找:
- 远房亲戚(出问题甩锅给你压力大)
- 同事(职场关系 + 钱事 = 灾难)
- 不会用电脑的长辈(教学成本 > 收益)
```

### 5.2 沟通脚本(直接 copy 改名字)

```
[微信发给候选人]

「
我做了个机场,主要给自己和朋友用。需要找几个内测朋友帮我跑通流程。
- 月费 30 元(等价 5 USDT)
- 用 USDT 付,你不会就教你
- 用一个月,有 bug 直接告诉我,免费给你下个月
- 你不喜欢直接退款

要不要试?
」
```

**关键纪律**:
- ❌ 不打折 / 不赠送 — 真付费才是真信号(B 阶段铁律)
- ✅ "不喜欢退款" 让他敢答应,但 80% 概率不会真退
- ✅ 主动说 "免费下个月" 比降价 30% 更有诚意

### 5.3 教学环节(USDT 不会用怎么办)

90% 朋友不会用 USDT,你要带他做一遍:

```
1. 让他下载 OKX(国内能下)
2. 微信付他 ¥36 给你转账(他充进 OKX 不要手续费)
3. OKX 内部 ¥36 → USDT(等价 5 USDT)
4. OKX 提币 → TRC20 → 你给他的 receive_address
5. 转账 memo 填 invoice 的 memo

整个流程: 微信付钱给他 → 他充交易所 → 提币给你
```

**重点**:你**先**微信付他 ¥36 → 他付 5 USDT 给你 panel → 你免去他"用 USDT 太麻烦"的心理负担。第一次成功后,他就会自己学。

### 5.4 验证 + 截图

跟 Phase 4.5 一样验证 user 拿到 grant。**完成的瞬间截图发朋友圈**(打码)— 这是你 launch 时刻,值得纪念。

---

## Phase 6: Sun 下午稳定化(Sun 13:00-17:00)

### 6.1 写客户使用指南(2 小时)

新建 `docs/customer-guide.md`(或者直接微信文档),5 段:

```
1. 你买的什么:30 天 / 100 GB / 多协议
2. 怎么付款:OKX 提 USDT TRC20 → 我给你的地址 → memo 填...
3. 怎么用:订阅链接(panel 给的)→ Clash / V2rayN 导入
4. 出问题:加我微信,优先看是不是 (a) 节点宕机 (b) 你账号到期 (c) 配置错
5. 续费:自动到期前 7 天提醒,自己再下一次单
```

**长度控制 < 1500 字**。客户超长不读。

### 6.2 配 Telegram 告警(2 小时)

panel 已有 health endpoint,接 TG bot:

```bash
# .env 加:
TELEGRAM_API_TOKEN="<你的 bot token>"
TELEGRAM_ADMIN_ID="<你的 TG user id>"

# 用现有 hardening/health endpoint + cron 每 5 分钟检查
crontab -e
# 加: */5 * * * * curl -fs https://panel.yourdomain.com/api/aegis/health > /dev/null || \
#     curl "https://api.telegram.org/bot${TG_TOKEN}/sendMessage?chat_id=${TG_ID}&text=panel%20DOWN"
```

### 6.3 数据备份脚本(30 min)

```bash
# /usr/local/bin/aegis-backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d)
DEST="/var/backups/aegis"
mkdir -p $DEST
sudo -u postgres pg_dump aegis | gzip > $DEST/aegis-$DATE.sql.gz

# 上传到阿里云 OSS / Backblaze B2 / 你信任的对象存储
# rclone copy $DEST/aegis-$DATE.sql.gz remote:aegis-backups/

# 删 30 天前的本地备份
find $DEST -name "*.sql.gz" -mtime +30 -delete

# crontab:
# 0 3 * * * /usr/local/bin/aegis-backup.sh
```

**`aegis_billing_*` 表 = 真钱数据,丢一次毁所有信任**。

### 6.4 周末打卡(15 min)

打开 `ROADMAP-launch-B-to-C.md` 里程碑日历,把 **2026-05-10 第一个真付费客户** 打 ✅。

---

## 周末退出标准

| 项 | 验证方式 |
|---|---|
| ✅ panel 在公网域名跑通 | `curl https://panel.yourdomain.com/api/aegis/health` 返回 200 |
| ✅ TRC20 主网 round-trip 一次 | invoice state = applied + user 真拿到 grant |
| ✅ 1 个真付费客户 | aegis_billing_invoices 表有 ≥ 1 行 state=applied 不是你自己 |
| ✅ 客户使用指南 | 客户能 0 客服自己用起来 |
| ✅ TG 宕机告警 | systemctl stop marzneshin → 5 min 内 TG 收到通知 |
| ✅ 数据库每日备份 | `ls /var/backups/aegis/` 有今天的 .sql.gz |

**6 项全绿 = 周末上线成功**。

下周一开始重复 Phase 5 流程找下一个客户(目标 Week 4 末 ≥ 5 客户)。

---

## 失败回滚预案

### 客户付了款但 invoice 永远 awaiting_payment

```bash
# 1. 看链上转账是否真的到了(Tronscan 搜地址)
# 2. 看 panel 日志是否 poll 到了:
sudo journalctl -u marzneshin -n 500 | grep -i "trc20\|tronscan"

# 3. 如果链上有但 panel 没看到 → 大概率 memo 错或金额不精确
# 4. 手动 apply(超出本周末范围,看 OPS-trc20-runbook §6.3)
# 5. 紧急退款:你 TronLink 转回客户的钱包 + 微信解释
```

**第一周客户出问题 = 学习样本,不是危机**。截图保留 + 道歉 + 给下个月免费。

### 你 panel 挂了

```bash
# 1. ssh 到 VPS
sudo systemctl status marzneshin
sudo journalctl -u marzneshin -n 100

# 2. 重启
sudo systemctl restart marzneshin

# 3. 还不行:
sudo systemctl stop marzneshin
sudo -u postgres pg_dump aegis > /tmp/emergency-dump.sql
# 然后给 客户群发 "维护中,1h 内恢复",别撑面子

# 4. 真起不来:从 backup 恢复
gunzip < /var/backups/aegis/aegis-<昨天>.sql.gz | sudo -u postgres psql aegis
```

**透明 > 完美**。客户原谅 1h 维护,不原谅"装作没事"。

---

## 第 2 周往后(Week 3+ Roadmap)

回 [`ROADMAP-launch-B-to-C.md`](./ROADMAP-launch-B-to-C.md) Week 3-5 段。

简版预告:

| Week 3 | 重复 Phase 5,目标 5 客户 |
| Week 4 | 第二台 VPS + Ansible 多节点(差异化 #4)|
| Week 5 | 评估接易支付码商 ROI(覆盖国内非技术用户)|

---

## 参考

- 工程实现:`ops/billing/trc20_*.py`(PR #79)
- 协议决策:`DECISIONS.md` D-015(memo > exact-amount)
- 日常运维:[`OPS-trc20-runbook.md`](./OPS-trc20-runbook.md)
- 上线全景:[`ROADMAP-launch-B-to-C.md`](./ROADMAP-launch-B-to-C.md)
- 易支付调研:本会话搜索结果(NodeSeek 共识 + epusdt 对比)
