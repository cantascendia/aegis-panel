# nilou.network — Landing Page

> 状态:Step 3 of payment merchant application playbook
> 用途:申请 Paddle / Lemon Squeezy / OKX Pay merchant 时提交的网站
> 关联:`docs/launch/PAYMENT-DECISION-FINAL-JP.md` §2.0

---

## 部署

### 选项 A:Cloudflare Pages(推荐)

```bash
# 1. 注册 nilou.network 域名(Cloudflare Registrar / Namecheap / Porkbun)
# 2. 把 marketing/nilou-network/ 推到 GitHub
# 3. 在 Cloudflare Pages 连接 repo,build dir = marketing/nilou-network
# 4. 自定义域名 nilou.network → Cloudflare 自动配 SSL
```

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
