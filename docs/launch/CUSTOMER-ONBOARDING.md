# 客户 onboarding — 操作员每客户必跑

> 每来一个新客户，操作员（你）按本清单走完。约 10 分钟。
> 跑完 = 客户能正常用 + 你有完整记录。

---

## 1. 确认客户意向（5 分钟）

询问：
- [ ] 套餐选哪个？（trial / m1 / q1 / y1）
- [ ] 主要用什么？（YouTube / 工作 / 游戏 / 多）
- [ ] iPhone / Android / 电脑？
- [ ] 哪个国家网络？（中国 / 日本 / 其他）
- [ ] 试用还是直接付费？（试用 → 跳到 §3；付费 → §2 收钱）

---

## 2. 收款（仅付费用户，跳过试用）

### 2.1 USDT TRC20 路径

1. 给客户钱包地址：`TXXXXXXXXXXXXXXXXXXXXXXXXX`（操作员填）
2. 提示 `转账金额：4.20 USDT`（按当前 ¥30 ≈ 4.2 USDT 算，按周更新汇率）
3. 等客户回截图 / TX hash
4. 用 [tronscan.org](https://tronscan.org) 确认转账：
   - 地址正确
   - 金额匹配
   - 状态 confirmed（≥1 块，约 30 秒）

### 2.2 支付宝扫码（易支付通道）

1. 让客户访问支付链接（先开易支付商家号 — see `OPS-epay-vendor-guide.md`）
2. 等到账通知（webhook 自动触发）

### 2.3 收到钱后

发感谢话：
```
收到 ¥30。账号马上开通，1 分钟内发订阅链接给你。
```

---

## 3. 开账号（aegis-user CLI）

```bash
ssh root@VPS

# 套餐参数：trial / m1 / q1 / y1
aegis-user create <CUSTOMER_HANDLE> <PLAN>

# 示例：
aegis-user create alice m1
```

**输出**（保存好）：
```
================================================================
✅ Created: alice (¥30/月_100GB)
✅ xray synced (5s)
Sub URL : https://nilou.cc/sub/alice/abc123def456
Expires : 2026-06-01T05:30:00 UTC
================================================================
```

---

## 4. 发客户

复制下面话术到微信，**填空**后发：

```
账号开好了！🎉

订阅链接：
https://nilou.cc/sub/alice/abc123def456

到期日：6 月 1 日（30 天后）
流量：100 GB / 月
设备：3 台同时

—— 安装 ——

iPhone：App Store 搜「Streisand」
安卓：GitHub 下「v2rayNG」
电脑：Mac App Store 搜「V2Box」/ Windows 用「v2rayN」

App 里 ➕ → 添加订阅 → 粘贴上面 URL → 启动 → 选 Tokyo Reality 节点

—— 验证 ——

Safari 打开 https://ip.sb，显示日本 IP 就是成了。
看 YouTube 4K 不卡 = 完美。

—— 不会装 / 报错 / 连不上 ——

发我截图，我现场处理。

—— 付款（如果是 trial 跳过）——

USDT TRC20 收到。

享用 ☕
```

---

## 5. 记录到客户表（手动）

复制到 `docs/ai-cto/private/customers.md`（gitignored）：

```markdown
## alice — 2026-05-02 m1
- contact: WeChat: alicewx / TG: @alice_a
- payment: 4.2 USDT / TX: e4a8b2... (tronscan link)
- subscription: https://nilou.cc/sub/alice/abc123def456
- expires: 2026-06-01
- traffic_cap: 100 GB
- referral_source: friend_b 介绍
- notes: 主要用 YouTube + ChatGPT，iPhone
```

---

## 6. 跟进（24h 内主动问）

```
昨天开的账号用着怎么样？连得上吗？
速度满意吗？看视频清晰吗？
```

如果回复"挺好" → 收藏，留作未来介绍来源。
如果回复"卡 / 连不上" → 立即处理（OPS-marznode-debug-runbook.md）。

---

## 7. 到期前 3 天提醒

```
你账号到 X 月 X 日到期，今天先提醒下。

继续用？我把账号续 30 天就行。
- USDT 4.2 / 支付宝 ¥31.5
- 留个原订阅链接，不用换

不续也没关系，到期后自动断流，余下流量清空。
```

---

## 8. 紧急情况脚本（万一节点挂了）

```
不好意思，节点 X 现在维护，预计 30 分钟恢复。
影响约 N 个用户，已经在抢救。

补偿：今天免费延 1 天，不用客气。

恢复后我会通知你。

（如果是你坏了，别甩锅；是 Vultr/上游就告诉客户大致原因）
```

---

## 9. 下个月手动事项（重复每月）

- [ ] 25 号查一遍：所有客户到期日，提醒续费
- [ ] 5 号查 ip.sb 节点 IP 是否健康
- [ ] 跑 OPS-go-live-checklist.md 全部 7 项
- [ ] 升级 panel/marznode 是否有新版（参考 GitHub release）
- [ ] 检查 USDT 钱包余额，准备 cash out 给银行账户

---

## 关键人物联系（紧急）

- VPS 控制面：Vultr 控制台账号
- 域名：nilou.cc 在 X 服务商（操作员填）
- 客户支持：你（保持微信 24h 在线）
- 备份操作员：（最好有 1 个朋友懂技术能 SSH 救火）

---

## 下次该做什么（按客户数量）

| 现在 | 触发 → 下一步 |
|---|---|
| 1-3 客户 | 加入第 2 节点（HK or SG）— $18/月 |
| 5-10 客户 | 配 Telegram bot 自动通知到期 |
| 10+ 客户 | 雇 1 个助理 / 写自助 self-service portal（D-016 反向决策）|
| 30+ 客户 | 改 staging VPS workflow，升级前先试 |
| 50+ 客户 | C 阶段触发 — 自构镜像 / 多区 / SLA / 退款保障 |
