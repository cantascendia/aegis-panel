# OPS — TRC20 USDT 直收支付通道运维手册

> **范围**:`ops/billing/trc20_*` 在生产环境的部署、运营、故障排查。
>
> **读者**:运营 / 运维。开发侧 SPEC 见
> [SPEC-billing-mvp.md](./SPEC-billing-mvp.md) §A.3;关联 EPay 通道
> 运维见 [OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md);USDT
> 套现流程见 [OPS-jpy-cashout.md](./OPS-jpy-cashout.md)。
>
> **使用方式**:首次部署前通读 §1-§4;月度核对走 §7;故障时按 §6
> 跳到对应症状。

---

## 1. 通道概览

TRC20 是 EPay 之外的**第二条独立支付通道**。两条通道并存,失败可
互相 failover:

| 维度 | EPay(易支付码商) | TRC20(USDT 直收) |
|---|---|---|
| 通信模型 | 推(码商 webhook → 我们) | 拉(我们轮询 Tronscan) |
| 中介 | 一家或多家码商 | 无 —— 直链上 |
| 手续费 | 1-3%(码商抽成) | 仅链上 gas(用户付) |
| 结算延迟 | 秒级(webhook 到达即 paid) | 30s 级(poll interval) |
| 资金归集 | 码商代收 → 周期打款 | 直接进 operator 冷钱包 |
| 跑路风险 | 中(码商可能冻结) | 低(链上不可逆) |
| 合规风险 | 低(走支付宝/微信渠道) | 高(USDT/CN 监管模糊) |

运营建议:**EPay 主力 + TRC20 备胎**(给愿意自己用钱包的高净值用户)
。两条都开,在用户结账页通过 PaymentChannel.priority 控制默认顺序。

---

## 2. 前置条件

部署 TRC20 通道前必须先准备:

### 2.1 冷钱包

- 用 **Ledger / Trezor / 离线机** 生成 TRC20 地址(以 `T` 开头,34
  字符)。**禁止**用交易所地址(交易所 deposit 地址会变 / 没有 memo
  支持 / 客服难联系)
- 私钥 **永远不进 panel 服务器**,也不进 `.env`、不进任何 git 仓库
- 把公钥地址记录在 `.env` 的 `BILLING_TRC20_RECEIVE_ADDRESS`(本字段
  100% 公开安全,链上任何人都能看到)
- 钱包准备少量 TRX(**约 100 TRX 起步**)给"激活地址"和未来发起
  套现交易付 gas

### 2.2 Tronscan API 访问

默认走 `https://apilist.tronscanapi.com`(公共,无 API key)。**不
需要任何注册**。验证:

```bash
curl 'https://apilist.tronscanapi.com/api/token_trc20/transfers?contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&toAddress=TXXXX-your-test-address-here&limit=1'
```

返回 JSON `{"data": [...], ...}` = 通。返回 4xx/5xx = 见 §6.1。

如果你的 panel 服务器从中国大陆出口被 Tronscan 拒绝(罕见),fallback
到 Trongrid 公共节点,改 `BILLING_TRC20_TRONSCAN_API_BASE` 指向自建
indexer 或代理。

### 2.3 Memo Salt

`BILLING_TRC20_MEMO_SALT` 是必填,随机 32 字符以上。**绝不**和别的
operator 的 panel 共享同一 salt(会让 memo 碰撞)。生成:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

复制结果到 `.env`。**这条一旦设置,中途不要改**(改后老 invoice 的
memo 重新计算会跟链上 tx 不匹配,等于让所有 awaiting_payment 失效)。
紧急轮换流程见 §7.2。

### 2.4 兑换率快照

`BILLING_TRC20_RATE_FEN_PER_USDT` 是 operator 锁定的兑换率,单位 fen
per 1 USDT。每周复盘一次:

