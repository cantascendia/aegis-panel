# OPS — Reality 配置审计运维手册

> **范围**:`hardening/reality/` 配置审计器在生产环境的日常使用、定期巡检
> 与故障处理。
>
> **读者**:运营 / 运维。开发侧 SPEC 见
> [SPEC-reality-audit.md](./SPEC-reality-audit.md);模块文档见
> [`hardening/reality/README.md`](../../hardening/reality/README.md);
> 关联通道运维见 [OPS-sni-runbook.md](./OPS-sni-runbook.md)(SNI 选型
> 与本审计互补:选型决定哪些 SNI 是好的,审计验证当前已部署配置)。
>
> **使用方式**:首次部署后跑一次 §3 全节点审计;每月跑 §6 巡检;新增节点
> 必跑 §5 验证;配置变更后必跑 §3。

---

## 1. 审计器做什么 / 不做什么

### 做

按 `compass_artifact_*.md` 五件套对每个 Reality 节点的 inbound 配置打分:

| 维度 | 检查 | 关键扣分 |
|---|---|---|
| SNI 冷门度 | 与 top1k 列表比对 | top-100 critical -30 / top-100~1000 warning -10 |
| ASN 同质 | SNI 实际 ASN vs VPS 出口 ASN | 不同 ASN critical -35 |
| 端口非标准 | 是否落在 2053/2083/2087/2096 推荐区间 | 443 critical -15 |
| shortId 合规 | 长度 / 字符集 / 去重 / 非全零 | 非法字符 / 全零 critical -25 |
| connIdle 短设 | ≤120s 推荐 / >300s 拒绝 | >300s critical -15 |

输出:每个 target 的分数(0-100)+ grade (green ≥70 / yellow 60-69 / red <60)
+ 摘要(JSON 或 Markdown)。

### 不做

- **不修改配置**。审计只读 panel DB 或 xray config 文件,不会改任何
  inbound。修复要 operator 在 dashboard 或 xray config 文件里手改
- **不验证 Reality 协议本身能不能跑**。客户端连不上 Reality 不在本审
  计范围内(那是 marznode + xray-core 的问题)。本审计只看**伪装质量**
- **不替代 SNI 选型**。审计找出"你的 SNI 不好"的事实;选**新** SNI 走
  [`OPS-sni-runbook.md`](./OPS-sni-runbook.md) 的流程

---

## 2. 三种使用方式

| 方式 | 何时用 | 命令 |
|---|---|---|
| **CLI from panel DB** | 部署后一次性扫所有节点 | `python -m hardening.reality.cli --from-db --vps-asn <ASN>` |
| **CLI from xray config** | 部署前 dry-run 一份候选 config | `python -m hardening.reality.cli --config <path-to-xray.json> --vps-asn <ASN>` |
| **REST `/api/reality/audit`** | dashboard "Reality 审计" 页(R.4 上线后)/ 自动化巡检 cron | sudo-admin token + POST 请求 |

CLI 与 REST 同源 —— 都走 `hardening.reality.checks.*` + `scoring.py` +
`report.py`。CLI 是给运维终端跑的;REST 是给 UI / 其他自动化系统调用的。

---

## 3. 标准全节点审计流程(部署后 / 大版本上线前必跑)

### 3.1 准备

获取本 panel 出口的 VPS ASN(给 `asn_match` check 用):

```bash
# 在 panel 主机上跑
curl -s ifconfig.me  # 拿到出口 IP
# 用 IP 查 ASN(Team Cymru 公开 WHOIS):
whois -h whois.cymru.com -- "-v $(curl -s ifconfig.me)" 2>&1 | tail -1
```

例如返回 `14061 | 137.184.0.0/16 | DIGITALOCEAN-ASN | US`,记下 14061。

### 3.2 跑审计

```bash
docker exec marzneshin-panel python -m hardening.reality.cli \
  --from-db \
  --vps-asn 14061 \
  --format markdown \
  --out /tmp/audit-$(date +%Y%m%d).md
```

文件落到 `/tmp/audit-YYYYMMDD.md`。同时 stdout 显示一个 summary:

```
Audit summary
=============
Total targets: 12
green:  8
yellow: 3
red:    1
worst score: 42

Detailed report: /tmp/audit-YYYYMMDD.md
Exit code: 1 (yellow or red findings)
```

