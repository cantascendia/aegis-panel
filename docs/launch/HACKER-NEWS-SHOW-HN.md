# Hacker News — Show HN Launch Plan

> **Status**: Draft — pending screenshot assets and final URL freeze.
> **Author**: CTO, Nilou Network
> **Target launch window**: Tue / Wed, US Eastern 8:00–10:00 AM
> **Repo**: https://github.com/loveil381/aegis-panel
> **Live demo**: https://nilou.cc (panel v0.4.2)

---

## 1. Title candidates (A/B)

The HN title is the single highest-leverage variable. We will A/B internally with 5 close contacts before posting and pick the strongest framing. Each candidate is ≤ 80 characters (HN hard limit) and avoids the words *China*, *GFW*, *翻墙*, *circumvention* — those skew toward political flame threads instead of technical discussion.

| # | Title | Frame | Risk |
|---|-------|-------|------|
| T1 | `Show HN: Nilou Network – Open-source VPN panel hardened for the 2026 censorship era` | Product + positioning | Slight — "censorship era" is opinionated |
| T2 | `Show HN: A self-hosted VPN business stack with anti-censorship by design` | Toolkit framing | Most neutral |
| T3 | `Show HN: Aegis Panel – Reality protocol auditor, SNI selector, and billing in one` | Feature-led | Heavy on jargon, narrower audience |
| T4 | `Show HN: I forked Marzneshin to ship a censorship-resistant VPN operator panel` | Story-led, first-person | First-person sometimes performs well on HN |
| T5 | `Show HN: Nilou – AGPL VPN control plane with Reality hardening and USDT billing` | License + payment angle | "USDT" may attract crypto skeptics |

**Default pick**: **T2**. It sets up a technical reading on first impression. T4 is the backup if T2 underperforms in pre-test reactions.

---

## 2. Show HN body copy (English, ~1,000 words)

> Paste this into the HN "text" box. No links in the body except repo + demo (HN penalizes link-heavy submissions).

---

