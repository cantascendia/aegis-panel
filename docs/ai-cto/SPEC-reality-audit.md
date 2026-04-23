# SPEC — Reality 配置审计器(S-R session,差异化 #3 MVP)

> **状态**:v1.0 flesh-out 完成(2026-04-23)。docs-only PR 合入后启动 R.1 代码 session。
>
> 本 spec 是 S-R session 的交付契约。Spec-Driven 流程:SPEC 合入 →
> `hardening/reality/**` 代码分批 PR(R.1–R.4,见文末 §PR sequencing)。
>
> 参考:CTO handbook §7、项目根 `compass_artifact_*.md` 五件套。

## Kickoff prompt(粘贴到新 Claude Code 会话)

```
/cto-resume

你是 Aegis Panel 项目 S-R session(Reality 配置审计器,差异化 #3
MVP)。

必读:
- docs/ai-cto/SESSIONS.md §S-R
- docs/ai-cto/SPEC-reality-audit.md(本 SPEC,已 flesh out)
- compass_artifact_*.md 五件套(冷门 SNI / 同 ASN / 非标准端口 /
  CF Tunnel / Vision+短 connIdle) —— 审计指标的权威来源
- hardening/sni/ 现有代码作为模块结构参考

地盘独占:
- hardening/reality/**
- docs/ai-cto/SPEC-reality-audit.md
- tests/test_reality_*.py

共享冲突点:
- hardening/panel/middleware.py 加 1 行 include_router(R.3 再动)

禁动: app/**, ops/**, hardening/{sni,iplimit,panel}/**, dashboard/**
```

---

## What(目标)

扫描当前运行的 Reality 配置(从 xray config JSON 或 panel DB 的
`InboundHost` 表读),按 `compass_artifact_*.md` 五件套检测:

1. **SNI 冷门度**:目标 SNI 是否在 top-1k domain list 里 / 被 GFW
   列入白名单的常见域(cloudflare/microsoft/apple 这种太热,容易
   被针对性抽查)
2. **ASN 同质性**:客户端可见的 remote ASN 与 SNI 实际 ASN 是否
   一致(Reality 要求这两者必须同 ASN,否则被动探测即暴露)
3. **端口非标准性**:443 大流量桌面节点 = 高风险;推荐 2053 /
   2083 / 2087 / 2096(CF 的 HTTPS alternate)
4. **shortId 合规**:长度 0-16 字符,字符集 `[0-9a-f]`,不能有
   重复或全零
5. **connIdle / connSetup 配置**:短 connIdle(推荐 ≤120s) +
   短 connSetup 降低复用探测窗口

输出:JSON 报告(可机读) + Markdown 摘要(可给运维看)。

---

## Input contract(读取层)

Loader 支持两条路径,输出统一 dataclass,checks 层与来源解耦:

```python
@dataclass
class RealityTarget:
    host: str                    # 节点域名/IP(展示用)
    sni: str                     # Reality serverName
    port: int
    public_key: str              # Reality 公钥(审计只核对存在性,不做密码学校验)
    short_ids: list[str]
    fingerprint: str             # utls client hello fp(chrome/firefox/...)
    conn_idle: int | None        # 秒;None = 未设置
    xver: int | None
    spider_x: str | None
    source: Literal["db", "config"]
```

**从 DB**(默认,canonical source):`app/db/models.py` 的 `InboundHost`
表字段映射:
- `sni`, `host`, `port`、`security`(必须 == `"reality"` 才纳入审计)
- `reality_public_key`、`reality_short_ids`(JSON column)
- `fingerprint`
- `conn_idle` / `xver` / `spider_x`:DB 暂无字段 → fallback 到 xray
  config 或填 None(loader 给 warning)

**从 xray config JSON**:解析 `inbounds[].streamSettings.realitySettings`
(`serverNames[0]` 取第一个、`shortIds[]`、`dest`、`xver`、`spiderX`);
connIdle 取 `sockopt.tcpKeepAliveIdle` 优先,fallback 到
`policy.levels.*.connIdle`。

Loader 不做校验(那是 checks 层的事),只做格式转换与缺字段标记。

---

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
- ❌ 不做密码学强度校验(Reality 密钥长度由 xray 生成器保证)

---

## How

### 目录结构(参考 `hardening/sni/` 形状)

