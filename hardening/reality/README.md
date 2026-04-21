# hardening/reality/ — Reality 配置审计

**状态**: ⏳ 待建(v0.2)

**目标**: 在管理员保存节点前,审计 `realitySettings` 是否符合 2026 加固清单:

- `shortIds` 至少 4 条、长度 ≥ 8 hex、熵 ≥ 3.5 bits/char
- `xver` 与节点 inbound 协议链一致
- `spiderX` 路径非空、非默认 `/`
- `serverName` 通过 `hardening/sni` 校验
- `dest` 可达且返回期望 TLS 指纹

## 产物

- `auditor.py` 被 `app/routes/nodes.py` 的 create/update 调用
- 审计失败 → 返回 400 + 明确错误码(方便 dashboard i18n)

## 暂无实现。