### 3.3 退出码契约(给 cron / CI 用)

| Exit | 含义 | 推荐动作 |
|---|---|---|
| `0` | 全 green | 通过,可继续 |
| `1` | 至少一个 yellow,无 red | 提工单 1 周内修;不阻塞发布 |
| `2` | 至少一个 red | 阻塞发布 / 立刻处置 |

CI / cron 可直接 `if [[ $? -ge 2 ]]; then alert; fi` 触发告警。

### 3.4 解读 Markdown 报告

报告每个 target 块大致这样:

```markdown
## Target: jp1.example.com (sni=static.naver.net, port=2083)

**Score: 42 / 100  —  grade: red**

| check | result | severity | delta |
|---|---|---|---|
| sni_coldness | ❌ static.naver.net rank 87 (top-100) | critical | -30 |
| asn_match | ✅ AS23576 == AS23576 (NAVER) | info | 0 |
| port_canonical | ✅ 2083 (CF alternate HTTPS) | info | 0 |
| shortid_compliance | ⚠️ 2 shortIds, recommended ≥4 | warning | -5 |
| timeout_config | ❌ connIdle missing | critical | -15 |
```

**修复优先级**:critical > warning > info。本例两条 critical:

1. **sni_coldness critical**:`static.naver.net` 是 top-100 之内的"通用
   CDN/SaaS"之一,被 GFW 持续抽查的概率高。**修复**:走
   [OPS-sni-runbook.md](./OPS-sni-runbook.md) `--region` 选一个**冷门
   且同 ASN** 的替代,例如 NAVER 体系内的子域 `nstatic.naver.com` /
   `manage.naver.com`(rank 排几千往后,GFW 抽查概率 100x 低)
2. **timeout_config critical**:`connIdle` 没设。在 xray config 的
   `policy.levels.0.connIdle` 加 `90`(推荐区间 60-120s);或 inbound
   的 `streamSettings.sockopt.tcpKeepAliveIdle` 设同样的 90。**重启
   xray** 让配置生效

修复后再跑 §3.2,直到 exit 0。

---

## 4. 评分阈值是怎么来的(背景)

| 边界 | 来源 |
|---|---|
| top-100 / top-1000 二级阈值 | compass_artifact_*.md 第一件套"冷门 SNI 选择" + GFW 实操观察:GFW 主动抽查的 list 大约在 top-100 内,top-1000 是"被动配色" |
| ASN 不匹配 = critical | compass_artifact_*.md 第二件套"同 ASN" + Reality 协议 spec:Reality 的伪装基础就是"我们的 IP 看起来像那个 SNI 的 IP",不同 ASN 会被任何半专业的 traffic analyzer 一眼识破 |
| 推荐端口 2053/2083/2087/2096 | CF 的 "alternate HTTPS ports",真实流量在这几个端口很多,我们藏在里面;443 反而是 GFW 重点关注 |
| connIdle ≤120s | compass_artifact_*.md 第五件套"短 connIdle":减少同一 connection 复用窗口,降低多路复用模式被识别概率 |
| shortId 长度 4-8 | xray-core 推荐 + Reality SPEC RFC-style 描述 |

调整这些阈值需要:
- 修 `hardening/reality/checks/<check>.py` 中的常量
- 修 `seeds/standard_ports.json` 或 `seeds/top1k.json`
- 跑测试 `pytest tests/test_reality_*.py`
- 走 PR(评分阈值变化是政策决策,需要审 review)

---

## 5. 新增节点验证(强制流程)

新部署一个 Reality 节点后,**必须在节点投产前**跑一次审计:

```bash
# 单节点审计:用 dry-run 模式针对这个 inbound 的 xray config 文件
docker exec marzneshin-panel python -m hardening.reality.cli \
  --config /path/to/new-node-xray.json \
  --vps-asn <new-node-VPS-ASN> \
  --format markdown \
  --out /tmp/new-node-audit.md
```

**接受标准**:exit 0(green)。

**拒绝标准**(任一):
- exit 2(red)→ 必须修复
- exit 1 + critical findings → 必须修复
- exit 1 + warnings only → operator 评估,签字接受可上(写到工单备注)