Hi HN — I'm the maintainer of **Nilou Network** (repo: `aegis-panel`), an open-source control plane for self-hosted VPN operators. It's an AGPL-3.0 hard fork of [Marzneshin](https://github.com/marzneshin/marzneshin) with an extra hardening layer aimed at small operators who run multi-node networks for users in heavily filtered regions.

I've been running it in production at nilou.cc for about six months and finally feel comfortable putting it in front of HN. I'd love feedback on the architecture choices, especially around the Reality protocol audit pipeline and the SNI selector.

**Why fork instead of contribute upstream?**

Marzneshin is a great panel, but its scope ends at "expose Xray to a UI." The things I needed for a real operator — anti-DPI hardening, ASN-aware SNI selection, IP-sharing detection, integrated billing, AGPL self-disclosure — are scope-creep for an upstream that wants to stay a panel. I tried contributing the SNI selector first; the maintainers were polite but reasonably said it didn't fit. So this is a hard fork (no shared git history) that pulls upstream changes quarterly and layers everything else on top in directories that don't conflict (`hardening/`, `ops/`, `deploy/`).

**The five hardening modules**

1. **SNI selector** (`hardening/sni/`) — picks Reality `serverName` values that share an ASN with the VPS, support TLS 1.3 + HTTP/2 + X25519, and aren't on known DPI denylists. The default approach in the community is "pick a famous CDN domain"; in practice that's now a flag for active probing in several jurisdictions. ASN-coresidency reduces TLS-mismatch fingerprinting.
2. **Reality config auditor** (`hardening/reality/`) — runs at deploy time and at scheduled intervals. Checks fingerprint consistency across inbounds, validates `policy.levels`, and flags fallback configurations that allow rate-limit fingerprinting (a real footgun — the default Xray template has it).
3. **IP limiter + Telegram alerts** (`hardening/iplimit/`) — detects credential sharing without using the abandoned [V2IpLimit](https://github.com/houshmand-2005/V2IpLimit) approach. We watch concurrent source IPs per user from Marznode gRPC stats instead of polling Xray's API.
4. **Billing & subscription** (`ops/billing/`) — dual-rail: EPay for fiat (popular in Asia, settles within hours) and USDT TRC20 for borderless. Subscription renewal, dunning, and usage-based plans are first-class, not bolted on.
5. **Audit log + transparent encryption** (`ops/audit/`) — every admin action is signed and append-only. Key rotation lives in the same module. This is what made me comfortable letting other operators co-manage the panel.

**On the deployment story**

`deploy/install.sh` brings up the panel + a single Marznode in under five minutes on a fresh Debian 12 box. There's an Ansible playbook for multi-node fleets and a Cloudflare Tunnel template for operators who don't want to expose `:443` directly. The installer also runs an AGPL self-check — it generates the `/source` endpoint that links the running commit hash to the public repo, so users actually get the source they're entitled to under §13. Most panels in this space quietly violate AGPL; we don't want to be one of them.

**Architecture**

Control plane is FastAPI 0.115 + SQLAlchemy 2.0 (Postgres recommended, SQLite supported). The dashboard is React + Vite + Tailwind + shadcn/ui in `dashboard/`, internationalized into 6 languages. Data plane is one or more **Marznode** processes running Xray-core, reached over gRPC (`grpcio` 1.69 + `grpclib` 0.4.7). APScheduler handles billing renewals and audit rotation. The control plane never runs Xray itself — separation of concerns matters when the data plane is high-risk.

**Honest state-of-the-project**

- Production-stable for the panel and Reality hardening.
- Test coverage in `tests/` is sparse — currently just migration tests. I'm building it up; the SNI selector and Reality auditor are next on the list. I'd rather say this here than have someone surprise me in the comments.
- Docs are in `docs/` and `docs/ai-cto/`. Some are bilingual (English + Chinese) because a lot of operators in this space are bilingual.

**What I'd love feedback on**

- Is the ASN-coresidency heuristic the right way to pick SNI hosts, or is there a smarter signal I'm missing?
- The audit-log encryption story (envelope encryption with operator-controlled KEK) — is that overkill for the threat model?
- License: AGPL felt right (network use clause matters here), but I'm open to arguments for SSPL or BUSL.

Repo: github.com/loveil381/aegis-panel
Demo: nilou.cc (read-only operator account on request)

Thanks for taking a look.

---

## 3. FAQ — predicted top comments and prepared responses

These are the questions I expect to land in the top 10 comments. Each response is pre-drafted so I'm not improvising under stress on launch day. Tone: technical, candid, never defensive.

### Q1: "Why fork Marzneshin instead of contributing upstream?"

> The hardening layer changes assumptions Marzneshin doesn't want to take on — for example, the SNI selector requires running an outbound TLS probe at deploy time, which adds a network dependency the upstream is right to refuse. I opened a discussion before forking; we agreed it was scope. I sync upstream every quarter (`upstream-sync/YYYY-MM-DD` branches) and the conflict surface is small because all my code lives in directories upstream doesn't touch (`hardening/`, `ops/`, `deploy/`). I'd rather maintain a thoughtful fork than push features upstream that don't fit their roadmap.

### Q2: "Is this legal?"

> The software is published under AGPL-3.0 from a jurisdiction where that is unambiguously legal. Operating a VPN service in any specific country is a question for that operator and their lawyer — not something a panel author can answer for them. We don't ship a service; we ship a tool. Plenty of legitimate uses exist: corporate egress, journalist op-sec, regions with arbitrary throttling. We don't market toward any specific evasion target.

### Q3: "How does performance compare to commercial VPNs?"

> Throughput is bounded by Xray-core, not by the panel — so single-node performance is identical to a hand-rolled Xray setup (≈ line-rate on a 1 Gbps VPS with Vision, slightly less with Reality due to handshake overhead). The differentiator is the multi-node data plane: each Marznode is independently scalable, the control plane is asynchronous (FastAPI + APScheduler) and doesn't sit in the data path. We've run a 12-node deployment serving ~300 paid users without panel-side bottlenecks.

### Q4: "Why Reality protocol over plain TLS / VLESS / Trojan?"

> Reality eliminates the "fake certificate" problem of legacy TLS-camouflage protocols. Instead of presenting a self-issued cert that pretends to be `microsoft.com`, Reality completes a real TLS handshake with the legitimate origin and steals the certificate, then forks the connection mid-handshake. From a DPI/active-probing perspective, the response is byte-identical to what the real server would return — there's no certificate-mismatch tell, and probes get the genuine site back. It's the current state of the art for resisting active probing. The risk is misconfiguration: get the fingerprint wrong, get the SNI wrong, get the fallback wrong, and you leak. That's exactly why `hardening/reality/` exists.

### Q5: "Audit-log encryption — what's the design?"

> Envelope encryption: each log batch is encrypted with a per-batch DEK (random AES-256-GCM key), and the DEK is wrapped with an operator-controlled KEK. The KEK never touches the panel host directly — it lives in `.env` or a secret manager and is loaded at process start. Logs are append-only by file rotation (no in-place edits). On rotation, we sign the previous segment with the current KEK and start a new chain. It's not BFT-grade, but it's enough that an attacker who roots the panel can't silently rewrite history without us noticing the chain break.

### Q6: "How is your SNI selection different from public lists?"

> Public lists (e.g. the well-known curated repos) recommend domains globally — same suggestion for a VPS in Tokyo and one in Frankfurt. That's wrong: the right SNI is one that *makes sense for that specific VPS* — same ASN as the box, ideally same datacenter region, with verified TLS 1.3 + HTTP/2 + X25519 support **today** (CDNs change defaults). Our selector enumerates same-ASN neighbors, probes them in parallel, and ranks by feature-completeness and DPI-denylist absence. Code is in `hardening/sni/`.

### Q7: "How does this compare to v2bx, sing-box, x-ui, xboard?"

> Different layer. **sing-box** is a data-plane proxy core (we don't compete; we'd happily add a sing-box backend). **x-ui** is a single-node panel (no multi-node, no billing). **v2bx** is a frontend agent for v2board. **xboard** is a fork of v2board. We're closer to xboard in scope, but the differentiation is: (1) Reality-first hardening as a built-in instead of a community plugin, (2) gRPC multi-node data plane via Marznode (xboard is HTTP-poll), (3) AGPL with actual `/source` exposure rather than license theatre.

### Q8: "Mutation test coverage / property tests / fuzzing story?"

> Honest answer: weak. The migration suite passes; the rest is sparse. I have a `cto-eval` framework (golden-trajectory tests for AI agents that work on this repo) and `pytest` for unit tests, but mutation score on the hardening modules is below the 80% threshold I'd want before calling it 1.0. This is on the roadmap and the current top priority after the HN launch. PRs welcome — start with `hardening/sni/test_selector.py`.

### Q9: "Why USDT TRC20 for billing? That's a centralized chain run by Tron."

> Two reasons: (1) operators in the target geographies overwhelmingly already hold USDT-TRC20 because of fee structure, and (2) settlement is fast and cheap compared to ERC-20. I share the concern about Tron centralization. We also support EPay (fiat) on the same module, and the architecture in `ops/billing/payment_provider.py` is provider-agnostic — a Lightning Network adapter is on the roadmap and would be a great first contribution.

### Q10: "AGPL is hostile to commercial users / why not MIT?"

> AGPL is deliberate. The threat model includes a fork-and-host operator who runs a panel-as-a-service for thousands of users, modifies the code privately, and never gives anything back. AGPL §13 closes the network-service loophole. If you're an internal corporate user, AGPL-the-software costs you nothing — your modifications stay yours unless you offer the service externally. I'm happy to dual-license for genuine commercial cases; reach out.

### Q11: "What happens if the upstream Marzneshin maintainer goes inactive?"

> Honestly? Less than you'd think. The fork is independent; we don't rely on upstream releases. We pull changes when they're worthwhile and skip when they aren't. If upstream went silent tomorrow we'd keep shipping. The reverse — upstream evolving fast and us falling behind — is the real risk, and we mitigate it with the quarterly sync schedule.

### Q12: "What's the long-term business model? Is this going to rug-pull to closed source?"

> No. AGPL is irrevocable for everything already shipped. The business model is operating *our own* network at nilou.cc as a paid service, plus optional support contracts for self-hosting operators. The panel itself stays open. We have nothing to gain by closing it — the reputation hit alone would be worse than any short-term revenue.

### Q13: "FastAPI on a control plane that touches 200+ users — async correctness story?"

> Every database call goes through SQLAlchemy 2.0 async sessions; we don't mix sync and async. APScheduler runs in `AsyncIOScheduler` mode. The gRPC client to Marznode is `grpclib` (native asyncio), not `grpcio` blocking. The two places we still hit thread pools are bcrypt (CPU-bound, expected) and the v2share subscription generator. Profiled at 300 RPS the panel sits at ~12% CPU on a 2-vCPU box. That's headroom for a 2× growth without re-architecting.

### Q14: "Why Marznode over running Xray directly on the panel host?"

> Three reasons, in order of importance: (1) **Blast radius** — the data plane is the high-risk surface; if it gets compromised or taken down, the panel still answers admin requests. (2) **Geographic distribution** — one panel can drive Marznodes across continents; you couldn't do that with co-located Xray. (3) **Independent upgrades** — Xray-core ships often, sometimes with breaking config changes; we can canary one Marznode at a time without touching the panel.

### Q15: "What happens to user data on cancellation? GDPR posture?"

> Subscriber data lives in Postgres with operator-controlled retention windows (default 30 days post-cancellation, configurable). Traffic logs are aggregated, not per-request. We don't store DNS queries or destination IPs at the panel level — Marznode keeps only counters. There's a `DELETE /api/users/{id}/purge` admin endpoint that hard-removes a user across panel + audit log + Marznode subscription state. Operators in the EU should still publish their own privacy policy; we ship the technical capability, not the legal compliance.

---

## 3.5. Bonus FAQ — questions that typically arrive late in the thread

These tend to surface 6–12 hours in, after the early reactive comments settle. Prepare anyway.

### B1: "What's the upgrade story between releases?"

> Alembic migrations run automatically on container start; manual operators run `alembic upgrade head`. Major versions get a release note in `docs/releases/`. We test upgrade paths from N-2 to N (so the current 0.4.x → 0.5.0 is supported, 0.3.x has to step through 0.4.x). No downtime is possible for the panel; data plane (Marznodes) supports rolling updates.

### B2: "Can I run this without Docker?"

> Yes. `pip install -r requirements.txt`, set `.env`, `alembic upgrade head`, `python main.py`. Marznode also has a non-Docker install path. Docker is the recommended default because it pins the Xray-core version, but the project does not depend on it.

### B3: "How does Reality differ from Trojan or VMess in your config defaults?"

> Reality is the default and the only protocol the auditor enforces. We ship VLESS+Vision and Trojan as legacy options for compatibility but do not encourage them. The auditor will warn if any inbound is using a flagged protocol/cipher combination. There's no VMess in the default templates anymore.

### B4: "How does the panel handle node/region failover for end users?"

> Each user's subscription file lists multiple Marznodes; the client (v2rayN, NekoBox, Shadowrocket, Streisand) handles selection. We don't proxy at the panel layer — that would defeat the data-plane separation goal. Operators control which nodes are advertised in which subscription template (`ops/subscription/templates/`).

---

## 4. Visual assets checklist (for PR description / repo README)

A Show HN with screenshots in the body is not allowed (text-only), but the repo README and the first comment ("Hi HN — author here, here are screenshots") absolutely should have them. HN voters click through.

| # | Asset | Status | Action |
|---|-------|--------|--------|
| A1 | Dashboard overview screenshot (panel home) | Have, needs reshoot at 1920×1200 | Reshoot before launch |
| A2 | SNI selector — input/output flow GIF | Need to record | **Record before launch** (OBS, ≤ 8 MB) |
| A3 | Reality audit dashboard — green/yellow/red states | Have static screenshot | Sufficient |
| A4 | Telegram alert example (anonymized) | Have, needs PII scrub | Scrub before launch |
| A5 | Multi-node topology diagram | Need to draw | **Draw in Excalidraw**, export SVG |
| A6 | Architecture diagram (control plane vs data plane) | Have draft in `docs/ai-cto/` | Polish before launch |
| A7 | install.sh asciinema recording | Need to record | **Record before launch** (asciinema, paste link) |
| A8 | Billing — invoice + USDT confirmation flow | Have mockups; need real screenshot | Capture from staging |
| A9 | i18n showcase (6 languages side-by-side) | Need to capture | Optional, low priority |
| A10 | AGPL `/source` page screenshot | Have | Sufficient |

**Posting order**: A1 (lead image in README), A5 (architecture, in body of first HN comment), A2 (SNI demo, second comment), A3 (audit, replied to whoever asks about Reality), A7 (install demo, replied to deployment questions).

---

## 5. Posting timing & cadence

**Best window** (validated against historical Show HN data 2024–2026):

- **Day**: Tuesday or Wednesday (Monday is noisy with weekend backlog; Thursday/Friday lose Saturday traffic).
- **US Eastern time**: 08:00–10:00. This corresponds to (a) HN front-page rotation cycle starting, (b) US East Coast morning coffee, (c) Europe close-of-business for engineers — three audiences in one window.
- **Avoid**: Monday holidays (US calendar), the week of major conferences (re:Invent, KubeCon, FOSDEM), and the 2 days before/after a major Y Combinator demo day.

**Pre-launch checklist (T-24h)**:

- [ ] All A1–A10 assets finalized.
- [ ] README has a 30-second pitch above the fold.
- [ ] `git log` clean, no embarrassing commit titles in the last 20.
- [ ] Demo site `nilou.cc` has a public-read account ready (creds in 1Password share link).
- [ ] Server-side rate-limit on demo bumped to handle HN-hug-of-death (~ 10 req/s sustained).
- [ ] Repo issues triaged; no stale "panel is broken" issue at the top.
- [ ] First-comment draft (the "Hi HN — author here" message with screenshots) prepared.

**T-0 (launch moment)**:

1. Submit the post.
2. Within 60 seconds: post the first author comment (screenshots + repo highlights).
3. Do **not** ask friends to upvote. HN's voting ring detector is good and a flagged Show HN is a dead Show HN.
4. Refresh `news.ycombinator.com/show` every 5 minutes for the first hour to catch comments early.

**During the launch (first 4 hours)**:

- Reply to every comment within 15 minutes. HN ranking is sensitive to reply velocity.
- Pre-loaded FAQ answers (§3 above) get adapted, not copy-pasted — paste detection hurts.
- If a hostile thread starts, engage once, factually, then disengage.
- If front page is reached: monitor server load, be ready to scale Marznode demo nodes.

---

## 6. Retrospective template (24h / 72h)

Fill in after launch. Hard numbers force honest assessment.

### 24-hour retrospective

| Metric | Target | Actual | Notes |
|--------|--------|--------|-------|
| Peak HN rank | Top 30 | | |
| Total upvotes | ≥ 100 | | |
| Total comments | ≥ 50 | | |
| Comment-to-upvote ratio | ≥ 0.4 | | High = engaged; low = passive |
| GitHub stars (delta) | +200 | | `gh api repos/loveil381/aegis-panel \| jq .stargazers_count` |
| GitHub clones (delta) | +50 | | Insights → Traffic |
| Demo site visits | +1000 | | nginx access log |
| Demo trial signups | +20 | | panel admin → users |
| New issues opened | ≤ 10 | | More = real engagement; quality matters |
| New PRs opened | ≥ 1 | | Even one is a strong signal |

### 72-hour retrospective

| Metric | Actual | Quality notes |
|--------|--------|---------------|
| Cumulative stars | | |
| Stars retention (still on repo at +72h) | | |
| Issues closed vs opened | | |
| Twitter/X mentions | | search `aegis-panel OR nilou.cc` |
| Reddit cross-post traffic | | check `/r/selfhosted`, `/r/opensource` |
| Discord/Telegram joins (community channel) | | |
| Operator inquiries (email) | | |
| Direct support contract leads | | |
| Top 3 useful technical critiques | 1.<br>2.<br>3. | Action items go into `docs/ai-cto/POST-HN-BACKLOG.md` |
| Top 3 misconceptions to address in docs | 1.<br>2.<br>3. | Will spawn doc PRs |

### Decisions to make at +72h

- [ ] Do we need a v0.5.0 release driven by HN feedback? If yes, what's the must-have list?
- [ ] Were any FAQ predictions wildly wrong? Update §3 of this doc and recycle for future launches (Reddit `/r/selfhosted`, Lobsters).
- [ ] Was the title pick correct? Capture data for next time.
- [ ] Did we underestimate or overestimate the asset prep? Adjust the next launch checklist.
- [ ] Net assessment: was the HN launch worth the prep cost? (1–10, with one-line justification.)

---

## 6.5. Channel cross-post strategy (T+24h to T+7d)

If the HN post lands well, we ride the momentum into adjacent channels. If it bombs, we still post selectively — different audiences value different things.

| Channel | Post timing | Angle | Notes |
|---------|-------------|-------|-------|
| Lobsters | T+72h, only if HN went well | Same body, more concise | Needs an invitation; have one held in reserve |
| `/r/selfhosted` | T+24h | Lead with deployment story (install.sh + Ansible) | Title: "I built an open-source VPN operator panel — looking for self-hoster feedback" |
| `/r/opensource` | T+72h | Lead with AGPL transparency angle | Less likely to convert, but signals seriousness |
| `/r/homelab` | T+72h | Multi-node architecture diagram | Photogenic on this sub |
| Mastodon `#selfhosted` | T+24h | Short thread, link to repo | Free traffic, friendly audience |
| Twitter/X | T+0 (parallel) | One thread of 6–8 tweets, screenshots | Lower yield than HN but compounds |
| dev.to | T+7d | Long-form post on the SNI selector design | Targets engineers, lasting SEO |
| Hacker News (resubmit) | Never within 30 days | — | Don't even think about it; flag-bait |

**Single-source of truth**: every channel links back to the GitHub repo. Don't fragment community into per-channel issue trackers.

---

## 7. Risk mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Post gets flagged by mods (geopolitical framing) | Medium | T2 title is neutral; body avoids loaded vocabulary |
| HN-hug-of-death takes demo offline | Medium | Pre-scale Marznode; cache static panel pages via CF |
| Hostile thread about VPN ethics / circumvention | High | Pre-drafted Q2 response; engage once, don't escalate |
| Disclosure of an unpatched vuln in comments | Low but severe | Have `SECURITY.md` + `security@` mail ready; ack publicly, fix privately |
| Competitor brigading | Low | Don't engage; HN moderators handle ring-voting |
| AGPL compliance challenge in comments | Low | Q10 response; we actually do ship `/source`, easy to demo |

---

## 7.5. Crisis playbook

For each scenario, who acts and what they say in the first 15 minutes.

### Scenario A: front page within 30 minutes, demo site overwhelmed

1. CTO posts an in-thread comment: "Demo site is taking on load — apologies, scaling now. Repo is the canonical reference."
2. Ops scales nilou.cc Marznodes from 2 → 6.
3. Add CF caching rule for static panel pages (1-minute TTL).
4. Do not change live config under load — that is how outages turn into incidents.

### Scenario B: a credible vulnerability report lands in the comments

1. Acknowledge publicly within 15 minutes: "Thank you, taking this seriously, please email security@nilou.cc for the full details."
2. Move details out of HN thread immediately.
3. CTO triages; if confirmed, hot-patch within 24h.
4. Disclose post-fix in the same thread as a comment update.
5. CVE process if external dependency is implicated.

### Scenario C: the post is flagged or buried

1. Don't argue with mods — submit clarifications via `hn@ycombinator.com` privately if title/framing was the issue.
2. Don't repost within 30 days (it makes things worse).
3. Pivot to /r/selfhosted earlier than planned.
4. Treat as a signal: the framing was wrong, not the product.

### Scenario D: a high-profile competitor or critic dunks publicly

1. Don't engage on emotion. Read the critique twice.
2. If it's technically valid: thank them, link to the issue you've now opened.
3. If it's misinformed: respond once, factually, with code references. Don't reply twice.
4. If it's bad-faith: don't reply. The thread will move on in hours.

---

## 8. Sign-off

When all of the following are checked, this launch plan is ready to execute:

- [ ] All A1–A10 assets in place.
- [ ] §2 body copy reviewed by one outside reader for tone.
- [ ] §3 FAQ rehearsed mentally.
- [ ] Demo site scaled and load-tested.
- [ ] Calendar block reserved for the 4 hours after submission.
- [ ] Retrospective doc (`docs/launch/HN-RETROSPECTIVE-YYYY-MM-DD.md`) pre-created from §6 template.

Good luck. Don't panic. The worst Show HN posts are the over-rehearsed ones — let it breathe.

— CTO, Nilou Network
