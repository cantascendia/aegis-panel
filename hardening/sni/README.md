# hardening/sni/ — SNI 智能选型器(MVP)

**状态**: ✅ v0.2 MVP(PR #13)

**目标**: 输入 VPS 出口 IP → 输出候选 SNI 列表(已通过 6 条硬指标验证)。

> **运维手册**: 故障排查 / 周期性重新验证 / blacklist 与 seeds 编辑 SOP →
> [`docs/ai-cto/OPS-sni-runbook.md`](../../docs/ai-cto/OPS-sni-runbook.md)。
> 本 README 是开发侧"模块构成";runbook 是运营侧"出事怎么办"。

## 六条硬指标(按 cheap-first 顺序执行)

1. **不在 DPI 黑名单**(`blacklist.yaml` 精确匹配,~free dict lookup)
2. **HTTP HEAD 不 301/302 跳转到不同域**(~50ms)
3. **与 VPS 同 ASN**(Team Cymru WHOIS 查询,`whois.cymru.com:43`)
4. **TLS 1.3 握手成功**
5. **ALPN 成功协商 `h2`**
6. **ECDHE 协商到 X25519 曲线**

指标 4-6 复用**同一个 TLS 握手**(一次 connect,三个布尔),避免对目标站三倍负载。

## X25519 检测的平台注意

- **Python 3.13+** + **OpenSSL 3.2+**: 通过 `ssl.SSLSocket.group()` 精确识别
- **Python 3.12**(CI + 多数生产): stdlib `ssl` 模块没暴露 API → 我们用 **实用 fallback**:TLS 1.3 成功握手且我方 client ctx 已 advertise X25519 → 视为 X25519 pass。真实 OpenSSL 3.0+ 服务器 ≥95% 默认 prefer X25519,fallback 与真相一致度很高
- **Python 3.11 或更早 / OpenSSL < 3.0**: 检测准确度下降,建议升级

生产建议:跑 Python 3.13 获得精确检测。3.12 足够 MVP,只是个别 exotic 服务器可能假阳。

## 数据源决策

**ASN / country 查询用 Team Cymru 免费 WHOIS**(`whois.cymru.com:43` TCP)。
- 无 API key / 无注册 / 无限流
- 单次 ~100ms,LRU 缓存 1024 条
- 备选但未实施:RIPE/ARIN WHOIS(更慢,作为 fallback 在 v0.3 再加)

**拒绝**(带理由):
- MaxMind GeoLite2: 要注册 license + 定期更新 DB,MVP 尺度下收益不抵运维复杂度
- IPinfo / IP2Proxy: 付费
- Cloudflare Radar API: 新且数据好,但要 API key

## DPI 黑名单

`blacklist.yaml` 手工维护,MVP 级别:当前 5 条(compass_artifact 文档引用的典型坏 SNI)。
- 编辑规则:PR 追加,每条带 `reason` + `source` + `added` 字段
- 未来 v0.3 接入情报订阅(SSL Labs / Abuse feeds)

## 候选种子表

`seeds/*.yaml`,按区域组织:
- `global.yaml` —— 全球 anycast CDN(微软 / 苹果 / Mozilla / Bing 等)
- `jp.yaml` / `kr.yaml` / `us.yaml` / `eu.yaml` —— 区域特色候选
- `--region auto`(默认)== 只加载 `global.yaml`
- `--region jp` == `global.yaml` + `jp.yaml` 去重合并

MVP 提供 ~20 条种子,生产使用可按需扩充(每条都要有 `notes`)。

## CLI 用法

```bash
# 从全球池选 10 条
python -m hardening.sni.selector --ip 1.2.3.4 --count 10

# 从日本区域池选 5 条
python -m hardening.sni.selector --ip 103.x.x.x --count 5 --region jp
```

输出 JSON 到 stdout。退出码:
- `0`:至少 1 个候选通过
- `1`:零候选通过(输出仍给,但运营者要看 `rejected[]` 字段找原因)
- `2`:VPS 的 ASN 查不到(致命,工具不可用)

## 输出 schema

见 `docs/ai-cto/SPEC-sni-selector.md` 的 "Output format" 段。`tests/test_sni_selector.py::test_output_json_schema_golden` 守护这个 schema,drift 会炸。

## 模块文件

| 文件 | 作用 |
|---|---|
| `__init__.py` | 公共 API re-export |
| `candidate.py` | `Candidate` / `CheckResults` / `Rejection` / `SelectorResult` dataclasses(纯 Python,无依赖) |
| `asn.py` | Team Cymru WHOIS + LRU 缓存 + `lookup_asn(ip)` async |
| `checks.py` | 六条硬指标的 check 函数 |
| `scoring.py` | `score_candidate(checks)` 纯函数打分 |
| `loaders.py` | YAML 加载 + 校验(`SeedLoadError`) |
| `selector.py` | orchestrator + `main()` CLI 入口 |
| `endpoint.py` | **FastAPI router `POST /api/nodes/sni-suggest`** — 由 `hardening/panel/middleware.apply_panel_hardening()` 注册,dashboard 前端调用 |
| `blacklist.yaml` | DPI 黑名单数据 |
| `seeds/*.yaml` | 候选种子数据(按区域) |

## HTTP 端点

`POST /api/nodes/sni-suggest`

- **Auth**: sudo admin(`SudoAdminDep`)
- **Rate limit**: **当前未装**(async def + slowapi 在 Linux CI 上真实触发 422,见 endpoint.py 模块 docstring 和 LESSONS.md L-010)。依靠 sudo-admin 门 + 60s wall-clock + `Semaphore(5)` 多层防御;Linux 环境下的 reproducer 搞定后再装回
- **Timeout**: 60 秒(`asyncio.wait_for`)
- **Request**:
  ```json
  {"vps_ip": "1.2.3.4", "count": 5, "region": "auto"}
  ```
  - `vps_ip`: 必填,字符串,IPv4/IPv6 均可
  - `count`: 1~50,默认 5
  - `region`: `auto | global | jp | kr | us | eu`
- **Response**: 与 CLI JSON 完全一致(`SelectorResult.to_dict()`),由 `test_output_json_schema_golden` 守护 schema
- **错误码**:
  - `401` — 未认证
  - `403` — 非 sudo admin
  - `422` — 请求体验证失败(例如 region 非白名单)
  - `500` — seeds/blacklist.yaml 加载失败(`sni_seed_load_error: ...`)
  - `504` — 60 秒探测超时(`sni_probe_timeout: ...`)

**架构说明(SPEC 偏离)**: SPEC 原写"`app/routes/node.py` 加新端点",实际落在 `hardening/sni/endpoint.py` 并通过 `apply_panel_hardening()` 注册。目的:保持 `app/routes/*` 零修改,upstream-sync 冲突面继续 = 一行。这是 Round 1 "upstream 冲突面 = 一行"原则的延用,不是新决策。

## 后续 PR(SPEC follow-up)

- ✅ PR #13: `feat(hardening): sni selector core + 6 indicators`(module + CLI + 41 测试)
- ✅ PR #16: `feat(hardening): sni dashboard endpoint`(endpoint + 10 测试)
- ✅ PR #18: `feat(dashboard): sni-suggest dialog`(新建节点表单 "Suggest SNI" 按钮)
- ⏳ rate-limit 装回 —— PR #22 尝试失败(Linux CI 422 实锤),延后到有 Linux Docker reproducer 再处理
- ⏳ `docs(hardening): sni runbook` — `deploy/README.md` 加 "全部候选不合格" 的排查手册
- 未来 v0.3: live DPI 情报订阅 + `/24` scan mode + 持续健康度监控

## Dashboard 集成(v0.2 尾段)

前端通过 `dashboard/src/modules/nodes/dialogs/sni-suggest/` 调用此端点:

- 新建节点对话框底部加一颗 "Suggest SNI" 按钮(`address` 填了才可点)
- 弹出独立 dialog,默认 VPS IP = node address,用户可改
- 参数:count(1-50,默认 5)+ region(auto / global / jp / kr / us / eu)
- 结果:按 score 降序,每行显示 6 条硬指标 ✓/✗ + 复制按钮
- Rejected 折叠区帮助运营排查 "为什么候选空"
- 全流程 i18n(8 语言,英文 canonical + 中文完整翻译)

**不做**的事:
- 不在 IP 输入时自动触发探测(每次 blur 都打第三方 CDN 握手太粗暴)
- 不自动把选中的 SNI 填进某个字段 —— Node 模型没有 SNI 字段,SNI 属于 inbound/service Reality 配置,让用户拷贝到真正需要的地方
