# nilou.network — Landing Page

> 状态:Step 3 of payment merchant application playbook
> 用途:申请 Paddle / Lemon Squeezy / OKX Pay merchant 时提交的网站
> 关联:`docs/launch/PAYMENT-DECISION-FINAL-JP.md` §2.0

---

## 部署

### 选项 A:Cloudflare Pages(推荐 + 详细步骤)

#### A.1 域名 DNS 接 Cloudflare(10 分钟,如未做)

1. `dash.cloudflare.com` → "Add a Site" → 输入 `nilou.network`
2. Cloudflare 给 2 个 nameserver(如 `xxx.ns.cloudflare.com`)
3. 去你的域名注册商(Namecheap / Porkbun / Cloudflare Registrar 等)改 NS
4. 等 24-48 小时 DNS propagation(通常 1-2 小时)

如果**直接在 Cloudflare Registrar 注册**域名 → 跳过这步,DNS 已对接。

#### A.2 创建 Cloudflare Pages 项目(5 分钟)

1. `dash.cloudflare.com` → 左栏 "Workers & Pages" → "Create" → "Pages" tab
2. "Connect to Git" → 授权 GitHub → 选 repo `cantascendia/aegis-panel`
3. 项目名:`nilou-network`
4. Build configuration:
   - **Production branch**: `main`
   - **Framework preset**: None
   - **Build command**: 留空(纯静态)
   - **Build output directory**: `marketing/nilou-network`
   - **Root directory**: 留空
5. "Save and Deploy"
6. 1-2 分钟后:`https://nilou-network.pages.dev` 上线(Cloudflare 默认子域)

#### A.3 绑定自定义域名(5 分钟)

1. Pages 项目 → "Custom domains" tab → "Set up a custom domain"
2. 输入 `nilou.network` → 添加
3. Cloudflare 自动配 SSL(Let's Encrypt 等价)+ DNS CNAME
4. 1-2 分钟后:`https://nilou.network` 上线

#### A.4 自动部署(已配)

每次 push 到 main + `marketing/nilou-network/` 有改动 → Cloudflare Pages 自动 rebuild + 部署。无需 GitHub Actions。

#### A.5 验证

- [ ] `https://nilou.network` 返回 200,显示 hero
- [ ] `https://nilou.network/legal.html` 返回 200(等填实际住所后)
- [ ] HTTPS 证书有效(Cloudflare 自动)
- [ ] `_headers` 文件生效(curl -I 看 X-Frame-Options 等 header)

### 选项 B:Vercel / Netlify

```bash
vercel deploy marketing/nilou-network
# 或
netlify deploy --dir=marketing/nilou-network --prod
```

### 选项 C:nginx 自部署(已有 nilou.cc 服务器复用)

```bash
# 把 index.html + styles.css 放 /var/www/nilou-network/
# nginx 配 server_name nilou.network
```

## 内容合规检查

**必须**(申请 Paddle / Lemon Squeezy 前):

- [ ] 不含字眼:VPN / 翻墙 / 节点 / 反审查 / GFW / Reality / DPI / 中国 / censorship / circumvent / 突破 / proxy / anonymization
- [ ] 业务说明清晰为"开源软件订阅托管服务"
- [ ] 法律实体声明(個人事業主 + 屋号 Nilou Network)
- [ ] AGPL-3.0 合规声明
- [ ] 米哈游商标免责
- [ ] Email 收件人:`hello@nilou.network` 已配置

**可选(过审后再补)**:

- [ ] `legal.html` — 法律页面
- [ ] `terms.html` — 用户条款
- [ ] `privacy.html` — 隐私政策
- [ ] 自定义域名邮箱(Cloudflare Email Routing 免费)

## 修改提示

- 改 brand 颜色:`styles.css` 顶部 `:root` token,与 `docs/launch/brand/BRAND-GUIDELINES.md` 同步
- 加 logo:把 `docs/launch/brand/logo-master.svg` 引入,header `.brand` 改成 `<img>`
- 改套餐价:`index.html` 内的 `.plan-price`(同步 `ops/billing/pricing.py` 真实价格)

## 与 nilou.cc 关系

- `nilou.cc` = 中国客户对外站(可保留中文 + USDT 表述)
- `nilou.network` = 国际化合规站(英文 SaaS,用于 Paddle / Lemon Squeezy 申请)
- 两者**不互链**,避免审核员从 nilou.network 顺藤摸到 nilou.cc 的中文敏感词

## 变更记录

- 2026-05-03 v1 初始版,4 套餐 + 6 features + 法律/商标声明
