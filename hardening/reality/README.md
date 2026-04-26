# hardening/reality/ — Reality 配置审计器

**状态**: 🟡 R.1 已合(本 PR,**核心离线逻辑**);R.2 (CLI + loader)、R.3 (REST endpoint)、R.4 (dashboard 页) 待续

**目标**:扫描运行中的 Reality 配置,按 `compass_artifact_*.md` 五件套打分(0-100),输出 JSON + Markdown 报告。

> **完整 SPEC**:[`docs/ai-cto/SPEC-reality-audit.md`](../../docs/ai-cto/SPEC-reality-audit.md)
>
> **运维手册**:R.2 CLI 落地后由 OPS-runbook 跟进。

---

## 五条硬指标 / 扣分表

每条 check 起始 100 分,findings 累计扣分(下限 0):

| Check | Critical | Warning | Info |
|---|---|---|---|
| `sni_coldness` | -30(SNI ∈ top-100) | -10(top-100 ~ top-1000) | 0(未命中) |
| `asn_match` | -35(SNI ASN ≠ VPS ASN) | -10(DNS / WHOIS 失败,无法判定) | 0(同 ASN) |
| `port_canonical` | -15(443) | -5(80 / 8443) | 0(2053 / 2083 / 2087 / 2096) |
| `shortid_compliance` | -25(非法字符 / 重复 / 全零) | -5(长度<4 或 >8 条) | 0 |
| `timeout_config` | -15(connIdle 缺失或 >300s) | -5(180-300s) | 0(≤120s) |

**Grade 映射**:≥70 = green / 60-69 = yellow / <60 = red。

---

## R.1 模块构成(本 PR)

| 文件 | 作用 |
|---|---|
| `models.py` | `RealityTarget` / `Finding` / `TargetResult` / `Report` / `ReportSummary` 五个 dataclass(纯 stdlib,无 I/O) |
| `scoring.py` | `score_target(findings)` + `grade_for(score)` + `grade_to_exit_code(grade)` 纯函数 |
| `checks/__init__.py` | re-export 五条 check 函数 |
| `checks/sni_coldness.py` | 与 `seeds/top1k.json` 比对 |
| `checks/asn_match.py` | DNS resolve + 复用 `hardening/sni/asn.lookup_asn` 做 Team Cymru WHOIS |
| `checks/port_canonical.py` | 与 `seeds/standard_ports.json` 比对 |
| `checks/shortid_compliance.py` | regex 字符集 + dedup + 全零 + 长度边界检查 |
| `checks/timeout_config.py` | connIdle 阈值检查 |
| `report.py` | `render_json(report)` + `render_markdown(report)` |
| `seeds/top1k.json` | 当前 ~120 条 hot-SNI 列表(2026-04 curated baseline,Tranco 真 1k 由 R.0.5 / 季度 refresh 跟进) |
| `seeds/standard_ports.json` | 端口分级 |
| `seeds/update_top1k.py` | 季度 refresh 脚本(stdlib only,run-on-demand,非 audit pipeline 一部分)|

**未在本 PR 范围**(SPEC § PR sequencing):

- **R.2**:`cli.py`(`python -m hardening.reality.cli`)+ `loader.py`(从 panel DB 或 xray config 读)
- **R.3**:`endpoint.py`(`POST /api/reality/audit`,`SudoAdminDep`)
- **R.4**:dashboard "Reality 审计" 页(S-F-2 session 范畴)

---

## 数据流(R.1 核心,R.2 后串起来)

```
xray_config.json ─┐
                  ├─→ loader (R.2) ─→ list[RealityTarget]
panel DB rows  ───┘                       │
                                          ▼
                  for each target:
                      findings = [check_*(target, **deps) for check_* in CHECKS]
                      score = score_target(findings)
                      grade = grade_for(score)
                      → TargetResult(host, sni, port, score, grade, findings)

                  rolled-up:
                      Report(schema_version, audited_at, source, targets, summary)
                                          │
                                          ▼
                              render_json + render_markdown
```

**为何 R.1 只交付核心**:每个 check 是纯函数,可单独单测,不需要任何 I/O。loader / CLI / REST 都是"输入输出适配",并不影响打分逻辑正确性。先把核心固化、单测覆盖,后续 R.2 / R.3 加适配层只是接线,不会回头改 check。

---

## 测试策略

R.1 单测全部离线,**零网络调用**(SPEC 锁的硬要求):

- `tests/test_reality_models.py` — dataclass shape + `Report.to_dict()` schema 稳定性
- `tests/test_reality_scoring.py` — 评分边界(70 / 60 / 0 / 100 floor / ceiling)
- `tests/test_reality_report.py` — JSON byte-determinism + Markdown 结构 (含 5 件套 checklist)
- `tests/test_reality_checks.py` — 每条 check ≥ 3 单测(happy / bad / edge)。`asn_match` 走 monkeypatch `hardening.sni.asn.lookup_asn` 不打实网

---

## seeds 维护

**`top1k.json`**:Tranco-style top-1k 列表的 R.1 baseline 是 ~120 条人工策展。覆盖 CDN 巨头 / 搜索 / 社交 / compass 点名的几个坏 SNI。**季度刷新**走 `update_top1k.py`(stdlib `urllib` 抓 Tranco 真实 1k 并写回本文件)。OPS runbook 后续添加日历提醒。

**`standard_ports.json`**:运营策略文件,纯人工维护。改 critical/warning/recommended 集合是一次 PR,无代码改动。

---

## License + 上游兼容

`hardening/reality/` 全部是 fork-local 新增。不动 `app/marzneshin.py`、`app/db/*`、upstream 任何文件。upstream sync 风险面 = 0(本模块独立目录,不会与 upstream 任何 file 冲突)。

R.3 endpoint PR 会在 `hardening/panel/middleware.py` 里加 1 行 `include_router`,这是已知的"自有 router 注入点"(D-009 / `apply_panel_hardening` 模式)。

---

## 引用

- 设计 SPEC:[`docs/ai-cto/SPEC-reality-audit.md`](../../docs/ai-cto/SPEC-reality-audit.md)
- 五件套来源:`compass_artifact_wf-5103cc40-b39f-4d20-9217-61987475be44_text_markdown.md`
- 关联模块:`hardening/sni/asn.py`(asn_match 复用 WHOIS 客户端)
- 关联模块:`hardening/sni/selector.py`(remediation 文案推荐用户调用以找替代 SNI)
