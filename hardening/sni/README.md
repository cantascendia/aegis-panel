# hardening/sni/ — SNI 智能选型器

**状态**: ⏳ 待建(v0.2 差异化 #1)

**目标**: 输入 VPS 出口 IP → 输出候选 SNI 列表(已通过 6 条硬指标验证)。

## 六条硬指标(来自 `compass_artifact_*.md`)

1. TLS 1.3 握手成功
2. 支持 HTTP/2(ALPN `h2`)
3. 使用 X25519 曲线
4. 非 301/302 跳转域
5. 与 VPS **同 ASN**(避免 BGP 层关联暴露)
6. 不在已知 DPI / GFW 黑名单

## 产物

- `selector.py` CLI:`python -m hardening.sni.selector --ip <vps-ip> --count 5`
- dashboard 集成:新建节点流程调用,预填 `serverName` 字段
- 单测 + 网络 mock fixture

## 暂无实现。
