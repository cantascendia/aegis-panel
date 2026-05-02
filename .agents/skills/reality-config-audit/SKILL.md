---
name: reality-config-audit
description: 审计 Xray / Reality 配置正确性 — 硬指标合规、指纹一致性、policy.levels 合理性、无指纹性回落限速。CI / 部署前必跑。
---

# Reality 配置审计(Skill)

## 目的

把 `.agents/rules/xray-config.md` 中的规则落地成自动化检查,每次下发配置到 marznode 之前跑,违反任一硬指标直接阻断。

## 何时调用

- **下发前**:控制面(Marzneshin)把 xray_config.json push 到 marznode 前
- **CI 时**:PR 涉及 `app/marznode/**` 或 `hardening/reality/**` 变更
- **定时扫描**:每日一次扫所有活跃节点的配置,发现飘移

## 审计项(全部必过,违反即阻断)

### ① SNI 白名单检查
所有 user 的 `streamSettings.realitySettings.serverName` 必须在 `hardening/sni/whitelist.json` 中。whitelist 由 SNI 选型器周期性生成。

### ② 指纹一致性检查
同一订阅组下所有客户端的 `fingerprint` 必须一致(默认 `chrome`)。

禁用指纹(有 bug 或已被 DPI 识别):
- ❌ `chrome_pq`(sing-box issue #2084)
- ❌ `randomized`、`HelloChrome_106_Shuffle`

### ③ Vision 流控检查
- 裸 TCP 传输的 Reality 入站必须 `flow: xtls-rprx-vision`
- XHTTP / gRPC 传输可省略(但必须明确标注)

### ④ 回落限速检查
`fallbacks[].bytesPerSec` **必须不存在或为 0**。开启就是指纹。

### ⑤ policy.levels 检查
`policy.levels.0` 必须包含:
- `connIdle: 120`(或更小)
- `handshake: 2`(或更小)

### ⑥ shortId 区分性检查
不同用户的 `shortId` 不能重复(避免日志级无法区分)。

### ⑦ Secret 明文扫描
配置中不得出现:
- 硬编码的 Xray `privateKey`(应从 `.env` 或 marznode 本地文件读)
- JWT secret、DB 密码、CF token 字符串模式
- 用正则扫:`(?i)(private_?key|secret|password|token)["'\s:=]+[a-zA-Z0-9+/]{20,}`

### ⑧ 端口合理性
- 不建议 443(易被扫)
- 推荐 8443 / 2053(CF 友好)
- 多节点不应全部用同一端口(指纹关联)

### ⑨ UUID 唯一性
所有 user 的 UUID 必须在库中唯一(DB UNIQUE 约束保底,配置层再验)。

### ⑩ TLS cert 有效期
(节点级检查)本地 TLS cert 剩余有效期 > 30 天;否则告警。

## 实现建议

- `hardening/reality/audit.py` 主入口
- 每个检查项独立函数,返回 `(passed: bool, detail: str)`
- CLI:`python -m hardening.reality.audit --node <id>` 或 `--all`
- 退出码:0=全过,1=有 warning,2=有 critical 失败(CI 阻断)
- 输出 JSON 报告供 dashboard 展示

```python
# 示例结构
def audit_node(node_id: str) -> AuditReport:
    checks = [
        check_sni_whitelist,
        check_fingerprint_consistency,
        check_vision_flow,
        check_no_fallback_ratelimit,
        check_policy_levels,
        check_shortid_unique,
        check_no_plaintext_secret,
        check_port_reasonable,
        check_uuid_unique,
        check_tls_cert_validity,
    ]
    return AuditReport(results=[c(node_id) for c in checks])
```

## CI 集成

在 `.github/workflows/reality-audit.yml`(待建):

```yaml
- name: Reality config audit
  run: |
    python -m hardening.reality.audit --all --format json > audit.json
    if [ $? -ne 0 ]; then
      cat audit.json | jq .
      exit 1
    fi
```

## 禁止

- ❌ 绕过任何检查项(哪怕"只是这次例外"也不行,改规则再跑)
- ❌ 审计失败但仍下发配置(阻断必须是硬阻断,不是 warning)
- ❌ 在审计代码里 log 敏感字段明文(即便是排查)

## 相关

- Rules: `.agents/rules/xray-config.md`
- SKILL: `sni-selector`(提供 whitelist 输入)
- compass_artifact: 规则来源
