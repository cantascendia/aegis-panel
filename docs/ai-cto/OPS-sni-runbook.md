# OPS — SNI 选型器运维手册

> **范围**:`hardening/sni/` 选型器在生产环境的日常使用与故障排查。
>
> **读者**:运营 / 运维。开发侧 SPEC 见
> [SPEC-sni-selector.md](./SPEC-sni-selector.md);模块文档见
> [hardening/sni/README.md](../../hardening/sni/README.md)。
>
> **使用方式**:首次部署前通读 §1-§3;故障时按 §4 直接跳到对应症状。

---

## 1. 标准使用流程

新建一个 Reality 节点时:

```bash
# 1. 在 panel 同主机或能 SSH 到 panel 的机器,运行
python -m hardening.sni.selector --ip <vps-egress-ip> --count 10 --region auto

# 2. 选 score 最高且 notes 与你部署位置相符的候选,例如:
#    score=1.10 host=www.microsoft.com  notes=anycast-cdn (same DC)
#
# 3. 在 dashboard "新建节点" 表单或直接编辑 inbound JSON 把
#    realitySettings.serverName 设为该 host
#
# 4. 节点跑起来后跑 §6 的"上线后验证"
```

**`--region` 选什么**:

- `auto`(默认)= 只用 `seeds/global.yaml`。先无脑用这个,够用就停
- `jp/kr/us/eu` = 全球 + 区域种子合并。VPS 在该区域且 global 候选 RTT 高于 200ms 时切
- 自己加种子:编辑 `hardening/sni/seeds/<region>.yaml`,无需重启 panel,工具加载时读

---

## 2. 输出结构速读

```json
{
  "vps_ip": "1.2.3.4",
  "vps_asn": 14061,
  "vps_country": "US",
  "probed_at": "2026-04-26T...Z",
  "elapsed_seconds": 8.4,
  "candidates": [
    { "host": "...", "score": 1.10, "checks": {...}, "notes": "..." }
  ],
  "rejected": [
    { "host": "speedtest.net", "reason": "blacklist: ..." },
    { "host": "...", "reason": "TLS 1.3 handshake failed" }
  ]
}
```

**`candidates[]`**:按 `score` 降序。直接用第一个;如果第一个 RTT > 200ms
而下面有同 ASN 的候选,选下面的。

**`rejected[]`**:**每次都看一眼**。它告诉你为什么列表短了或空了 ——
比追额外候选更便宜的就是从这里读"系统已替你筛过的失败"。

**Score 解释**:

| 值 | 含义 |
|---|---|
| `1.0` | 六指标全过的基线 |
| `+0.1` | 同数据中心(子网级)bonus |
| `+0.1` | OCSP stapling 观测到 |
| `-0.2` | TLS RTT > 200ms(可能跨洋) |
| `0.0` | 任意硬指标失败 → 不会出现在 candidates,会出现在 rejected |

---

## 3. 退出码

| code | 含义 | 处置 |
|---|---|---|
| `0` | ≥1 候选通过 | 按上述流程选用 |
| `1` | 零候选通过(JSON 仍输出) | **看 §4** |
| `2` | VPS 的 ASN 查不到 | **看 §5** |

shell pipeline 可靠地 `if python -m hardening.sni.selector ...; then ...`。

---

## 4. 应急:零候选通过(exit 1)

### 4.A 检测命令

```bash
python -m hardening.sni.selector --ip <vps-ip> --count 10 --region auto > sni-out.json
echo "exit=$?"
jq '.candidates | length, .rejected | length' sni-out.json
jq '.rejected[] | .reason' sni-out.json | sort | uniq -c | sort -rn
```

### 4.B 判定条件

`exit=1` + `candidates 长度 = 0` + `rejected 长度 ≥ 1`(否则跳 §5)。

### 4.C 处置步骤(按 rejected reason 主因分类)

#### 主因 1:`TLS 1.3 handshake failed` 占大多数

→ **VPS 自身的 TLS 出口被屏**。可能性:

1. VPS 提供商出口防火墙阻断了 TLS 1.3 探测(罕见但有过 Hetzner / OVH 案例)
2. 测试机器(跑 selector 的机器)与目标的链路有 DPI(更常见)

**修**:换一台没有出口限制的机器跑 selector,然后把结果的 SNI 在
**目标 VPS** 上手验:

```bash
ssh root@<vps>
openssl s_client -connect www.microsoft.com:443 -tls1_3 -alpn h2 < /dev/null 2>&1 | head -20
```

如果 VPS 上能握成功 → 换运行 selector 的机器,重跑;问题在你跑工具
的位置,不在 VPS。

如果 VPS 上也握不成功 → **VPS 出口本身有问题**,联系 VPS 提供商或换段。

#### 主因 2:`HTTP 301/302 redirects to a different hostname` 占大多数

→ 种子表里的候选都跳走了。可能 CDN 改了行为。

**修**:

```bash
# 看是哪些种子在跳:
jq '.rejected[] | select(.reason | contains("redirect"))' sni-out.json

# 对每个跳走的 host 手验 301 目的地:
curl -sI https://<host>/ | grep -i location
```

如果同一目的地反复出现(如 `www.x.com → cn.x.com`),把那个目的地
**作为新种子**加到 `seeds/global.yaml` 或区域文件,然后重跑 selector。
旧的跳转源建议加注释而不是删,留个历史。

#### 主因 3:`resolves to an IP in a different ASN than the VPS` 占大多数

→ VPS 在冷门 ASN(典型:Hetzner / RackNerd / 小型 IDC),CDN 巨头都不
在同 ASN。

**修**:

```bash
# 查 VPS 实际 ASN
echo "begin
verbose
<vps-ip>
end" | nc whois.cymru.com 43
```

