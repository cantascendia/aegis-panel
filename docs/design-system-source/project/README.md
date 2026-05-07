# Nilou Network — Design System

A managed-hosting brand for self-hosted open-source apps, run by an independent operator in Japan. The brand vocabulary is **lotus + water-ripples + Persian/Sumeru-inspired geometric arabesque** — calm, audit-able, engineer-narrative. Slogan: *Open-source. Audit-able. Won't disappear.* (中文: 抗封 · 透明 · 不跑路)

> **Trademark notice.** "Nilou" is used here as a generic word — Persian for *blue lotus*. Nilou Network is independent and **not affiliated with miHoYo / HoYoverse or the *Genshin Impact* franchise.** No copyrighted assets are used. The visual style is *inspired-by* (color, geometry, mood), not *derived-from*.

---

## Sources

Everything in this design system is lifted from the user's repo. The reader may not have access; paths kept for reference.

- **Repo:** `cantascendia/aegis-panel` (default branch `main`) — AGPL-3.0 fork of Marzneshin
- **Public landing site:** `marketing/nilou-network/` (live at https://nilou.cc / https://nilou.network)
  - `styles.css` — production landing CSS (source of truth for tokens)
  - `en/index.html`, `ja/index.html`, `zh/index.html` — three-language landing
- **Brand book:** `docs/launch/brand/BRAND-GUIDELINES.md`
- **Voice & copy:** `docs/launch/CUSTOMER-PITCH-CARDS.md`, `CUSTOMER-FAQ.md`, `BRAND-NAMING-DECISION.md`
- **Dashboard app (Marzneshin fork):** `dashboard/` — Vite + React + Tailwind + shadcn/ui + NextUI

## Products represented

1. **Marketing site** (`marketing/nilou-network`) — static landing, three languages. Cormorant + Inter, cream/teal/gold palette, lotus/ripple/arabesque motifs.
2. **Aegis Panel / Marzneshin Dashboard** (`dashboard/`) — operator-facing admin panel for managing nodes, users, hosts, services, billing, audit, Reality config. shadcn/Tailwind base; semantic HSL tokens; light + dark.

The marketing site is the *brand expression*; the dashboard is the *product*. They share color tokens but diverge on type (dashboard uses Lato + Ubuntu via Tailwind config; marketing uses Cormorant + Inter). The design system biases toward the **marketing palette** — that is the canonical brand direction; the dashboard inherits it.

---

## Index — what's in this folder

| File | What it holds |
|---|---|
| `README.md` | this file — context, content, visual foundations, iconography |
| `SKILL.md` | Agent SKill manifest — drop-in for Claude Code |
| `colors_and_type.css` | CSS variables for the full token system + semantic type classes |
| `assets/` | logos, lotus mark, arabesque pattern, feature icons, hero screenshot |
| `fonts/` | (none — fonts loaded from Google Fonts; see Substitutions below) |
| `preview/` | small HTML cards that populate the Design System tab |
| `ui_kits/marketing-site/` | high-fidelity recreation of the landing page + components |
| `ui_kits/aegis-panel/` | high-fidelity recreation of the operator dashboard + components |

---

## CONTENT FUNDAMENTALS

The voice is **engineer-narrative**: transparent, mildly self-deprecating, refuses to oversell. It is allergic to enterprise marketing hyperbole. Two languages run in parallel — Chinese (peer-to-peer, WeChat-native, conversational) and English (calmer, more documentary).

### Casing & punctuation
- **Sentence case** for headlines and body. Title Case is reserved for nav items and plan tier names (`Trial`, `Monthly`, `Quarterly`, `Annual`).
- **Em dashes ( — )** are heavily used to set off clarifications. Native to the voice.
- **Italic** is reserved for: brand emphasis on the display serif (`<span class="accent">without the self-hosting.</span>`), and for trademark hedges (*Genshin Impact*, *個人事業主*).
- Periods at the end of body sentences. Eyebrow labels and pill tags are **unpunctuated**.

### Pronouns
- "**We**" (the operator) and "**you**" (the customer). Never "users". The operator is one person, never a corporate "team".
- The dashboard speaks in **imperative + noun phrases** ("Add user", "Reset usage", "Disable host") — typical admin-panel voice.

### Tone calibration

| Move | Yes | No |
|---|---|---|
| Honesty | "We do not offer a contractual SLA at the current scale" | "Enterprise-grade SLA" |
| Mechanism > promise | "跑路 = 公开打脸" (running away = public face-slap, code is on GitHub) | "We promise we won't disappear" |
| Numbers w/ caveats | "Near 0.5% block rate; industry average 5–8%" | "Near 0% block rate" |
| Scarcity disclosure | "B-phase cap: 200 users. Word of mouth only." | "Scaling fast" |

### Emoji
**Sparingly, only in product/marketing copy in CN.** Pitch cards use ✅ for "what we do" lists, 🇯🇵🇭🇰🇺🇸 for region flags, 🪷 for the lotus motif. **Dashboard never uses emoji.** **English landing avoids emoji** entirely.

### Sample voice — short-form
> "you bought an airport that got blocked? you suddenly can't connect, support disappears, money won't refund. We did a few things others don't…" (CN, peer-to-peer; never opens with capital letter in chat)
>
> "Self-hosted apps, without the self-hosting." (EN headline; sentence-case display serif)
>
> "We target 99.9% monthly uptime for managed instances. We do not offer a contractual SLA at the current scale — we'd rather be honest about being a small operation than promise enterprise guarantees we can't keep." (EN FAQ; the *we'd rather* clause is the voice signature)

### What the voice **never** does
- "Cutting-edge", "world-class", "best-in-class", "AI-powered" — banned hyperbole.
- "Solutions" used as a noun. We say "tools", "software", "service".
- "Reach out" — we say "email", "talk to us".
- 100% guarantees of any kind.
- Compares itself to a Genshin character. The character connection is *inspiration*, never *claim*.

---

## VISUAL FOUNDATIONS

### Color
- **Primary brand:** teal `#3a9188` (deep `#2d736b`, soft `#5bc0be`).
- **Secondary:** gold `#c9a253` (soft `#efe1bf`) — used as a punctuation color: eyebrow underlines, plan-highlight pill background, status dots, divider arabesque tint.
- **Anchor:** navy `#1e3a5f` (deep `#142940`) for headings, footer, dark surfaces.
- **Surface:** cream `#faf6ee` and warm cream `#f5ecdc` instead of pure grey. White (`#ffffff`) is used for cards and elevated surfaces, never as the page background hero. The hero uses a *radial cream wash*: `radial-gradient(ellipse 80% 60% at 50% 0%, var(--brand-cream-warm) 0%, transparent 60%)`.
- **Status:** emerald (online), amber (warning/trial), coral (offline). Distinct from primary teal.

### Type
- **Display:** Cormorant Garamond (Medium 500 + Italic 400) — h1, h2, prices, brand wordmark in footer. Letter-spacing is tightened (`-0.025em` to `-0.02em`).
- **UI / body:** Inter (300/400/500/600/700). 1rem base, line-height 1.65 for body / 1.78 for prose.
- **Mono:** JetBrains Mono — code, IPs, hashes, hex tokens.
- **CJK:** Noto Serif SC/JP for display, Noto Sans / PingFang / Source Han for body.
- The signature move is `<h1>Self-hosted apps, <em class="accent">without the self-hosting.</em></h1>` — display serif in roman + italic in teal on the second line.

### Spacing
- 8pt grid via `--s-1 (4px)` … `--s-11 (160px)`. Sections pad `--s-9 (96px)` vertical; cards pad `--s-6 (32px)`.

### Radii
Modest, never pill-rounded: `--r-sm 4px`, `--r-md 6px`, `--r-lg 10px`, `--r-xl 14px`. Pills (`999px`) are reserved for plan tags, status dots, and the eyebrow chip.

### Shadows
Three-stop, **navy-tinted, low-opacity** (4–8% alpha):
- `--shadow-sm`: 0 1px 2px rgba(20,41,64,.04), 0 1px 3px rgba(20,41,64,.06)
- `--shadow-md`: 0 4px 6px rgba(20,41,64,.04), 0 10px 15px rgba(20,41,64,.05)
- `--shadow-lg`: 0 10px 25px rgba(20,41,64,.08), 0 20px 40px rgba(20,41,64,.06)
- Glow: `--shadow-glow-teal` for emphasis on focus / hover of teal CTAs.

### Borders
Hairline, warm-cream, **never grey**: `--border #e8dfca`, `--border-soft #f0e6d3`. Cards use `1px solid var(--border-soft)` and shift to `border-color: var(--brand-teal-soft)` on hover.

### Backgrounds & motifs
- **Radial cream wash** at hero top.
- **Arabesque divider strip** — `assets/pattern-arabesque.svg` repeated horizontally at 64px tall, opacity 0.4, gold-tinted via `color: var(--brand-gold)` (the SVG uses currentColor). Used between sections.
- **Lotus mark** — `assets/lotus.svg` (8-petal radial bezier) — used as hero brand mark. Animates with a 7s `lotus-breathe` (subtle scale 1→1.05 + 3deg rotate).
- **Water ripples** — concentric SVG circles, two large blobs floating in the hero corners. 16s + 22s `ripple-float` keyframes (translate ±24px, scale 1.04, opacity 0.4 ↔ 0.5).
- **No gradients** as primary backgrounds. The exceptions: cream→cream-warm vertical gradient for `pricing` and `contact` sections, and `linear-gradient(135deg, rgba(91,192,190,0.12), rgba(201,162,83,0.10))` for hover-state cards.
- **No full-bleed photography.** The single hero image is a screenshot of the dashboard.
- **No grain, no noise textures.**

### Animation
- Default transition `--t-base: 0.18s cubic-bezier(0.4, 0, 0.2, 1)` — quick, decisive.
- Reveal: `--t-reveal: 0.6s cubic-bezier(0.16, 1, 0.3, 1)` — used by the `IntersectionObserver` `.scroll-reveal` (translateY 16px → 0, opacity 0 → 1, with stagger via `--i` index).
- Spring: `--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)` for playful one-shots.
- Status dot pulses with a 2.4s `status-pulse`.
- All animations respect `prefers-reduced-motion`. No bouncy hovers, no parallax, no auto-playing video.

### Hover & press states
- **Buttons:** primary teal → teal-deep on hover, +1px translate-y up, shadow grows sm → md. Press: same, no extra shrink. No color shift on press (relies on translate).
- **Cards:** `transform: translateY(-2px)` + shadow grows + border shifts to `var(--brand-teal-soft)`. Plans get `-3px` and `--shadow-lg`.
- **Links:** body links use `var(--brand-teal-deep)` for AA contrast (5.7:1 on cream); hover → no underline change, just color deepens.
- **Focus:** `outline: 2px solid var(--brand-teal); outline-offset: 3px;` — never removed.

### Transparency & blur
- Sticky topbar uses `backdrop-filter: saturate(180%) blur(14px)` over `rgba(255,255,255,0.88)` — only place blur is used.
- Eyebrow chip uses `rgba(201,162,83,0.10)` gold tint.

### Cards
1px hairline border, `--r-lg (10px)` corners, `--shadow-sm` resting, `--shadow-md` on hover. Inner padding `--s-6 var(--s-5)`. Headers are `t-h3` (Inter 600 1.08rem). The *plan-highlight* variant gets a teal border + cream inner gradient + a gold pill tag overlapping the top edge.

### Layout rules
- Container max-width `1180px`, gutter `--s-5`.
- Topbar: sticky, `position: sticky; top: 0; z-index: 50`. 56px tall on mobile.
- Hero is 2-column ≥980px (text + dashboard mockup), single-column below. Hero pads `--s-10` top, `--s-9` bottom.
- Feature grid: `repeat(auto-fit, minmax(290px, 1fr))`.
- Plan grid: `repeat(auto-fit, minmax(245px, 1fr))`.
- Footer: 4-column ≥880px, 2-column 480–880, 1-column below.

---

## ICONOGRAPHY

### Approach
The brand uses **inline SVGs only** — no icon font, no icon library dependency, no PNG icons in UI. Stroke is `1.5–1.6px`, `stroke-linecap="round"`, `stroke-linejoin="round"`, `currentColor` everywhere so a single `color:` rule themes the icon.

The **feature icons** (`assets/icons/feat-1.svg` … `feat-6.svg`) are 6 hand-rolled 24×24 line glyphs from the production landing — managed-instance dial, mail envelope with chevron, shield with check, user-with-link, multi-region globe, transparent-pricing pyramid. They are the canonical icon set; new icons should match their stroke weight and roundness.

The **lotus mark** (`assets/lotus.svg`) is the primary brand glyph — 8 petals as bezier paths rotated 0/45/90/…/315°, 1.5px stroke, with two centered concentric circles (small filled, larger stroked). Used at 84px in the hero, 30px in the topbar, 64px on mobile, 16px as favicon.

The **arabesque pattern** (`assets/pattern-arabesque.svg`) is a horizontally-repeating Persian arabesque used for section dividers — 64px tall, gold-tinted via currentColor, 40% opacity.

### Iconography rules
- **Stroke icons only.** No filled bowl-and-spoon glyphs. No duotone.
- **Stroke weight 1.5–1.6px** at 24×24. Scale up by viewBox, not by stroke.
- **No emoji in product UI.** Pitch-card emoji (✅, 🇯🇵, 🪷) are CN-marketing-only.
- **No unicode glyphs as icons** (✓ is used inside plan list bullets via CSS `content: "✓"` colored teal — that's the only allowed exception).
- **No FontAwesome / Lucide / Heroicons** unless the codebase already pulls them. The Aegis dashboard uses **lucide-react** internally (per `package.json`), so dashboard recreations may use Lucide; the **marketing brand uses inline SVG**.

### What's in `assets/`
- `lotus.svg` — primary brand mark (currentColor)
- `pattern-arabesque.svg` — section divider strip (currentColor)
- `icons/feat-1.svg` … `feat-6.svg` — six feature glyphs (currentColor)
- `hero-dashboard-v3.png` — hero screenshot (the dashboard, framed)
- `project-icon.png` — Marzneshin project icon (used inside dashboard)

---

## Substitutions / Caveats
- **Fonts** are loaded from Google Fonts (`Cormorant Garamond`, `Inter`, `JetBrains Mono`). No local TTF/WOFF was shipped in the repo — the production landing imports from `fonts.googleapis.com`. If you need offline assets, please drop the WOFF2 files into `fonts/` and re-export.
- The brand book lists `--brand-gold: #F4E5C2` but production CSS uses `#c9a253` (deeper, AA-passing on cream). **We follow production.** The lighter `#efe1bf` from the book is preserved as `--brand-gold-soft`.
- **Dashboard fonts** (Lato + Ubuntu, per `tailwind.config.js`) are documented but not adopted — the canonical brand uses Cormorant + Inter. If you specifically mock the dashboard, swap the font stack accordingly.
