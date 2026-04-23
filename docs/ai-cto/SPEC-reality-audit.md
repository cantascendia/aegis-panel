# SPEC — Reality 配置审计器(S-R session,差异化 #3 MVP)

> **状态**:骨架,待 S-R session 首日 flesh out。
>
> 本 spec 是 S-R session 的交付契约。Spec-Driven 流程:S-R 先补完
> 骨架成一个完整 SPEC 并 PR 合入,然后才能写 `hardening/reality/**`
> 代码。
>
> 参考:CTO handbook §7、项目根 `compass_artifact_*.md` 五件套。

## Kickoff prompt(粘贴到新 Claude Code 会话)

```
/cto-resume

你是 Aegis Panel 项目 S-R session(Reality 配置审计器,差异化 #3
MVP)。

必读:
- docs/ai-cto/SESSIONS.md §S-R
- docs/ai-cto/SPEC-reality-audit.md(本骨架)
- compass_artifact_*.md 五件套(冷门 SNI / 同 ASN / 非标准端口 /
  CF Tunnel / Vision+短 connIdle) —— 审计指标的权威来源
- hardening/sni/ 现有代码作为模块结构参考

地盘独占:
- hardening/reality/**
- docs/ai-cto/SPEC-reality-audit.md
- tests/test_reality_*.py

共享冲突点:
- hardening/panel/middleware.py 加 1 行 include_router(SPEC 通过
  后再动)

禁动: app/**, ops/**, hardening/{sni,iplimit,panel}/**, dashboard/**

第一步: flesh out 本 SPEC 的所有 TBD 段落,开 docs-only PR。
SPEC 合后再写 code。
```

---

## What(目标)

扫描一份当前运行的 Reality 配置(从 xray config 或 panel DB 的
host 表读),按 `compass_artifact_*.md` 五件套检测:

1. **SNI 冷门度**:目标 SNI 是否在 top-1k domain list 里 / 被 GFW
   列入白名单的常见域(cloudflare/microsoft/apple 这种太热,容易
   被针对性抽查)
2. **ASN 同质性**:客户端可见的 remote ASN 与 SNI 实际 ASN 是否
   一致(Reality 要求这两者必须同 ASN,否则被动探测即暴露)
3. **端口非标准性**:443 大流量桌面节点 = 高风险;我们推荐 2053 /
   2083 / 2087 / 2096(CF 的 HTTPS alternate)
4. **shortId 合规**:长度 0-16 字符,字符集 `[0-9a-f]`,不能有
   重复或全零
5. **connIdle / connSetup 配置**:短 connIdle(推荐 120s 以内) +
   短 connSetup 降低复用探测窗口

输出:JSON 报告(可机读) + Markdown 摘要(可给运维看)。

## Why

AUDIT + VISION 都标了这条为 **差异化 #3**:
- 引自 VISION:"Reality 已经不够,**Reality 2026 加固层**是必做
  的防 GFW 升级"
- 引自 AUDIT:"目前 Reality 配置全靠手动,**出错即翻车**"

## 非目标

- ❌ 不自动 fix 配置(只报告,改还是运维决定)
- ❌ 不扫描 xray 以外的 inbound 协议(VMess/Trojan/WireGuard 另外一码事)
- ❌ 不做 live probe(不主动探测自己的节点 —— 那是 differentiation #3 v0.2)
- ❌ 不改 `app/routes/hosts.py`(upstream 同步区)

---

## How(大纲,待 S-R 细化)

### 目录结构(参考 `hardening/sni/` 形状)

```
hardening/reality/
├── __init__.py
├── README.md
├── db.py              # Models(如果要建审计历史表 —— TBD)
├── checks/            # 每条指标一个 pure function
│   ├── __init__.py
│   ├── sni_coldness.py
│   ├── asn_match.py
│   ├── port_canonical.py
│   ├── shortid_compliance.py
│   └── timeout_config.py
├── scoring.py         # 综合 0-100 分
├── seeds/
│   ├── top1k.json     # 常见 SNI 黑名单(大致前 1k)
│   └── standard_ports.json
├── report.py          # JSON + Markdown 生成
├── loader.py          # 从 xray config 或 DB 读 Reality 配置
├── cli.py             # CLI 入口(独立脚本或 argparse)
└── endpoint.py        # 可选:REST /api/reality/audit(SudoAdminDep)
```

### 接口

**CLI**:
```bash
python -m hardening.reality.cli --config /path/to/xray.json
# 或读 panel DB
python -m hardening.reality.cli --from-db
```
输出:`report.json` + `report.md`。

**REST**(第二 PR):
```
POST /api/reality/audit
  body: {config: {...}} 或 empty(读 DB)
  response: {score: 0-100, findings: [...], recommendations: [...]}
```
通过 `apply_panel_hardening()` 挂载,SudoAdminDep。

### 评分模型(TBD,S-R 定)

粗设想:
- 每个 check 返回 `{ok: bool, severity: "critical" | "warning" | "info", evidence: str}`
- 加权求和 → 0-100
- critical 直接扣 40,warning 扣 10

### Seeds 哪里来?

- `top1k.json`:Tranco top-1M 前 1k(可脚本生成)
- `standard_ports.json`:人工维护 `[443, 8443, 80, 8080, ...]`

---

## Acceptance criteria(S-R 补)

- [ ] 每条 check 至少 3 个单测(happy / bad / edge)
- [ ] 总体 golden report:给一份已知的"完美" Reality 配置 + 一份
  已知"糟糕"的,score 分别稳定在 90+ / 30-
- [ ] CLI 退出码契约:score >= 70 → 0,60-70 → 1(warning),< 60 → 2
- [ ] 零外网调用(ASN 查询用本地 MMDB 或缓存;sample size 足够就行)
- [ ] 五件套里的每条加固建议都至少有一个 check 覆盖

## Risks(S-R 补)

| 风险 | 对策 |
|---|---|
| top1k 列表过时 | TBD(季度更新?Tranco 数据源脚本?) |
| ASN 数据库体积 | TBD(用 hardening/sni/ 已用的 Team Cymru 查询?还是打包 MMDB?) |
| 误报率(保守审计让运维烦) | TBD |
| 新 xray 字段(比如 xver / padding mode)未覆盖 | TBD(定期 review 五件套有没有新条) |

---

## PR sequencing(S-R 落地)

1. **R.0**:本 spec 补全,docs-only PR(S-R 首日)
2. **R.1**:`hardening/reality/checks/*` + `scoring.py` + `seeds/*` + `report.py` + 单测(核心离线逻辑)
3. **R.2**:`cli.py` + `loader.py`(从 xray config 读)+ CLI 契约测试
4. **R.3**:`endpoint.py` + `middleware.py` 加一行 + 集成测
5. **R.4**:dashboard/ 加一个 "Reality 审计" 页(可能触发新建 S-F-2 session 或延后;本 spec 不覆盖前端)

每 PR ≤ 600 LOC。