如果 VPS 在小 ASN,**降级使用 score 0.8 候选** —— 同 ASN 是 bonus 不
是必须。手工编辑 inbound JSON 用 `score 0.8+` 的最佳同协议候选即可。
注意:同 ASN 失败仅扣 -0.0,但其他 5 个指标过的话仍然 score=1.0。
真正的 score=0 是其他 5 个指标失败。

如果你想"宁可不用同 ASN bonus,但用更好的 SNI",直接挑 `--region` 与
你 VPS 物理区域**不一致**的种子(例如 VPS 在德国但你跑 `--region us`),
能拿到该区域的 CDN 候选。

#### 主因 4:`X25519 not in negotiated groups (or unknown)` 占大多数

→ 大概率是 selector 跑在 Python 3.12 + OpenSSL <3.2 上,导致 `tls.group()`
不可用。

**修**:`hardening/sni/checks.py` 在 3.12 上有 fallback("TLS 1.3 握手成功
就视为 X25519 OK"),理论上不应该出现这个 reason。如果出现,说明 fallback
失效了 —— 这是 bug,提到 `hardening/sni` 的 issue tracker。

**临时绕过**:跑在 Python 3.13 + OpenSSL 3.2 的环境(精确检测路径)。

### 4.D 验证命令

修完一项主因后重跑 selector,目标:`exit=0` + `candidates 长度 ≥ 3`。

---

## 5. 应急:VPS ASN 查不到(exit 2)

### 5.A 检测命令

```bash
echo "begin
verbose
<vps-ip>
end" | nc -w 5 whois.cymru.com 43
```

### 5.B 判定条件

返回 `NA | <ip> | NA | ZZ | NA | ...` 或 5 秒超时。

### 5.C 处置步骤

1. 5 分钟后重试一次 —— Cymru 偶发限流
2. 如果一直 NA:验证 IP 真的是 VPS 出口 IP(而不是网卡本地 IP):
   ```bash
   ssh root@<vps> "curl -s ifconfig.me"
   ```
3. 如果 IP 是公网且 ASN 仍 NA,VPS 出口在一段未分配 ASN 的 IP —— 很罕见。
   联系 VPS 提供商或迁移到正经段
4. 实在拿不到 ASN:跑 selector 时**不要传 --ip,改传 `--ip <类似 ASN 的邻居 IP>`** 应急,但此模式下 same-ASN 检查名存实亡。临时用,不要留作长期方案

### 5.D 验证命令

```bash
python -m hardening.sni.selector --ip <vps-ip> --count 5
echo "exit=$?"  # 应当是 0 或 1,不再是 2
```

---

## 6. 上线后验证(每个新节点必跑)

按选好的 `serverName` 重启节点后:

```bash
# 1. 节点上 xray 是否真的在监听 reality 端口
ssh root@<vps> "ss -tlnp | grep <reality-port>"

# 2. 从外网 TLS 1.3 + h2 探测节点本身
openssl s_client -connect <vps>:<reality-port> -tls1_3 -alpn h2 -servername <chosen-sni> < /dev/null 2>&1 | grep -E 'Protocol|ALPN|Cipher'
# 期望:Protocol = TLSv1.3 / ALPN protocol: h2

# 3. 客户端实际握手:用 v2rayN/sing-box 加节点连一下,跑 https://www.cloudflare.com/cdn-cgi/trace
#    返回正常 = 通了

# 4. 跑 24h 后回看 access log 没出现高频 reset/RST 才算稳
```

---

## 7. 周期性维护

| 频率 | 动作 |
|---|---|
| **每周** | 看一眼 `tail -50` panel 日志中 SNI 选型相关 warning,如 "blacklist entry skipped: ..." |
| **每月** | 跑一次 `selector --ip <每个节点>` 重新验证现网 SNI 仍 score≥1.0;有掉线则按 §4 处置 |
| **每季度** | 读 `compass_artifact_*.md` 看是否有新公开 DPI 黑名单情报,有则 PR 加到 `blacklist.yaml` |
| **每次 VPS 提供商出事(集体被封 / 价格变 / 跑路)** | 全网节点重跑 selector,可能区域种子表也要更新 |

---

## 8. blacklist / seeds 编辑 SOP

任何对 `hardening/sni/blacklist.yaml` 或 `hardening/sni/seeds/*.yaml` 的修改:

1. **单 PR 一次只改一个文件**,review 时候才好对照 source citation
2. **`source` 字段必填**,可以是 compass_artifact 段名 / 公开新闻 URL /
   GitHub issue 链接;不接受 "群里有人说"
3. **`added` 字段填 ISO 日期** —— 半年后整理时知道哪条该淘汰复审
4. 改完本地跑 `python -m hardening.sni.selector --ip <一个测试 VPS>` 确认
   loader 不报 `SeedLoadError`,再 push

---

## 9. 已知限制(给运营心理预期)

- **selector 一跑只是当下快照**,DPI 规则可能下午就变。这是 §7 的"周期性
  重新验证"的存在理由,不是 bug
- **score 不是绝对**。score=1.1 的候选不见得永远比 score=1.0 的好 ——
  CDN 的 datacenter bonus 会随 IP 漂移变化。如果两个候选都过 6 指标,
  人工挑选 + 跑 24h 观测最终用哪个
- **没有自动监控**。当前 selector 是 one-shot CLI;Reality 健康度仪表盘
  (`compass_artifact_*` 提到的 v0.3 自动监控)还没建,所以 §7 的运维
  动作目前是 **人** 跑,不是 cron

---

_2026-04-26 初版,随 SPEC-sni-selector.md follow-up #3 落地。_
_配套修改:`deploy/README.md` + `hardening/sni/README.md` 加链接指向本文件。_