```bash
# 看 USDT/CNY 当前市场价(参考 OKX C2C 中位)
curl -s 'https://www.okx.com/v3/c2c/tradingOrders/books?quoteCurrency=CNY&baseCurrency=USDT&side=sell&paymentMethod=all&userType=all' \
  | python -c 'import sys,json; d=json.load(sys.stdin); print("中位:", d["data"]["sell"][2]["price"])'
```

设定原则:**比市价低 1-2%**(给运营留缓冲不至于亏)。例如市价 7.30
CNY/USDT,你设 `BILLING_TRC20_RATE_FEN_PER_USDT=720`(7.20 CNY/USDT)
。用户感知不到 1-2%,operator 不容易亏。

**绝不自动 fetch ticker** —— 多一个外部 API 依赖,且市场波动期会出现
"用户点 checkout 时 7.20,实际付款时 7.30"的歧义匹配问题。决策见
[D-015](./DECISIONS.md#d-015)。

---

## 3. 标准部署流程

### 3.1 编辑 `.env`

```bash
# 主开关
BILLING_TRC20_ENABLED=true

# 必填三件套
BILLING_TRC20_RECEIVE_ADDRESS=TXXXX...your-cold-wallet-address...
BILLING_TRC20_RATE_FEN_PER_USDT=720
BILLING_TRC20_MEMO_SALT=<随机 32+ 字符,见 §2.3>

# 默认即可,有需要再改
BILLING_TRC20_TRONSCAN_API_BASE=https://apilist.tronscanapi.com
BILLING_TRC20_MIN_CONFIRMATIONS=1
BILLING_TRC20_POLL_INTERVAL=30
BILLING_TRC20_PAYMENT_WINDOW_MINUTES=30
BILLING_TRC20_USDT_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
```

### 3.2 重启 panel

```bash
docker compose restart marzneshin
# 或裸跑
systemctl restart marzneshin
```

### 3.3 启动验证

启动日志中应看到:

```
billing scheduler started reap_interval=60s apply_interval=30s trc20_poll_interval=30s
```

**没看到 `trc20_poll_interval`** = scheduler 没装好,见 §6.2。

### 3.4 健康检查(无真实付款的快速测)

```bash
# 在 panel 容器内
python -c '
from ops.billing.providers import get_provider
p = get_provider("trc20")
print("address:", p.receive_address)
print("rate:", p.rate_fen_per_usdt)
'
```

返回你 `.env` 配的值 = OK。抛 `Trc20Misconfigured` = 配置缺漏,看
异常消息(它会列出缺哪个 env 变量)。

---

## 4. 端到端验证(testnet 强烈推荐)

**禁止**直接在主网用真实金额验证。先在 Tron testnet (Nile / Shasta)
跑一遍。

### 4.1 切换 testnet

```bash
# .env 临时改
BILLING_TRC20_TRONSCAN_API_BASE=https://nileapi.tronscan.org
BILLING_TRC20_USDT_CONTRACT=TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf  # Nile 测试 USDT 合约
BILLING_TRC20_RECEIVE_ADDRESS=TXXXX-Nile-testnet-cold-wallet
BILLING_TRC20_MIN_CONFIRMATIONS=1
```

注意 Nile 的 USDT 合约地址和主网不同。从
[Nile faucet](https://nileex.io/join/getJoinPage) 拿测试 TRX 和 USDT。

### 4.2 跑流程

1. 在 dashboard 创建一个测试用户,买一个最便宜的 plan(¥0.01)
2. 结账时选 TRC20,记下显示的 address + memo + amount
3. 用 TronLink / TokenPocket 等钱包向该 address 发送 amount USDT,**记
   得在 memo 字段填入 invoice 的 memo**(8 字符字母数字)
4. 等 30-60 秒
5. dashboard 应能看到 invoice 状态从 `awaiting_payment` → `paid` →
   `applied`,用户的 `expire_date` 被延长

### 4.3 验证审计 trail

```bash
# 在 panel 容器内
python -c '
from app.db import GetDB
from ops.billing.db import PaymentEvent
from ops.billing.db import Invoice

with GetDB() as db:
    inv = db.query(Invoice).order_by(Invoice.id.desc()).first()
    print(f"invoice {inv.id}: state={inv.state}, paid_at={inv.paid_at}, applied_at={inv.applied_at}")
    print(f"  trc20_memo={inv.trc20_memo}, expected_millis={inv.trc20_expected_amount_millis}")
    for ev in db.query(PaymentEvent).filter(PaymentEvent.invoice_id == inv.id).order_by(PaymentEvent.id.asc()).all():
        print(f"  event[{ev.id}] {ev.event_type}: {ev.payload_json}")
'
```

应能看到:
- `created` event(从 admin 或 user checkout)
- `state_paid` event,payload 含 `tx_hash` + `amount_millis` + `matched_via=memo`
- `state_applied` event,payload 含 `grant_gb_delta` + `grant_days_delta` 等

### 4.4 切回主网

测过后改回主网 env,**重新生成 MEMO_SALT**(测网期间产生的 memo 不
应在主网复用)。

---

## 5. 监控与告警

### 5.1 关键日志(grep 这些字段)

| 日志 | 含义 | 告警级别 |
|---|---|---|
| `trc20 poller marked N invoice(s) paid` | 正常工作 | INFO,周对账时统计 |
| `trc20 poller: tronscan fetch failed` | API 单次失败 | WARN,持续 > 10 分钟告警 |
| `trc20 poller: invoice X skipped (state race)` | 罕见,不影响功能 | INFO |
| `trc20 poller: invoice X failed to mark paid` | 严重,可能数据库故障 | CRITICAL,立即介入 |
| `trc20 poller: invoice X missing trc20_memo` | provider/DB drift | CRITICAL,数据腐败 |

### 5.2 业务指标

每月对账时,从 PaymentEvent 表统计:

```sql
-- TRC20 invoice 总览(本月)
SELECT
  COUNT(*) FILTER (WHERE state = 'applied') AS applied_count,
  COUNT(*) FILTER (WHERE state = 'expired') AS expired_count,
  COUNT(*) FILTER (WHERE state = 'awaiting_payment') AS still_open_count,
  SUM(total_cny_fen) FILTER (WHERE state = 'applied') / 100 AS revenue_cny
FROM aegis_billing_invoices
WHERE provider = 'trc20'
  AND created_at >= date_trunc('month', now() - interval '1 month')
  AND created_at < date_trunc('month', now());

-- 链上 USDT 实际入账(对账用,核对 cold wallet 余额变化)
SELECT
  SUM((payload_json ->> 'amount_millis')::bigint) / 1000.0 AS total_usdt
FROM aegis_billing_payment_events
WHERE event_type = 'state_paid'
  AND created_at >= date_trunc('month', now() - interval '1 month')
  AND created_at < date_trunc('month', now())
  AND payload_json ? 'tx_hash';
```

把 SQL 算出的 `total_usdt` 和 cold wallet **链上余额变化**对比,差值
应 = 0(误差应只来自 cents-dither,< 1000 millis × invoice 数)。

### 5.3 用户体验指标

`expired_count / (applied + expired)` = 用户**放弃支付率**。> 50% =
通道 UX 不好(memo 难复制 / amount 难记 / 钱包不支持 memo),考虑
A.4 dashboard 优化或调整 PAYMENT_WINDOW_MINUTES。

---

## 6. 故障排查

### 6.1 Tronscan API 不通 / 返回 4xx-5xx

**症状**:日志反复打 `trc20 poller: tronscan fetch failed`。

**排查**:

```bash
# panel 主机内
curl -v https://apilist.tronscanapi.com/api/token_trc20/transfers?limit=1 2>&1 | head -20
```

- 返回 200 = panel 应用 bug,看 panel 日志
- 返回 4xx + body 含 "rate limit" = 罕见(我们 30s 一次远远低于 100/s),
  确认没人手动并发刷 API
- 返回 5xx = Tronscan 自己挂,等 + 切 fallback
- 网络层完全不通 = 中国大陆出口被墙,切 Trongrid 或自建 indexer

**Mitigation**(15 分钟内不能恢复时):

```bash
# 切到备用 base
echo 'BILLING_TRC20_TRONSCAN_API_BASE=https://api.trongrid.io' >> .env
docker compose restart marzneshin
```

注意 Trongrid 的响应 schema 不完全相同 —— `_parse_one` 会因字段缺失
退出哪些 entries 的 warning 日志。如果完全 parse 失败,临时停用
TRC20:

```bash
sed -i 's/BILLING_TRC20_ENABLED=true/BILLING_TRC20_ENABLED=false/' .env
docker compose restart marzneshin
```

dashboard 用户结账时不再看到 TRC20 选项,但已开 invoice 仍会在窗口期
内被处理(只是 poll 不会跑)—— 等 30 分钟自动 expire,A.5 reaper 收尾。

### 6.2 Scheduler 没启动(没看到 trc20_poll_interval 日志)

**排查**:

```bash
docker compose logs marzneshin | grep -i 'billing scheduler'
docker compose logs marzneshin | grep -i 'apply_panel_hardening'
```

- 没 `billing scheduler started` = `apply_panel_hardening` 没跑 =
  upstream lifespan 改了,见 [L-016](./LESSONS.md#l-016)
- 看到 `started reap_interval=...` 但没 `trc20_poll_interval` = 你的
  `ops/billing/scheduler.py` 是 A.5 之前的旧版,跑 `git pull` 再重启

### 6.3 用户付了但 invoice 没变 paid

**排查 SOP**(从最常见到最罕见):

1. **Invoice 在窗口期内?** 默认 30 分钟。检查 `expires_at`:
   ```sql
   SELECT id, state, created_at, expires_at, trc20_memo, trc20_expected_amount_millis
   FROM aegis_billing_invoices WHERE id = <id>;
   ```
   若 `expires_at < now` = invoice 已 expired,A.5 reaper 会自动改
   state。用户应该看到"超时"提示;refund 走 §8

2. **用户付的金额对不对?** 查 invoice 的 `trc20_expected_amount_millis`,
   对比 Tronscan 上对应 tx 的金额(USDT 6 decimals → 我们存 millis = 3
   decimals,所以对比时用户付 1.223 USDT 对应 1223 millis)
   - 不匹配:用户必须重发(链上没法补)。原 invoice 失效,创建新 invoice
   - 匹配但状态未变:见步骤 3

3. **memo 对不对?** 大部分手机钱包**不支持 memo**(TokenPocket 默认
   带,imToken 选填,Trust Wallet 不带),退化到 amount-only 匹配。
   检查:
   ```sql
   SELECT payload_json FROM aegis_billing_payment_events
   WHERE invoice_id = <id> AND event_type = 'state_paid';
   ```
   如果根本没 `state_paid` event = poller 没匹配上。手动核 Tronscan

4. **手动核 Tronscan**:
   ```bash
   curl -s "https://apilist.tronscanapi.com/api/token_trc20/transfers?contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&toAddress=$BILLING_TRC20_RECEIVE_ADDRESS&limit=20" \
     | python -m json.tool | grep -A 2 'transaction_id'
   ```
   找用户的 tx。如果 tx 存在但 amount 不等于 invoice 的 expected_millis
   = 用户付错了金额(常见原因:钱包默认 fee 模式吃掉了 cents-dither
   的几位 millis,或用户手填金额漏了小数位)

5. **手动 paid**(谨慎):确认 tx 真存在 + 金额 ≥ expected 后,以
   sudo-admin 身份从 dashboard "Manual Apply" 操作。所有手动操作
   都会写 `admin_manual` event,审计可追溯

### 6.4 用户重复付款

**症状**:用户 paid 两次,只想要一份服务。

**根因**:用户钱包重发了一次 tx(网络确认慢按了第二次),或不同钱包
同时发。

**处理**:

- 我们的 invoice 状态变 `paid` 后,A.5 applier 30s 内变 `applied`,
  state-machine guard 防止"再付再 grant"。第二笔 tx 的金额成为
  operator 净收入
- **不要主动给用户 refund** 第二笔。因为:
  1. 链上没 chargeback,refund 必须 operator 主动发 USDT
  2. 接下来用户会问你要更多 refund(谁给钱谁就是冤大头),从此循环
- **正确动作**:把第二笔的金额折算成等值 plan,告知用户已多续期。
  Audit log 记录 `admin_manual` 事件 + note 说明操作

### 6.5 Rate 大幅波动

**症状**:USDT/CNY 当周从 7.20 涨到 7.50,operator 担心吃亏。

**Mitigation**:

```bash
# 改 .env
sed -i 's/BILLING_TRC20_RATE_FEN_PER_USDT=720/BILLING_TRC20_RATE_FEN_PER_USDT=740/' .env
docker compose restart marzneshin
```

注意:
- **改 rate 不会影响已经 awaiting_payment 的 invoice**(已锁定到那些
  invoice 的 expected_millis)
- 新 invoice 立刻按新 rate 出账
- 用户已经截图的"价格表"会过时,A.4 UI 应该实时按 rate 显示而不是
  缓存

短期内 rate 涨幅 > 5%,考虑两条路:
1. **主动调价**(本节做的):平稳的运营选择
2. **暂停 TRC20** 等市场回归(`BILLING_TRC20_ENABLED=false`),只走
   EPay。激进保守

---

## 7. 周期维护

### 7.1 月度对账

按 §5.2 SQL 跑一遍,把"DB 计算的 USDT 总和"和"cold wallet 余额变化"
对比。**必须每月对一次**,差异 > 0.5% 立刻深查(可能是 §6.4 的重付
或 cents-dither 累计误差,但累积大于此值就不正常)。

### 7.2 Memo Salt 轮换

**默认不需要**。仅在以下情况触发:
- 怀疑 salt 泄漏(`.env` 误推到 public repo / 运维离职带走)
- 旧 salt 由前任设置且无文档,想清理
- 半年以上未轮换且无技术债

**轮换 SOP**(必须停服 5 分钟):

```bash
# 1. 停服(让所有 awaiting_payment invoice 自然 expire)
docker compose stop marzneshin

# 2. 等 31 分钟(默认 PAYMENT_WINDOW_MINUTES=30,加 1 分钟容错)
sleep 1860

# 3. 启动 panel 让 reaper 把过期的 invoice 全部清理
docker compose start marzneshin
sleep 90

# 4. 再次停服
docker compose stop marzneshin

# 5. 改 salt
sed -i "s/^BILLING_TRC20_MEMO_SALT=.*/BILLING_TRC20_MEMO_SALT=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')/" .env

# 6. 启动
docker compose start marzneshin
```

启动后新 invoice 用新 salt;旧 invoice(都是 expired 状态了,因为
reaper 跑过)的 memo 失效不影响业务。

### 7.3 USDT 套现

冷钱包余额到达阈值(运营定,常见 5000 USDT)时,operator **手工**走
[OPS-jpy-cashout.md](./OPS-jpy-cashout.md) 流程把 USDT 换成法币入账。
panel 这边什么都不用做。

### 7.4 备用 indexer 演练

每季度演练一次:

```bash
# 临时切到 fallback,确保 panel 还跑
sed -i 's|BILLING_TRC20_TRONSCAN_API_BASE=.*|BILLING_TRC20_TRONSCAN_API_BASE=https://api.trongrid.io|' .env
docker compose restart marzneshin
# 跑 §4 的 testnet round-trip 一遍
# 跑通后切回 Tronscan
```

---

## 8. 紧急 SOP

### 8.1 用户主张"我付了你没收到"

1. 让用户提供 **TRC20 tx hash**(钱包 app 内的 tx 详情可截图)
2. 在 Tronscan 上查 tx,核对 `to_address` 是否 = 我们的 `BILLING_TRC20_RECEIVE_ADDRESS`,`amount` 是否匹配 invoice
3. 不匹配:解释清楚后让用户向**正确**地址重发(再三确认我们的地址给
   用户)。**不要**主动 refund(链上不可逆,refund 必须我们主动发,
   一旦给了第二个用户也会要)
4. 匹配但 invoice 没 paid:进入 §6.3 排查 SOP

### 8.2 链 reorg / tx 被 revert

**极罕见**(Tron 主网 reorg 历史上 0 次)。如果某天 cold wallet 余额
和 panel 计算的入账对不上 + Tronscan 上某 tx 显示 `confirmed: false` 退回 mempool:

1. 把对应的 invoice 从 `paid` / `applied` 拉回 `awaiting_payment`(SQL 改 state + 删 `state_paid` 之后的 PaymentEvent —— **审计 trail 必须保留**,**不删**,改用 `admin_reorg_revert` event 标记)
2. 通知用户重发
3. 如果用户已被授予流量 + 用了一部分,把已用部分作为 operator 损失记账;
   不要追用户(链上 reorg 不是用户的错)

### 8.3 Cold wallet 私钥丢失

**绝望情况**。私钥丢 = 余额永远归 operator-之前-的-自己 拿不到,新
入账的 USDT 也都进同一地址。

**Mitigation**:

1. 立刻在 `.env` 改成新冷钱包地址 + 新 salt + 重启
2. 老地址里的 USDT 永远归零(链上数学规则)
3. 对账时把这部分作为 operator 损失记入

**预防**:每次创建冷钱包都做 **2-of-3 多签** 或物理上的 mnemonic
backup(2 份,不同地点)。

---

## 9. 已知限制

- **Tronscan 历史回溯有限**:他们公开 API 默认只返回最近 1 万笔 tx。
  如果用户隔天才来抱怨,而中间已经 1 万笔 tx 流过,你可能查不到。
  按 §6.3 步骤 5 跑流程时多一句"用户付款时间到现在 < 24h 才能保证
  查到"的提示
- **没有 Webhook 替代**:Tron 协议本身不提供。我们 30s poll =
  延迟下限。要做 < 5s 的实时,需要切自建 indexer + websocket,工作量
  大,目前不做(决策见 [L-024](./LESSONS.md#l-024))
- **国内大陆出口受限**:中国 panel 服务器直连 Tronscan 可能时通时不通。
  生产环境建议海外 VPS,或常备 §6.1 的 fallback 配置
- **Cents-dither 累计误差**:每个 invoice 用户多付 < 1¢,长期累计是
  operator 净收益,但月对账时数字不会"完美归零"。差异在百元规模属
  正常,千元就要查了(可能 §6.4 重付)

---

## 10. 关联文档

- [SPEC-billing-mvp.md](./SPEC-billing-mvp.md) §A.3 — 设计契约
- [DECISIONS.md#d-015](./DECISIONS.md) — 匹配策略 / cents-dither / rate 锁定
- [LESSONS.md#l-024](./LESSONS.md) — 拉模型 vs. 推模型设计哲学
- [OPS-epay-vendor-guide.md](./OPS-epay-vendor-guide.md) — 第一支付通道运维(对比阅读)
- [OPS-jpy-cashout.md](./OPS-jpy-cashout.md) — USDT 套现入账流程
- `ops/billing/trc20_*.py` 5 个模块的 docstring(代码侧权威)
