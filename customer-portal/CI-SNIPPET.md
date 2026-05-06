# CI smoke-build snippet — for operator to drop into `.github/workflows/`

**Why this is a separate file**: `.github/workflows/**` is in `.claude/rules/forbidden-paths.md` and requires the §32.1 double-sign workflow. AI agents must not write workflow files directly. After review + double-sign, copy the snippet below to `.github/workflows/customer-portal-ci.yml` and delete this file.

> Source: harness-auditor wave-11 R2 audit (improvement #2, +3 score on Principle 8 — Durable State + Validation Gates).

---

## Snippet

```yaml
name: Customer Portal CI

on:
  push:
    branches: [ "master" ]
    paths:
      - "customer-portal/**"
  pull_request:
    branches: [ "master" ]
    paths:
      - "customer-portal/**"

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./customer-portal
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v3
        name: Install pnpm
        with:
          version: 10
          run_install: false

      - name: Get pnpm store directory
        shell: bash
        run: |
          echo "STORE_PATH=$(pnpm store path --silent)" >> $GITHUB_ENV

      - uses: actions/cache@v3
        name: Setup pnpm cache
        with:
          path: ${{ env.STORE_PATH }}
          key: ${{ runner.os }}-pnpm-portal-${{ hashFiles('customer-portal/pnpm-lock.yaml') }}
          restore-keys: |
            ${{ runner.os }}-pnpm-portal-

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build

      - name: Verify dist size budget (< 500 KB)
        run: |
          DIST_SIZE=$(du -sb dist | cut -f1)
          MAX_SIZE=$((500 * 1024))
          echo "dist size: $DIST_SIZE bytes (budget: $MAX_SIZE)"
          if [ "$DIST_SIZE" -gt "$MAX_SIZE" ]; then
            echo "::error::customer-portal/dist exceeds 500 KB budget"
            exit 1
          fi
```

---

## Why these specifics

| Choice | Reason |
|---|---|
| Trigger only on `customer-portal/**` paths | Avoid running on every dashboard / app PR |
| pnpm v10 (not v9 like dashboard-ci.yml) | Match `customer-portal/` lockfile producer (current local pnpm 10.33.0) |
| `pnpm install --frozen-lockfile` | Catch lockfile drift |
| dist size budget 500 KB | Current build is 236 KB (P1) — leave headroom for P2 i18n strings + auth wiring; alarm if portal bloats |
| No lint / test step yet | P1 has no lint config or test suite; add when P2 introduces them |

## Acceptance

After workflow lands, PR #240 will get a new `Customer Portal CI` check next to the existing `eval-gate`, `Chromatic Deploy`, etc. — closes auditor improvement #2.
