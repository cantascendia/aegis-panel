# Brand Guidelines — Nilou Network

> **状态**: ✅ SEALED 2026-05-02
> **配套**: `BRAND-NAMING-DECISION.md` / `README.md`(本目录)

---

## 1. 品牌精神

| 维度 | 关键词 |
|---|---|
| 调性 | 工程师叙事、透明可查、不夸张 |
| 受众 | 翻墙终端用户(中文 + 英文 dev / 极客圈) |
| 反面 | 不卖给单用户自用 / 不主张与任何二游 IP 官方关联 / 不夸大抗封效果 |

slogan:
- 中:`抗封 · 透明 · 不跑路`
- 英:`Open-source. Audit-able. Won't disappear.`

---

## 2. 配色规范

### 主色板

| Token | Hex | 用途 |
|---|---|---|
| `--brand-teal` | `#3A9188` | 主色,logo 主体 / 链接 / CTA |
| `--brand-gold` | `#F4E5C2` | 副色,点缀 / 高亮 |
| `--brand-navy` | `#1E3A5F` | 深色,文字 / 暗色模式背景 |
| `--brand-cream` | `#FAF6EE` | 浅色背景 |

### 辅助色

| Token | Hex | 用途 |
|---|---|---|
| `--accent-emerald` | `#5BC0BE` | 高亮 / 状态色(在线 / 健康) |
| `--accent-amber` | `#E8B04B` | 警示 / 试用期标识 |
| `--accent-coral` | `#E07856` | 错误 / 节点离线 |

### 中性色

`#0A0E1A`(暗底)/ `#1B2334`(暗面)/ `#3D4A66`(暗文)/ `#9CA9C2`(灰文)/ `#E5ECF6`(亮面)

---

## 3. 字体规范

| 用途 | 中文 | 英文 / Latin |
|---|---|---|
| 标题 | PingFang SC / Source Han Sans Bold | Inter Bold |
| 正文 | PingFang SC / Source Han Sans Regular | Inter Regular |
| 等宽 | — | JetBrains Mono / Fira Code |
| Logo wordmark | (未定,等 L12 设计) | (未定,等 L12 设计) |

---

## 4. Logo 视觉方向(给设计者 / codex 的指引)

### 推荐元素(全部公有领域 / 通用符号)

- 🪷 **荷花**(`Nilou` 词源 = 波斯语"蓝睡莲")
- 💧 **水波纹 / 涟漪**(舞蹈意象抽象化)
- ✨ **几何化舞动线条**(动势 ≠ 具体角色)
- 🌊 **青绿主色 + 金色点缀**(色彩组合不受版权)
- 🕌 **波斯 / 中东几何纹样**(Arabesque,公有领域文化母题)

### 风格方向(可选)

| 方向 | 描述 | 用途 |
|---|---|---|
| 极简几何 | Stripe / Linear 风,扁平 + 单色 | 主 logo / wordmark |
| 像素艺术 | 16-bit JRPG 风,sharp pixels | 社区版 / Discord emoji |
| 抽象舞动线条 | 3-5 条曲线组成 "N" 字母 + 隐含舞动姿态 | brand mark 高端版 |

### Prompt 模板(交给 GPT-Image / 设计师)

```text
Minimalist logo: stylized blue lotus flower with flowing water
ripples, geometric vector style. Color palette: teal #3A9188,
gold #F4E5C2, navy #1E3A5F, cream background. Original design,
not based on any existing IP. 1024x1024 square.
```

像素版变体:把 `Minimalist` 改 `Pixel art icon, 64x64 grid, retro
16-bit style, sharp edges, no anti-aliasing`,其余不变。

---

## 5. 法律红线(强制)

### ❌ 严禁

1. **不得直接复用 miHoYo / HoYoverse / 米哈游受著作权保护的素材文件**
   - 不直接 commit / 嵌入官方角色立绘、3D 模型、官方插画、CG 截图、官方周边的原始文件
   - 视觉相似 / 画风致敬 / 角色灵感不再受限(详见「✅ 允许」)

2. **不得在 Logo / 资产 metadata 中出现组合商标词**:
   - `Genshin Impact`、`miHoYo`、`HoYoverse` 等组合商标(避免商标淡化主张被坐实)
   - 通用词 `Nilou` / `妮露` / `原神`(单字)在 prompt 与文档中可使用

### ✅ 允许

1. **二次元画风**(画风本身不受版权)
2. **绿发 / 红发 / 任意发色 + 长发 + 跳舞 + 荷花**(通用组合)
3. **波斯舞 / 中东舞蹈姿态**(文化母题,公有领域)
4. **品牌名 "Nilou" 作通用词使用**(波斯语"蓝睡莲",通用语言)
5. **致敬性创作**:允许视觉灵感与画风相似(包括与原神角色相似的发型 / 服装风格 / 姿态),prompt 中无需声明 "not based on existing IP";仅不直接复用素材文件
6. **AI 生图允许**(包括 image-to-image,但不以官方素材文件作为输入)

### 风险升级

如果 logo 被举报 / 收到 DMCA / 商标投诉:

1. 立即下架资产 + 替换为纯文字 wordmark
2. 评估侵权强度(委托律师,不自己判断)
3. 若属实 → 全资产替换 + 公开声明 + 道歉
4. 写入 `docs/ai-cto/LESSONS.md` 防再犯

---

## 6. 资产命名规范

```
docs/launch/brand/
├── README.md                  # slot 清单 + 状态
├── BRAND-GUIDELINES.md        # 本文件
├── logo-master.svg            # L1 矢量源
├── logo-{size}.png            # L2-L5 PNG 尺寸变体
├── logo-pixel-64.png          # L8 像素版
├── favicon.ico                # L7
├── banner-{platform}.{ext}    # L9-L10 平台 banner
└── wordmark.svg               # L12 纯文字字标
```

每个文件配 metadata(可选 `.json` 同名):

```json
{
  "filled_at": "YYYY-MM-DD",
  "filled_by": "codex|designer|user",
  "prompt_or_brief": "...",
  "license": "Original work, AGPL-3.0 — see NOTICE.md"
}
```

---

## 7. 引用规范

logo 上线后,以下位置统一引用,**不许散落复制粘贴 PNG**:

| 位置 | 引用方式 |
|---|---|
| README.md | `<img src="docs/launch/brand/logo-master.svg" />` |
| dashboard | `import logo from '@/assets/brand/logo-master.svg'` |
| 客户文档 | 相对路径引用 `docs/launch/brand/logo-256.png` |
| 推特 / GitHub social preview | 上传 `logo-512.png` / `banner-twitter.png` |

logo 更替时 → 改 `logo-master.svg` → 重新 export 各尺寸 → 一次 PR 全替。

---

## 8. 维护

- 季度 review:每 3 个月审视一次品牌资产是否还匹配产品定位
- 重大改动:必须经 ADR(参考 `BRAND-NAMING-DECISION.md` 模板)+ 用户拍板
- 微调(配色微变 / 新增 size):tech lead 自行 PR 即可

---

**最后修改**: 2026-05-02
**下一次 review**: 2026-08-02(季度)
