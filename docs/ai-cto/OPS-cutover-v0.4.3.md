# OPS Runbook — v0.4.3 Production Cutover

> **状态**: 待 operator 本机执行(沙箱拒嵌密码 SSH,符合最小信任原则)
> **影响**: 仅 dashboard 浏览器 tab `<title>` 文本 + logo alt — 客户感知 = tab 标题改为 "Nilou Network"
> **风险等级**: 低(无 schema / API / 数据流改动);回退 30 秒
> **关联 PR**: #205-#213(wave-10 品牌生效全栈)

## Pre-flight

- [ ] image `ghcr.io/cantascendia/aegis-panel:v0.4.3` 已 build success(GitHub Actions run `25254350491`)
- [ ] main 在 `47ce61b` 之后(本 runbook merge 后会前进)
- [ ] 当前生产 = v0.4.2(SHA `e76d5a5d96d7`)

## Cutover(operator 本机执行)

```bash
ssh root@nilou.cc

# in remote shell:
cd /opt/aegis-src
git fetch --tags
git checkout v0.4.3
cd deploy/compose
docker compose -f docker-compose.sqlite.yml pull panel
docker compose -f docker-compose.sqlite.yml up -d panel

# verify (≤10s panel restart 期内可能短暂 502)
sleep 10
docker ps --filter name=panel --format "{{.Image}} | {{.Status}}"
curl -s https://nilou.cc/api/aegis/health
```

预期输出:
- `docker ps`: image tag 含 `v0.4.3`,Status `Up X seconds (healthy)`
- `health`: `{"status":"ok",...}` 200

## 客户端验证

- [ ] 浏览器打开 `https://nilou.cc/HFPB5MLu/`,tab title 显示 **"Nilou Network"**(原 "Marzneshin")
- [ ] dashboard logo alt 文本 = "Nilou Network"(右键 logo 图 → 检查 → alt 属性)
- [ ] favicon 仍是 PR #210 ship 的 project-icon.png(本 cutover 不动)

## 回退(若 panel 起不来)

```bash
docker compose -f docker-compose.sqlite.yml down panel
git checkout v0.4.2
docker compose -f docker-compose.sqlite.yml up -d panel
```

回退耗时 ~30s。客户连接 30s 内有重连即可。

## Cutover 后

- 在 `docs/ai-cto/STATUS.md` 把 wave-10 条目的 cutover 状态从"⏸ 待 operator"改为"✅ live YYYY-MM-DD"
- 在 `docs/ai-cto/SESSIONS.md` 记录 cutover 完成时间

## 为什么沙箱拒了 AI 自动 cutover

详见 `docs/ai-cto/LESSONS.md` 设计原则:嵌密码 SSH 进生产 = 高危,即使工作目标合规也应 fail-safe。Operator 本机执行保留人工 gate,符合 §32.1 forbidden-paths(`deploy/`)精神。

未来想 AI 自动 cutover:走 SSH key + 限制 sudo + 单步 preview(不是 pull/up 链式),不要走嵌密码路径。
