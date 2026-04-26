# 调研 — `v2share` 依赖(beta 版)替代评估

> 状态:已结案 → D-013(决策合入 DECISIONS.md)。本文件留作调研留痕,
> 半年内重新评估时以此为基线。
>
> 触发:`docs/ai-cto/STATUS.md` 的 Round 1 leftover "v2share==0.1.0b31
> beta 替代评估"。

---

## 数据(2026-04-26 抓取)

### PyPI

| 指标 | 值 |
|---|---|
| 最新版本 | **`0.1.0b31`** —— 就是我们当前 pin 的 |
| 上次发布 | **2025-03-06**(~14 个月前) |
| Python 要求 | `>=3.9` |
| Homepage | https://github.com/khodedawsh/v2share |
| Author / Maintainer | **None**(PyPI 元数据空) |
| License | **None**(PyPI 元数据空) |
| Summary | "generate configurations painlessly for xray/sing-box/clash" |

`0.1.0b3` 在 2024-05,到 `0.1.0b31` 在 2025-03,期间发布 ~28 个 beta,
**没有发布过 `0.1.0` 稳定版**。"beta" 在这里是**版本号习惯**(作者从来
没把它正式 1.0)而不是质量缺陷标识。

### GitHub `khodedawsh/v2share`

| 指标 | 值 |
|---|---|
| Stars / Forks | 15 / 9 |
| Open issues | 1(小问题,非阻塞) |
| 默认分支 | `master` |
| 最后 commit | **2025-03-04**(~14 个月前) |
| Archived / Disabled | 否 / 否 |
| License(repo 级) | None |

最近 5 个 commit 都集中在 2024-12 ~ 2025-03 区间(sing-box mux 修复、
splithttp pass-through 等),近 14 个月**完全停摆**。

### 关键事实:维护者身份

`khodedawsh` GitHub 用户**就是 Marzneshin 上游的主维护者**。也就是说
v2share 与 Marzneshin **生死共体**:Marzneshin 活,v2share 几乎肯定
继续维护;Marzneshin 一旦弃坑,v2share 大概率同时弃坑。

---

## 我们的使用面

`app/utils/share.py` —— 唯一使用点。导入了 `v2share` 主包 + `v2share.base`
+ `v2share.data` + `v2share.links`。功能:把 panel 的 inbound 配置
**翻译成 xray / sing-box / clash 三种协议的订阅字符串**,推给客户端订阅。

替换成本估算:

- **xray 订阅链接**(`vless://`、`trojan://` URI 格式)—— 简单,自己拼字符串可以
- **sing-box JSON 配置** —— 中等,需要跟 sing-box config schema 演进
- **clash YAML** —— 中等,proxy 类型多,边缘 case 多
- 如果都自己写,大概 1-2 周工作 + 长期维护负担(每次 xray / sing-box /
  clash 升级都可能要追)
- v2share 把这 3 件事打包成一个 Python lib 是真有价值

---

## 选项矩阵

| # | 方案 | 工作量 | 优 | 劣 |
|---|---|---|---|---|
| **A. 保持 pin,继续用** | 0 | 完全无成本,与 upstream Marzneshin 同步 | 上游 14 个月没动,bus factor = 1 |
| B. 升到稳定版 | — | — | **0.1.0 稳定版不存在,无版本可升** |
| C. Vendor 进仓库 | 1-2 天 | 我们获得直接编辑权,可补 license 声明 | 失去 PyPI 升级路径,所有上游 bug 修我们自己合 |
| D. Fork 成 `aegis-share` | 2-3 天 | 同 C + 独立 PyPI 发布 | 维护双倍 commit;若 v2share 复活合并冲突 |
| E. 自己实现 | 1-2 周 + 长期 | 完全控制 | 重复造轮子,性价比最低 |
| F. 找替代 lib | — | — | **没有覆盖 3 协议的同等 Python lib** |

## 决定:**A + 准备 C 备胎**(D-013)

**Round 3-4 阶段保持 A**:

1. 现状:上游 Marzneshin 仍活跃(2025-10-02 发 `v0.7.4`),v2share 与之
   命脉绑定;**无法律 / 安全 / 功能性紧急理由**让我们拆开
2. License 缺失风险通过"维护者归属推断"软处理:`khodedawsh` 的所有公开
   repo 都 AGPL-3.0(包括 marzneshin / marznode 等),v2share 缺 license
   可视为遗漏,实际 license 推定与作者其他作品一致。**生产 license
   audit 时这一条要单独标注**(`docs/ai-cto/AUDIT.md` 触发再说)
3. CVE 监控通过 CI 现有 `pip-audit` 自动覆盖
4. **触发 C(vendor)的硬条件**:
   - `khodedawsh/v2share` 仓库 archived 或被删
   - xray / sing-box 主版本升级 ≥1 个,v2share 6 个月无适配 commit
   - 我们自己发现 v2share 的 bug 影响订阅生成且作者不响应 PR

**今天动作**:`requirements.txt` 添加注释解释 beta 版本是上游唯一版本而非
临时选择;LESSONS / DECISIONS 留痕;不动代码。

---

## 触发复评的下一时间点

- **日历触发**:2026-10-26(从决策起 6 个月,半年回看)
- **事件触发**:见上 §决定 第 4 点的硬条件之一被满足
- 复评时把本文件作为基线,记 delta 到本文件底部,而非新建文件

---

_2026-04-26 调研 + 决策。下次复评者:把 git log + PyPI 抓取再跑一次,
对照本文件的"数据"段标 delta。_
