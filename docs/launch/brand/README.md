# Brand Assets — Nilou Network

> 状态:**slots reserved**(codex 后续填充)
> 决策依据:`docs/launch/BRAND-NAMING-DECISION.md`(SEALED 2026-05-02)

---

## 资产槽清单

| Slot | 文件名 | 尺寸 | 格式 | 用途 | 状态 |
|---|---|---|---|---|---|
| L1 | `logo-master.svg` | viewBox 1024×1024 | SVG | 矢量主 logo,所有派生品的源头 | ⏳ TODO |
| L2 | `logo-512.png` | 512×512 | PNG (transparent bg) | GitHub social preview / 推特头像 | ⏳ TODO |
| L3 | `logo-256.png` | 256×256 | PNG | 邮件签名 / 名片 | ⏳ TODO |
| L4 | `logo-128.png` | 128×128 | PNG | dashboard topbar | ⏳ TODO |
| L5 | `logo-64.png` | 64×64 | PNG | 推特卡片缩略 | ⏳ TODO |
| L6 | `logo-32.png` | 32×32 | PNG | favicon @ 1x | ⏳ TODO |
| L7 | `favicon.ico` | 16+32+48 多尺寸 | ICO | 浏览器 tab | ⏳ TODO |
| L8 | `logo-pixel-64.png` | 64×64 | PNG (sharp pixels) | 像素风社区版,Discord emoji / 8-bit banner | ⏳ TODO |
| L9 | `banner-twitter.png` | 1500×500 | PNG | 推特顶图 | ⏳ TODO |
| L10 | `banner-github.png` | 1280×640 | PNG | GitHub social preview | ⏳ TODO |
| L11 | `banner-readme.svg` | 宽度 800,高度自适应 | SVG | README.md 顶部 banner | ⏳ TODO |
| L12 | `wordmark.svg` | 高度 80 | SVG | 纯文字 "Nilou Network" 字标(无图形) | ⏳ TODO |

## 填充流程(给 codex / 设计师 / 自助)

1. 读 `BRAND-GUIDELINES.md`(本目录)— 配色 / 字体 / 法律红线
2. 读 `BRAND-NAMING-DECISION.md` — 品牌精神 / 受众
3. 按上面 slot 清单产出文件,**一次提交一组**(L1+L2+L6+L7 一组,L9+L10 一组),不要 12 个文件一个 PR
4. 每个 slot 填充时:
   - 删除本目录下对应的 `.TODO` 占位文件
   - 更新本表格状态 `⏳ TODO` → `✅ filled (YYYY-MM-DD)`
   - PR 描述附加预览缩略图

## 法律红线(强制,不可逾越)

详见 `BRAND-GUIDELINES.md` §法律红线。简版:

- ❌ 不得直接复用 miHoYo / HoYoverse 受版权保护的素材文件(立绘 / 3D / CG 截图)
- ✅ 视觉相似 / 画风致敬 / 角色灵感 OK(包括与原神角色相似的发型 / 服装风格 / 姿态)
- ✅ AI 生图 OK(包括 image-to-image,但不以官方素材文件作为输入)
- ✅ 通用元素 OK(荷花 / 舞者剪影 / 波斯纹样 / 任意配色)
- ✅ 二次元画风 OK(画风不受版权保护)

## 引用方

logo 上线后会被以下位置引用,届时一并改:

- `README.md` — 顶部 banner / shields
- `dashboard/public/favicon.ico` — 浏览器 tab
- `dashboard/index.html` — `<title>` + `<link rel="icon">`
- `docs/launch/CUSTOMER-PITCH-CARDS.md` — 卡片头图
- 推特 `@niloucc` — 头像 + banner
- GitHub repo settings — Social preview

每处引用在本 README 加 backlink,便于 logo 更替时一次性扫描替换。
