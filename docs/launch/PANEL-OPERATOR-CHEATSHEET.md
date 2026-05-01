# 后台面板操作 Cheatsheet — 不再问 AI

> 大部分操作 dashboard 都能做，不用 SSH。本 cheatsheet 列出每个常用操作的具体点击路径。

**面板地址**：https://nilou.cc/HFPB5MLu/  
**登录**：riku / FSZChDAcVwSH1N9TaBA3

---

## 🎯 最常用 5 个操作

### 1. 开新账号

**界面操作**：
1. 左侧菜单 → **Users** / **用户管理**
2. 右上角 **➕ Create User** / **创建用户**
3. 填字段：
   - Username：`alice` 或客户外号（英文/数字，**不要空格中文**）
   - Services：勾选 **Reality-VLESS**（必选）
   - **Data Limit**：
     - trial → `50` GB
     - m1 → `100` GB
     - q1 → `300` GB
     - y1 → `1228` GB（1.2 TB）
   - **Reset Strategy**：选 **No Reset**
   - **Expiration**：选 **Fixed Date**
   - **Expire Date**：
     - trial → 今天 +3 天
     - m1 → 今天 +30 天
     - q1 → 今天 +90 天
     - y1 → 今天 +365 天
   - **Note**：写 `m1 - WeChat: alice / paid USDT 4.2 / 2026-05-XX` 自留底
4. **Save** / **保存**

✅ 创建后用户出现在列表。

### 2. 拿订阅链接发客户

**界面操作**：
1. **Users** 列表
2. 点用户那一行的 **eye 图标** / **详情**（或点用户名）
3. 弹出 dialog 中有：
   - **Subscription Link** + **复制按钮**（一键复制完整 URL）
   - **QR Code**（手机扫码也能用）
4. **复制 URL** → 粘贴到客户微信

✅ 客户在 Streisand / V2Box / Shadowrocket 里"添加订阅 → 从 URL"粘贴即可。

### 3. 续费（30 天 → 60 天）

**界面操作**：
1. **Users** 列表
2. 点该用户 → **Edit** / **编辑**
3. 改 **Expire Date**：原日期 +30 天
4. 改 **Data Limit**（如果加流量）：原值 + 100 GB
5. **Save**

✅ 客户**不用换订阅链接**，自动延期。

### 4. 停用 / 关闭账号

**界面操作 A（暂停，可恢复）**：
1. **Users** 列表
2. 点用户 → 找 **Enabled toggle** / **启用开关**
3. 关掉 → **Save**

✅ 用户连接立刻断；订阅 URL 仍存在但客户连不上。

**界面操作 B（永久删除）**：
1. **Users** 列表
2. 点用户右侧的 **垃圾桶图标**
3. 确认删除

⚠️ 删除后无法恢复。流量统计也清空。

### 5. 看流量统计 / 谁用了多少

**界面操作**：
1. **Home** / **首页** Dashboard
2. 看顶部 **Total Users** / **Active Users** / **Online**
3. **Users** 列表里每行有 **Used Traffic** 列（实时刷新）
4. 点用户 → **详情**里有按月/按日历史图表

---

## 🔧 节点管理（很少改）

### 看节点是否健康
**Nodes** 菜单 → 表格里 **Status** 列：
- ✅ **healthy** → 正常
- 🟡 **unhealthy** → 看 Message 列描述
- 🔴 **disabled** → 操作员手动停用了

### 重新连接节点（同步出问题时）
1. **Nodes** 菜单 → 点 tokyo-1 那行
2. 找 **Resync** / **重新同步** 按钮（如果有）
3. 或 **Edit** → **Save**（不改任何字段）→ 自动触发重连

✅ 等价于 SSH 跑 `aegis-upgrade`，但 30 秒搞定。

---

## 🔑 修改 admin 密码 / 加协助操作员

**界面操作**：
1. **Admins** 菜单（左侧）
2. **➕ Add Admin** 创建子管理员（**关掉 sudo** 给个普通权限的助理）
3. 编辑自己 → 改密码

⚠️ 别忘旧密码，丢了只能 SSH 救（去 `/opt/aegis/.env` 看 `SUDO_PASSWORD`）。

---

## 💸 计费 / 收款（B 阶段先手工，无 self-service）

dashboard **Billing** 菜单目前用不太上（没 plan / channel 数据）。

**手工流程**：
1. 客户微信付 USDT 4.2 / 支付宝 ¥31.5
2. 你截图保存 + 在 `Note` 里记录
3. 用 §1 创建账号

**未来**（≥3 客户 + 有人主动要 self-service 时）才接 web checkout。

---

## ❌ 这些 dashboard 做不了，必须 SSH

仅以下情况需要让 AI / 直接 SSH：
1. **服务器升级**（panel / marznode 版本切换）→ `ssh root@VPS aegis-upgrade vX.Y.Z`
2. **节点断同步**（manage page 空 + 真客户连不上）→ 跑 `aegis-sync-clients`
3. **完全宕机**（dashboard 都打不开）→ 看 docker 容器
4. **改 Reality 私钥 / SNI / xray_config 底层** → 改 `/opt/aegis/data/marznode/xray_config.json`

✅ 平时 95% 操作（开账号/复制 URL/续费/停用/看流量）**全在 dashboard 做**。

---

## 🚨 万一搞错了

操作前确认：
- 删用户前看清 `Username`，**别误删客户**
- 改 `Expire Date` 别改成过去日期（会立刻断）
- 把 `Enabled` 关了客户立刻断，要继续用记得开回

**误操作能恢复**：
- 删除用户 → 不能恢复（流量统计清空，UUID 重新生成）
- 改 expire date / data_limit / enabled → 改回去就行

---

## 📱 移动端访问

dashboard 是响应式的，**手机浏览器**能直接登录用。
- iOS Safari：直接打开 https://nilou.cc/HFPB5MLu/
- 收藏到主屏幕，加图标当 App 用
- ⚠️ Public WiFi 别登录，回家 5G 再登

---

## 🆘 实在搞不定再找我

只有以下情况联系我：
1. dashboard **完全打不开**（白屏 / 502）
2. 客户报"连不上"+ 你 dashboard 里看着 **状态是 healthy**
3. **服务器升级**（v0.4.x 之后我再发版本通知你）
4. 收 USDT 工具流程没跑通

其它操作 dashboard 自己点，**不用问我**。
