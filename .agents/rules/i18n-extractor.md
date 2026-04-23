---
name: i18n-extractor
description: Dashboard i18n 抽取契约 —— 避免 drift-gate 假阴/假阳
activation: glob
globs:
  - "dashboard/src/**/*.tsx"
  - "dashboard/src/**/*.ts"
  - "dashboard/public/locales/*.json"
  - "tools/check_translations.sh"
---

# 前端 i18n 抽取契约(硬规则)

源自 LESSONS **L-012**(locale drift gate 最初的假阳性灾难)和
**L-017**(注释含 `t("...")` 字面导致 drift 误报),两条已反复
踩过,必须固化成规则。

## 背景

`tools/check_translations.sh` 用行级 PCRE 正则抽 t() 调用:

```
\Wt\(["']\K[\w.-]+(?=["'])
```

规则:正则必须看到 `t("key")` 或 `t('key')`,**引号必须紧贴括号**,
**key 必须是纯字面量**(字符类 `[\w.-]+` = `[a-zA-Z0-9_.-]+`)。

任何让这个正则误抓或漏抓的写法都会在 CI 触发 drift gate 失败,
浪费 1-3 轮迭代。

## 硬规则

### ✅ 允许的 t() 写法

```tsx
// 1. JSX 里最常见,短 key,引号紧贴:
<span>{t("page.billing.invoices.title")}</span>

// 2. toast / mutate 里,单 options 对象:
toast.success(
    i18n.t("page.billing.invoices.toast.apply_success", {
        defaultValue: "Invoice #{{id}} applied",
        id: inv.id,
    })
);

// 3. 长 key 先提到 const,JSX 引用 const(biome 不会拆开简单变量引用):
const notePlaceholder = t("page.billing.invoices.action.note_placeholder");
return <Textarea placeholder={notePlaceholder} />;
```

### ❌ 禁止的 t() 写法

```tsx
// ❌ 1. 三参数形式 —— biome 会换行把引号甩到下一行:
t("page.billing.plans.toast.create_success", "Plan {{code}} created", {
    code: plan.operator_code,
});

// ❌ 2. JSX 属性里直接写长 key,biome 换行后正则抓不到:
<Textarea
    placeholder={t(
        "page.billing.invoices.action.note_placeholder",
    )}
/>

// ❌ 3. 动态 key / 模板字面:
t(`page.billing.state.${state}`);  // 正则只抓字面,动态的就漏
t(opt.labelKey);                    // 同样漏
```

### 注释里不得写 `t("...")` 字面

这是 L-017 的直接教训。

```tsx
// ❌ 下面这行会让正则把 "..." 抽成 source key,drift +1:
// Extract to a const so the extractor regex sees a single-line t("...") call

// ✅ 改写成不含 t() 字面的描述:
// Extract to a const so the extraction regex sees a single-line call
// (biome wraps long i18n calls in JSX attributes; the line-based
// scanner needs the quote right after the paren).
```

## Locale 文件编辑规则

- `en.json` 和 `zh-cn.json` 是 canonical,新 key **必须**同时添加
  两边
- 其他 6 个 locale(fa / pt-br / ru / ar / zh-tw / tr)在增量 PR
  里**不动**,避免扩大 drift baseline —— 一次性同步走专门的 "locale
  parity cleanup" PR
- JSON key subtree 用**段组 append-only**,不和别人的 subtree 交叉
  - 管理员面:`page.billing.{plans,channels,invoices}.*`
  - 用户面:`page.billing.{purchase,my_invoices}.*`
  - Reality 审计:`page.reality.*`(S-R 专用)

## PR preflight(本地一次性检查)

drift-gate 依赖 `jq`(Ubuntu CI 装;Windows git bash 没装),所以
本地用 Python 跑一次等价检查:

```bash
# 用 Python 替代 jq(Windows 友好),参数对齐 CI
LANG=C.UTF-8 LC_ALL=C.UTF-8 grep --exclude-dir={node_modules,dist} \
    -orPh "\Wt\([\"']\K[\w.-]+(?=[\"'])" dashboard/ | sort | uniq > /tmp/head_keys.txt

python -c "
import json
j = json.load(open('dashboard/public/locales/en.json', encoding='utf-8'))
def flat(o, p=''):
    r = []
    for k, v in o.items():
        kk = f'{p}.{k}' if p else k
        if isinstance(v, dict): r += flat(v, kk)
        else: r.append(kk)
    return r
json_keys = set(flat(j))
src = [l.strip() for l in open('/tmp/head_keys.txt') if l.strip()]
missing = [k for k in src if k not in json_keys]
extra = [k for k in json_keys if k not in src]
print(f'en.json: missing={len(missing)} extra={len(extra)}')
"
```

基线(2026-04-23):`en.json: missing=23 extra=65`、
`zh-cn.json: missing=45 extra=0`。新 PR 后两者都不得**升高**。

## CI 失败快速排查顺序

drift 失败时,按顺序查:

1. 是不是忘了把新 key 加到 `en.json` + `zh-cn.json`
2. 是不是注释里不小心写了 `t("...")` 字面(L-017)
3. 是不是 biome 把 `t("…")` 拆成多行(3 arg 形式;或长 JSX 属性)
4. 是不是用了动态 key(模板字面/变量 key)
5. 是不是 locale 文件 JSON 语法坏掉(用 `python -c "import json; json.load(open('...',encoding='utf-8'))"` 验证)
