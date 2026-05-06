---
name: i18n-enforcement
description: >
  在提交代码前检查国际化合规性。当任务涉及 UI 文本、提示信息、按钮标签、
  错误消息等用户可见字符串时触发。覆盖 dashboard/(react-i18next 8 语言)、
  customer-portal/(P2 起 react-i18next en/ja/zh-cn) 与 Flutter (legacy)。
  不适用于日志、注释、变量名。
---

# 国际化合规检查

在提交任何涉及用户可见文本的代码前，逐项检查。覆盖三个前端栈：

| 栈 | 路径 | 库 | 当前状态 |
|---|---|---|---|
| dashboard/ | `dashboard/src/**/*.tsx` | react-i18next | ✅ 8 语言 (en/kur/kmr/ckb/fa/ru/ar/zh-cn) |
| customer-portal/ | `customer-portal/src/**/*.{jsx,tsx}` | react-i18next (P2 起) | 🔄 P1 单语言英文,P2 加 ja/zh-cn |
| Flutter (legacy) | `*.dart` | AppLocalizations / l10n | 历史遗留 |

## React (dashboard + customer-portal) 必须通过

- [ ] 所有用户可见字符串通过 `useTranslation()` hook：`t('key.path')`
- [ ] 新增的 key 已在 `public/locales/<lang>.json` 中定义（全部支持的语言）
- [ ] dashboard：8 语言全有键
- [ ] customer-portal P2+：**3 语言**全有键(`en/ja/zh-cn`)；marketing 页可只有 en + ja/zh skeleton TODO 标记（SPEC-customer-portal-p2 TBD-9 SEAL）
- [ ] key 使用语义化路径（如 `auth.login.button.submit`），不用数字编号
- [ ] 含变量的字符串用 i18next 占位符（`{{count}} items`），不用字符串拼接
- [ ] 日期/数字/货币用 `Intl.DateTimeFormat` / `Intl.NumberFormat` 或 `i18next-icu`，不手写格式

## Flutter 必须通过

- [ ] 所有用户可见字符串通过国际化函数调用（`AppLocalizations.of(context)!.xxx`、`S.of(context).xxx`、`context.l10n.xxx`）
- [ ] 新增的字符串已在 `.arb` 文件中定义
- [ ] 字符串 key 使用语义化命名，不使用数字编号

## 常见违规模式

### React (dashboard / customer-portal)

- 直接写英文/中文在 JSX：`<button>登录</button>`、`<div>{loading ? '加载中' : ''}</div>`
- 字符串作为 prop 传入：`<Btn label="Submit" />` 而非 `<Btn label={t('btn.submit')} />`
- alert / confirm / toast 文本硬编码（应走 `t()`）
- aria-label / placeholder / title 属性硬编码

### customer-portal P1 → P2 迁移特别注意

- P1 jsx 中已有大量硬编码英文（MarketingPages.jsx / PanelPages*.jsx）— P2 必须**逐个**迁移到 `t()`
- 不允许把 P1 硬编码直接 `defaultValue` 包一层完事（L-039 documentation drift 警示）
- `MarketingSections.jsx` 中 `PLANS` / `FEATURES` / `FAQS` 数组结构需重构成 i18n key 引用而非字符串

### Flutter

- 直接写中文/英文字符串在 Widget 的 `Text()` 中
- `'确定'`、`'取消'`、`'提交'`、`'加载中'` 等常见 UI 文本硬编码
- `SnackBar`、`AlertDialog`、`Tooltip` 中的硬编码文本

## 例外

以下场景允许不走 i18n：
- 日志输出（`log()`、`print()`、`console.log()`、`debugPrint()`）
- 代码注释
- 开发者面向的调试信息
- 第三方 SDK 要求的固定字符串参数
- 品牌专有名词（`Nilou Network`、`Marzneshin`、`Reality`、`v2rayN` 等）— 但应通过 i18n key 的 `defaultValue` 而非完全跳过
- 测试 fixture 数据（`<input defaultValue="liu.wei@nilou-demo.network" />` 仅限 staging）

## customer-portal 专项检查（P2.2 起）

```bash
# 列出 customer-portal/ 中疑似硬编码英文(>3 字符 + 包含空格)
grep -rEn '>[A-Z][a-z]+[ ][A-Za-z]+' customer-portal/src/lib/*.{jsx,tsx} 2>&1 | head -20

# 验证 locale 文件 key 一致性(en/ja/zh-cn 一致)
node -e "
  const en = require('./customer-portal/public/locales/en.json');
  const ja = require('./customer-portal/public/locales/ja.json');
  const zh = require('./customer-portal/public/locales/zh-cn.json');
  const flatten = (o, p='') => Object.entries(o).flatMap(([k,v]) =>
    typeof v === 'object' && v !== null ? flatten(v, p+k+'.') : [p+k]);
  const enK = new Set(flatten(en));
  const jaK = new Set(flatten(ja));
  const zhK = new Set(flatten(zh));
  console.log('en keys:', enK.size);
  console.log('ja missing:', [...enK].filter(k => !jaK.has(k)).slice(0, 10));
  console.log('zh missing:', [...enK].filter(k => !zhK.has(k)).slice(0, 10));
"
```

参考：
- `docs/ai-cto/SPEC-customer-portal-p2.md` §1.2(i18n deliverable)+ AC §B 全 6 项 checkbox
- `dashboard/src/features/i18n/index.ts` — pattern to mirror