```
hardening/reality/
├── __init__.py
├── README.md
├── models.py           # RealityTarget, Finding, Report dataclasses
├── checks/             # 每条指标一个 pure function
│   ├── __init__.py
│   ├── sni_coldness.py
│   ├── asn_match.py
│   ├── port_canonical.py
│   ├── shortid_compliance.py
│   └── timeout_config.py
├── scoring.py          # 综合 0-100 分,映射 grade
├── seeds/
│   ├── top1k.json                # Tranco 2026-Q1 快照
│   ├── standard_ports.json       # [443, 8443, 80, 8080, ...]
│   └── update_top1k.py           # 运维季度刷新脚本
├── report.py           # JSON + Markdown 渲染
├── loader.py           # 从 xray config 或 DB 读 Reality 配置
├── cli.py              # CLI 入口(`python -m hardening.reality.cli`)
└── endpoint.py         # R.3:REST /api/reality/audit(SudoAdminDep)
```

### CLI 契约

```bash
python -m hardening.reality.cli --from-db [--format json|md|both] [--out <dir>]
python -m hardening.reality.cli --config /path/to/xray.json [...]
```

- stdout:JSON 报告
- stderr:人类可读 markdown 摘要
- exit code:`0` (score ≥ 70 全绿)、`1` (60–69 黄)、`2` (<60 红)
- `--out <dir>`:写入 `report.json` + `report.md` 到指定目录

### REST 接口(R.3 PR)

```
POST /api/reality/audit
  body: {source: "db"} | {source: "config", config: {...}}
  response: Report JSON(见下方 schema)
```

通过 `apply_panel_hardening()` 挂载,`SudoAdminDep` 保护。

### 评分模型

每条 check 返回:

```python
@dataclass
class Finding:
    check: str                              # "sni_coldness"
    ok: bool
    severity: Literal["critical", "warning", "info"]
    score_delta: int                        # 负数(或 0)
    evidence: str                           # 给人看的一句话
    remediation: str                        # 建议修正
    data: dict                              # 机读补充(asn 号、shortId 列表等)
```

**扣分表**(起始 100 分,下限 0;按 target 独立计分):

| Check | Critical | Warning | Info |
|---|---|---|---|
| `sni_coldness` | -30 (SNI 在 top-100) | -10 (top-100 ~ top-1000) | 0 (未命中) |
| `asn_match` | -35 (SNI 与 VPS 跨 ASN) | -10 (同国不同 ASN) | 0 (同 ASN) |
| `port_canonical` | -15 (443 + 桌面节点标记) | -5 (8443/80) | 0 (2053/2083/2087/2096) |
| `shortid_compliance` | -25 (非法字符 / 重复 / 全零) | -5 (长度<4 或 shortId 条数>8) | 0 |
| `timeout_config` | -15 (connIdle>300s 或缺失) | -5 (180s ~ 300s) | 0 (≤120s) |

**Grade 映射**:≥70 green / 60–69 yellow / <60 red。
**CLI exit code** 与 grade 对齐(见 CLI 契约)。

### Output schema(v1.0)

```json
{
  "schema_version": "1.0",
  "audited_at": "2026-04-23T12:00:00Z",
  "source": "db",
  "targets": [
    {
      "host": "jp1.example.com",
      "sni": "www.lovelive-anime.jp",
      "port": 2083,
      "score": 92,
      "grade": "green",
      "findings": [
        {
          "check": "sni_coldness",
          "ok": true,
          "severity": "info",
          "score_delta": 0,
          "evidence": "SNI not in Tranco top-1k",
          "remediation": "",
          "data": {"rank": null}
        }
      ]
    }
  ],
  "summary": {
    "total": 5,
    "green": 4,
    "yellow": 1,
    "red": 0,
    "worst_score": 62
  }
}
```

**可 diff 性**:两次运行配置无变更 → JSON 字节级相等(`audited_at`
字段由调用方决定,测试中可注入固定时间)。

### Markdown 报告结构

```
# Reality Audit Report
_Generated: {audited_at} | Source: {source}_

## Summary
| Total | Green | Yellow | Red | Worst |
|---|---|---|---|---|
| 5 | 4 | 1 | 0 | 62 |

## Per-target
### jp1.example.com (score: 92 🟢)
- ✅ sni_coldness — SNI not in Tranco top-1k
- ⚠️ port_canonical — port 443 on desktop node (-15)
  - Remediation: switch to 2053/2083/2087/2096

## Compass 五件套 checklist
- [x] 冷门 SNI
- [x] 同 ASN
- [ ] 非标端口
- [x] shortId 合规
- [x] 短 connIdle
```

### Seeds

- **`top1k.json`**:Tranco top-1M 前 1k 快照,数据戳 2026-Q1;
  `update_top1k.py` 给运维季度手动刷新(SPEC 锁定 "季度 review" 到
  OPS runbook)