不通过的节点:**不要上线**。给 Reality 客户的"伪装"只有在所有节点都
通过审计时才有意义,任何一个 red 节点拉低整个 fleet 的可信度
(攻击者只需要识破一个就开始关注其他)。

---

## 6. 月度巡检(必跑)

每月初跑一次全 fleet 审计,目的:

1. **抓配置漂移**:operator 临时改了某 inbound 的 connIdle / shortId
   忘了恢复;upstream Marzneshin 升级带新字段没 audit 适配
2. **抓 SNI 流行度漂移**:某 SNI 上个月 rank 800,这个月窜进 top-100
   (Naver / Yahoo 等业务有大新闻时会突然热)→ sni_coldness 从 warning
   变 critical
3. **抓 ASN 漂移**:VPS provider 偶尔会迁 IP 池到不同 ASN(本运营
   罕见,但 DigitalOcean / Linode 历史上有过)。VPS ASN 一变,所有
   节点的 asn_match 全挂

**SOP**:

```bash
# 每月 1 号 UTC 02:00 跑(配 cron)
0 2 1 * * docker exec marzneshin-panel python -m hardening.reality.cli \
  --from-db --vps-asn $REALITY_VPS_ASN \
  --format json --out /var/log/reality-audit-$(date +\%Y\%m).json \
  || (echo "reality audit non-zero exit"; alert-via-telegram)
```

历史报告归档 `/var/log/reality-audit-YYYYMM.json`,**保留 12 个月**(便
于"上个季度怎么样"的对比)。

`docs/ai-cto/AUDIT.md` 是高层"运营周看板"的位置,审计巡检结果可摘要
入档。

---

## 7. seeds 维护(季度 refresh)

`hardening/reality/seeds/top1k.json` 是审计的"热门 SNI 黑名单"。**真
实流行度会变**(去年的 top-100 今年可能滑出 top-500)。

**默认刷新节奏**:每季度一次(对齐 Marzneshin upstream sync 节奏)。

**SOP**:

```bash
# 1. 跑 refresh 脚本(stdlib only,无外部依赖)
python -m hardening.reality.seeds.update_top1k --output hardening/reality/seeds/top1k.json

# 2. diff 对比
git diff hardening/reality/seeds/top1k.json | head -50

# 3. 跑全套 reality 测试
pytest tests/test_reality_*.py

# 4. 跑当前 fleet 审计,看新 seed 后还有哪些 fleet 漂移到 critical / warning
docker exec marzneshin-panel python -m hardening.reality.cli --from-db --vps-asn $ASN

# 5. 提 PR
git checkout -b chore/reality-seeds-refresh-$(date +%Y%m)
git add hardening/reality/seeds/top1k.json
git commit -m "chore(reality): seeds quarterly refresh $(date +%Y-%m)"
```

PR review 关注:有没有"原本是 top-1000 现在被滑出"的 SNI(那些 SNI
在我们 fleet 里可能被 audit 标 warning,值得确认是真不热了还是 list
出错)。

---

## 8. 故障排查

### 8.1 `asn_match` 全部 warning

**症状**:audit 里所有 target 的 asn_match 都是 `warning -10` + evidence
"DNS resolution failed" 或 "WHOIS lookup failed"。

**排查**:

```bash
# panel 主机上
docker exec marzneshin-panel python -c '
import asyncio
from hardening.sni.asn import lookup_asn
print(asyncio.run(lookup_asn("8.8.8.8")))
'
```

- 返回 `ASNInfo(asn=15169, ...)` = OK,看 audit 时是哪个 SNI 有问题
- 抛 `ASNLookupError: timeout` = panel 主机不能连 Team Cymru WHOIS
  (默认 `whois.cymru.com:43`,纯 TCP)。检查防火墙 / 出口

**Mitigation**:

```bash
# 临时跳过 ASN check(让其他 4 条 check 还能跑)
# 不带 --vps-asn,asn_match 自动降级到 warning
python -m hardening.reality.cli --from-db --format markdown
```

退出码会变 1(因为 warning),但你可以肉眼看其他 4 条 check 的结论。

### 8.2 某 SNI 不在 top1k.json 但实际很热

**症状**:某 host(比如 `figma.com`)在 audit 里被标 sni_coldness=info,
但你听说它最近在中国大陆很火,GFW 关注度上升。

