---
name: sni-selector
description: 为 Reality 协议智能选型 serverName(SNI) — 扫 VPS 同 ASN 邻居、验证 TLS 1.3/H2/X25519、规避 DPI 黑名单。商业化机场抗封核心护城河。
---

# SNI 智能选型器(Skill)

## 目的

Reality 的伪装成败几乎只取决于 `serverName` 这一行。这个 Skill 封装了一套完整的 SNI 候选评估流程,给定一台 VPS,产出可直接写入 Xray 配置的候选域名列表。

## 何时调用

- 部署新节点前
- 季度性 SNI 健康度巡检(某些域名会被 DPI 加入黑名单)
- 现有节点被封后的应急切换
- 用户报告连接异常,怀疑 SNI 进入黑名单

## 硬指标(必须满足)

任何入选的 serverName 必须:

1. ✅ 目标站支持 **TLS 1.3**
2. ✅ 目标站支持 **HTTP/2**
3. ✅ 目标站支持 **X25519** 曲线
4. ✅ 不是跳转域(不是 302/301 到其他域名)
5. ✅ 目标 IP 与 VPS **同 ASN 或同数据中心**(商业化机场强制)
6. ❌ 不在 DPI 黑名单(硬编码黑名单 + 动态黑名单)

## 流程

### Step 1 — 确定 VPS 所在 ASN
```bash
# 用 VPS 自己的出口 IP 查 ASN
curl -s "https://api.ipapi.is/?q=$(curl -s ifconfig.me)" | jq .asn
```

### Step 2 — 扫描同 ASN /24 邻居
```bash
# 用 RealiTLScanner 或 xray tls ping 批量扫
for ip in $(same_asn_ips.txt); do
  xray tls ping $ip 2>&1 | grep -E "TLS 1.3|HTTP/2|X25519"
done
```

### Step 3 — 对每个候选域名验证硬指标 1-4

用 openssl / curl 脚本:
```bash
# TLS 1.3 支持
openssl s_client -connect $domain:443 -tls1_3 < /dev/null 2>&1 | grep "TLSv1.3"

# HTTP/2 支持  
curl -sI --http2 https://$domain | grep -i "HTTP/2"

# X25519 曲线(读 ClientHello 响应)
openssl s_client -connect $domain:443 -groups X25519 < /dev/null 2>&1 | grep "X25519"

# 不是跳转域
curl -sI https://$domain | grep -E "^HTTP/" | head -1 | grep -v "30[12]"
```

### Step 4 — 过滤 DPI 黑名单

硬编码黑名单(绝不用):
- `speedtest.net`(Iran MCCI 重点 DPI)
- `www.google.com`(中国不可达)
- `dl.google.com`(历史被封)
- `gateway.icloud.com`(频繁纳入 DPI 规则)

动态黑名单:从 `hardening/sni/blacklist.json` 读取(由运营方根据实际被封事件维护)。

### Step 5 — 地区匹配加权

按 VPS 地区优先候选:
- 🇯🇵 日本: `www.tiktok.jp`, `www.amazon.co.jp`, `www.lovelive-anime.jp`
- 🇰🇷 韩国: `static.naver.net`, `www.kakao.com`
- 🇺🇸 美国: `swdist.apple.com`, `www.bing.com`, `addons.mozilla.org`
- 🌐 Anycast 通用: `www.microsoft.com`, `www.apple.com`, `itunes.apple.com`

### Step 6 — 输出

产出 JSON 文件 `hardening/sni/candidates.<node-id>.json`:

```json
{
  "generated_at": "2026-04-21T10:00:00Z",
  "node_id": "node-tokyo-01",
  "vps_asn": "AS12345",
  "candidates": [
    {
      "domain": "www.amazon.co.jp",
      "score": 95,
      "tls13": true,
      "h2": true,
      "x25519": true,
      "same_asn": true,
      "neighbor_ip": "54.230.x.x",
      "last_verified": "2026-04-21T10:00:00Z"
    }
  ]
}
```

## 参考实现位置

- `hardening/sni/selector.py` — 主入口 CLI:`python -m hardening.sni.selector --node <id>`
- `hardening/sni/blacklist.json` — 黑名单
- `hardening/sni/rules.py` — 6 条硬指标的独立函数(可独立测试)
- `tests/hardening/sni/test_selector.py` — 测试(用 mock requests / openssl)

## 禁止行为

- ❌ 把"这次验证结果"缓存超过 24 小时(DPI 黑名单变化快)
- ❌ 对失败的域名重试超过 2 次(避免被目标站识别为扫描)
- ❌ 选型时并发 > 20(避免触发目标站 WAF)
- ❌ 无证据(score < 70)也输出候选