- **`standard_ports.json`**:人工维护 `{"recommended": [2053, 2083,
  2087, 2096], "warning": [8443, 80], "critical": [443]}`

---

## Acceptance criteria

- [ ] 五条 check 各 ≥ 3 单测:happy (ok=True)、bad (critical 扣分触发)、
  edge(shortId 长度 0 / 16 等边界值)
- [ ] Golden fixtures:`tests/fixtures/reality_perfect.json` (预期
  score ≥ 90) + `reality_broken.json` (预期 score ≤ 30) 两份入仓,
  CLI 契约测试跑过
- [ ] CLI 退出码契约:≥70 → 0、60–69 → 1、<60 → 2;`--format` 支持
  `json` / `md` / `both`;`--out <dir>` 写双文件
- [ ] 零外网调用:pytest 套件 CI 里启 `pytest-socket --disable-socket`;
  ASN 查询走 monkeypatched resolver(复用 SNI 模块的 fake resolver)
- [ ] 五件套全覆盖:§Traceability 表每行对应至少一个 check
- [ ] 可 diff 性:同配置两次运行 JSON(去掉 `audited_at`)字节级相等
- [ ] SPEC 1.0 schema 稳定:schema_version 不因 R.1–R.3 变动,新增
  check 通过 additive 不破坏现有字段

---

## Risks

| 风险 | 对策 |
|---|---|
| top1k 列表过时 | 打包 Tranco 2026-Q1 快照;附 `seeds/update_top1k.py` 脚本供运维季度手动刷新;OPS runbook 里记录 "季度 review" |
| ASN 数据库体积 | 复用 `hardening/sni/asn.py` 的 Team Cymru DNS 查询策略(已验证,零打包),共用 LRU cache;不打包 MMDB 避免 70MB+ 仓库膨胀 |
| 误报率(运维烦) | (1) Info 级默认不扣分,只提示;(2) 支持 `~/.aegis/audit_ignore.yaml` 白名单按 check+host 静音;(3) R.1 只开 critical 扣分,warning 按运维反馈在 R.2 后再放 |
| 新 xray 字段未覆盖 | SPEC 锁定 v1.0 schema;每季度 review compass_artifact 五件套;新 check 走 additive PR,schema_version 升到 1.x(minor) |
| DB fixture 成本 | 测试 mock `InboundHost` 对象,不跑 alembic;checks 单测纯 dataclass 输入,loader 单测用内存 list |
| 跨平台 CLI(Windows vs Linux) | stdout 使用 UTF-8 强制(`sys.stdout.reconfigure(encoding="utf-8")`),markdown 表情回退到纯文本(环境变量 `AEGIS_NO_EMOJI=1`) |

---

## Traceability — compass_artifact 五件套覆盖

| 建议 | 对应 check | 模块路径 |
|---|---|---|
| 冷门 SNI(避开 google/cloudflare,用 jp/kr 本地热门) | `sni_coldness` | `hardening/reality/checks/sni_coldness.py` |
| 同 ASN 匹配(SNI IP 与 VPS 同 ASN) | `asn_match` | `hardening/reality/checks/asn_match.py` |
| 非标端口(2053/2083/2087/2096) | `port_canonical` | `hardening/reality/checks/port_canonical.py` |
| shortId 合规(0–16 hex,去重,非全零,≤8 条) | `shortid_compliance` | `hardening/reality/checks/shortid_compliance.py` |
| 短 connIdle(≤120s)+ handshake 2 | `timeout_config` | `hardening/reality/checks/timeout_config.py` |
| CF Tunnel 边缘加固 | (非本 MVP,记 R.0.5 backlog) | — |
| Vision flow / spiderX 模式 | (非本 MVP,记 R.0.5 backlog) | — |

---

## PR sequencing

1. **R.0**:本 SPEC flesh-out,docs-only PR(S-R 首日) — **本 PR**
2. **R.1**:`checks/*` + `scoring.py` + `models.py` + `seeds/*` +
   `report.py` + 单测(核心离线逻辑)— ≤ 400 LOC
3. **R.2**:`cli.py` + `loader.py`(DB + xray JSON 两路径)+ CLI
   契约测试 + golden fixtures — ≤ 200 LOC
4. **R.3**:`endpoint.py` + `hardening/panel/middleware.py` 加 1 行
   `include_router` + 集成测 — ≤ 150 LOC
5. **R.4**:dashboard/ 加 "Reality 审计" 页 —— 延后到 S-F-2 session,
   本 SPEC 不覆盖前端

每 PR ≤ 600 LOC 上限作为兜底。