**排查**:

```bash
# 看 top1k.json 里有没有
grep -i "figma" hardening/reality/seeds/top1k.json
```

**Mitigation**:

把 host 加入 top1k.json,rank 给个估值(比如 250 触发 warning,80
触发 critical):

```bash
# 编辑加一行 + commit
# 走 §7 的部分 SOP(跑测试 + 当前 fleet audit + PR)
```

如果是 hour-level 紧急(GFW 当天发起拨片),临时把 panel DB 里那个
inbound 的 SNI 直接换掉(不等 audit 完整流程)+ 立刻走 OPS-sni-runbook
找替代。

### 8.3 audit 报告文件 0 字节 / 空 targets 列表

**症状**:exit 0 但 `Detailed report` 显示 `Total targets: 0`。

**根因**:`from_db_rows` 找不到符合条件的行(`reality_public_key` 列
为空 / NULL 的 inbound 全部被过滤)。

**排查**:

```sql
SELECT id, address, sni, port, security, reality_public_key IS NULL OR reality_public_key = '' AS no_key
FROM hosts;
```

如果所有 reality 节点的 `reality_public_key` 都为空 = 上游 Marzneshin
schema 兼容性问题(罕见,可能版本错开)。开 issue 走 upstream-sync
讨论。

### 8.4 REST endpoint 504 timeout

**症状**:dashboard "Reality 审计" 页(R.4 上线后)/ 直接 POST
`/api/reality/audit` 返回 504,日志写 "reality audit exceeded 60s budget"。

**根因**:WHOIS 慢卡了。Team Cymru 偶尔会挂或速率限制。

**Mitigation**:

```bash
# 重试,如果连续多次 504,跳过 ASN check:
curl -X POST .../api/reality/audit \
  -H 'Authorization: Bearer <sudo-token>' \
  -d '{"source": "db"}'  # 不带 vps_asn
```

不带 `vps_asn` 的请求,asn_match 自动降级 warning,**不会**触发 WHOIS
调用,响应秒级。

---

## 9. 周期性维护清单

| 频率 | 动作 | 命令 / SOP |
|---|---|---|
| **Per deploy / config change** | 跑 §3 全节点审计 | `cli --from-db --vps-asn ...` |
| **Per new node** | 跑 §5 dry-run 审计 | `cli --config ... --vps-asn ...` |
| **每月** | 跑全 fleet 审计 + 归档 | §6 cron |
| **每季度** | seeds refresh + 跑全套审计验证 | §7 SOP |
| **每半年** | 评分阈值复盘 | review §4 + 看历史 audit / 新威胁情报 |
| **upstream sync 后** | 全节点审计 + 看 schema drift | §3 + §8.3 排查 |

---

## 10. 已知限制

- **top1k.json 是 manually curated baseline (~120 entries)**,不是真
  Tranco 1k。差异化 #1(SNI 选型)同款限制 —— `update_top1k.py`
  季度刷新填这个洞,但目前是"已知 hot SNI 防御"而非"全网 1k 防御"
- **Reality "伪装质量"是相对概念**,审计能给的只是"已知规则下的分数",
  GFW 实际策略不公开。应理解为"高分降低被针对性识别概率",不是"100
  分 = GFW 永远看不见你"
- **ASN check 依赖 Team Cymru**,服务端可能限速;高频 audit (1 次 / 秒
  级别)会被 throttle。生产环境的 cron 跑月度 / 每周即可,不要 1 分钟
  级别
- **没有"零信任"模式**:审计自己 trust panel DB / xray config;如果
  这些被攻击者改过,审计会被骗。**审计是 ops 工具,不是入侵检测系统**

---

## 11. 关联文档

- [SPEC-reality-audit.md](./SPEC-reality-audit.md) — 设计契约 (R.1-R.4 PR sequencing)
- [`hardening/reality/README.md`](../../hardening/reality/README.md) — 模块代码索引
- [`compass_artifact_*.md`](../../) (五件套) — 审计指标的权威来源
- [OPS-sni-runbook.md](./OPS-sni-runbook.md) — SNI 选型(audit 找出问题后,选型负责修复)
- `hardening/reality/cli.py --help` — CLI 完整参数说明
