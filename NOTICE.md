# NOTICE

This project is a hard fork (detached source copy) of **Marzneshin** by the
[Marzneshin organization](https://github.com/marzneshin/marzneshin), licensed
under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Marzneshin is itself the official successor to Gozargah/Marzban and shares
lineage with the upstream Marzban codebase. All copyright notices from both
upstreams are preserved.

## Upstream Attribution

- **Direct upstream**: https://github.com/marzneshin/marzneshin
- **Forked at commit**: `d3b25e23c4977c63eacc6aca591e0cdf0c2bcd68`
- **Forked on (UTC)**: 2026-04-21
- **Upstream commit date**: 2025-10-02
- **Lineage upstream**: https://github.com/Gozargah/Marzban (original, AGPL-3.0,
  last activity 2025-01-09; Marzneshin is the active successor)

## Source (this fork)

- **Source code URL**: https://github.com/cantascendia/aegis-panel

This URL satisfies AGPL-3.0 §13 source-disclosure for users interacting with
this panel over a network. The deployed panel surfaces it via UI footer and
the `GET /api/system/info` response (`source_code_url` field). The
`deploy/compliance/agpl-selfcheck.sh` script verifies both surfaces at install
time; it reads this URL by parsing the line above (canonical-extraction
contract — keep the line shape `**Source code URL**: <url>`).

All copyright notices, license files (`LICENSE`), and author attributions
contained in the upstream source files are preserved and must remain preserved
in this fork and any subsequent derivative works.

## Why This Fork Exists

This fork adds a **Reality 2026 hardening & commercial operations layer** on
top of Marzneshin, targeting operators running >200-user paid deployments with
multi-node fault tolerance. The hardening spec is captured in
`compass_artifact_*.md` and distilled into `docs/ai-cto/VISION.md`.

Our additions are kept in separate top-level directories where possible
(`hardening/`, `deploy/`, `ops/`, `docs/ai-cto/`) to minimize conflicts during
upstream sync.

## License Implications (AGPL-3.0)

AGPL-3.0 obligations that apply to this fork and anyone operating it:

1. **Source disclosure over a network**: If you run a modified version of this
   software and make it accessible to users over a network (for example, a
   paid proxy panel), you MUST offer those users the complete corresponding
   source code. A common and compliant solution is to publish your running
   branch on a public Git host and link to it from the panel footer or an
   `/source` endpoint.
2. **Same license**: Derivative works of upstream code must also be licensed
   under AGPL-3.0.
3. **Preserve notices**: Copyright, license, and author attribution notices
   from upstream files may not be removed.

Only **genuinely new modules** that do not derive from upstream code files may
be released under a different compatible license (e.g., Apache-2.0 or MIT).
Such modules are kept in separate top-level directories and each contains its
own `LICENSE` file when it deviates from AGPL-3.0.

## Our Own Contributions

All modifications to upstream files, and all original code under the
`hardening/`, `deploy/`, `ops/`, and `docs/ai-cto/` directories, are the work
of this project's maintainers. Independent modules declare their own license
per directory; when absent, AGPL-3.0 applies.

---
For questions about compliance or licensing, open an issue or contact the
maintainers. We take AGPL-3.0 obligations seriously and expect contributors
and operators to do the same.
