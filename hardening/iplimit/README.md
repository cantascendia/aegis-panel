# hardening/iplimit/ — 原生 IP 并发限制

**状态**: ⏳ 待建(v0.3)

**为什么自研**: Marzban 生态的 V2IpLimit / miplimiter / luIP 全部**不兼容
Marzneshin**(API 路径不同,详见 `docs/ai-cto/COMPETITORS.md` 第 5 节)。不
走 "fork 外挂工具改 API" 路线 —— 维护成本高,每次 upstream 更新都要跟。

## 方案

1. 订阅 Marznode 暴露的 Xray `stats` gRPC(`app/marznode/` 已有基础)
2. 按用户级计数当前连接 IP 集合,超阈值触发:
   - 断连多余连接(优先断最后登录)
   - Telegram / email 告警
3. 策略可配置:`max_concurrent_ips` / `grace_period` / `country_filter`

## 参考

- Hiddify `app/roles/shared_limit.py` 算法(见 COMPETITORS.md 建议 3)
- 不要 copy AGPL 代码(Hiddify 也是 AGPL),要重写并在本目录声明 AGPL

## 暂无实现。
