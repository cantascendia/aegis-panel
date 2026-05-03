# Nilou Network Marketing Site

Static marketing pages for `nilou.network`.

## Scope

- Pure static HTML and CSS.
- No package dependency, no build step, no client-side telemetry.
- Language versions:
  - `/en/`
  - `/ja/`
  - `/zh/`
- Shared legal disclosure page:
  - `/legal.html`

## Positioning

Nilou Network is presented as a general managed cloud operations service for application stacks, similar in category to small-team SaaS hosting and operations products.

Avoid regulated or sensitive infrastructure language in marketing copy. The site must not use terms related to traffic tunneling, censorship circumvention, hidden routing, or product names from the parent application.

## Design

The visual system uses original blue-lotus, water, and dance-stage motifs. It does not include third-party character artwork or copyrighted game assets.

## Deployment

Cloudflare Pages configuration:

- Production branch: `main`
- Framework preset: none
- Build command: empty
- Build output directory: `marketing/nilou-network`
- Root directory: repository root

Static headers live in `_headers`.

## Manual Checks

Before publishing:

- Open `/en/`, `/ja/`, `/zh/`, and `/legal.html`.
- Confirm all pages return HTTP 200.
- Confirm legal placeholders are replaced before public launch.
- Confirm no remote font, script, or image dependency is introduced.
- Confirm copy remains generic SaaS hosting and operations copy.
