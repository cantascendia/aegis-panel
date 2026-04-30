# SPEC — Eval Gate Workflow (CI Auto-Enforcement of 铁律 #12)

> Issue: [#112](https://github.com/cantascendia/aegis-panel/issues/112)
> Branch: `ci/eval-gate-workflow`
> Status: v1 (advisory mode)
> Author: CTO (delegated to CI infrastructure agent)
> Date: 2026-04-30
> Template: D-005 (three-section SPEC for small/medium PRs)

---

## 1. What

**A GitHub Actions workflow that auto-runs `evals/` validation on every PR that
modifies harness configs, posts a results table to the PR as a comment, and
flags PRs that do not include corresponding `evals/` updates.**

Concretely:

- Trigger: PR (base = `main`) touching any of:
  - `CLAUDE.md`
  - `.claude/{commands,agents,skills,rules}/**`
  - `.agents/skills/**`
  - `playbook/**`
  - `evals/**`
- Action: Run `scripts/eval-runner.sh evals/golden-trajectories` (yaml schema
  validator) → render Markdown results table → post as PR comment.
- Side check: If the PR diff does **not** touch `evals/`, append an advisory
  warning ("harness config changed without eval coverage — 铁律 #12 violation
  candidate").
- Mode: **Advisory** for first 2 weeks. Workflow always exits 0 (does not
  block merge). After observation window, flip to enforce (fail on schema
  errors / missing evals).

This v1 ships the trigger, the parser harness, and the comment surface. It
does **not** invoke Claude / any LLM — it only validates that yaml cases
exist and conform to schema.

---

## 2. Why

### 2.1 The problem (current state)

Iron Law #12 in `CLAUDE.md` says:

> 无 eval 的 agent 配置改动不得进 main

Today this is **honor system only**. There is no CI gate. An engineer (or
agent) can land `.claude/agents/foo.md` without ever updating `evals/`, and
nothing catches it. This was the #2 finding in the §34 harness audit
(`docs/ai-cto/HARNESS-AUDIT-2026-04.md`).

### 2.2 Why this design (vs alternatives)

The issue body listed 4 TBDs. Decisions and rationale:

| TBD | Choice | Rationale |
|---|---|---|
| **TBD-1** Tool selection | Local Bash parser, no external API | Braintrust = $25/mo subscription. v1 should ship before paying. Schema validation alone catches >50% of "agent shipped without eval" cases. |
| **TBD-2** Mock vs real Claude | Mock (parser only — yaml schema check) | Real Claude invocation requires API key in CI, costs ~$0.05/PR, and adds a non-determinism axis that we don't want to debug while the harness itself is being tuned. Schema check is deterministic + free. |
| **TBD-3** Environment | GitHub Actions Linux + read-only checkout | Parser is Bash + grep + awk. No worktree, no DB, no Python. Cheapest possible runner config. |
| **TBD-4** Failure handling | Advisory comment, no merge block (2 weeks) | If we enforce on day 1 and the parser has a bug, the entire harness PR pipeline halts. Advisory mode lets us collect signal on false-positive rate before turning the screws. |

### 2.3 ROI

Harness audit estimated: ~30 min/quarter saved per agent landed without
eval (no need for retroactive eval-coverage sweep). At current pace
(~6 agents/quarter) this is ~3 hr/quarter, ~12 hr/year. The workflow itself
costs <2 hr to maintain.

---

## 3. How

### 3.1 Components (4 new files)

```
.github/workflows/eval-gate.yml          # GHA workflow definition
scripts/eval-runner.sh                   # local yaml schema validator
docs/ai-cto/SPEC-eval-gate.md            # this file
evals/regression/003-eval-gate-trigger.yaml   # self-test trajectory
```

### 3.2 Workflow logic (eval-gate.yml)

```
on: pull_request paths: [harness paths above]
jobs:
  eval-gate:
    if: base == main
    steps:
      1. checkout (fetch-depth: 0 — needed for git diff vs base sha)
      2. Check `git diff base..HEAD --name-only` for evals/ touch
         → emit needs_evals advisory flag if absent
      3. Run scripts/eval-runner.sh evals/golden-trajectories
         → capture stdout, append to GITHUB_STEP_SUMMARY
         → record exit_status (advisory: don't propagate to job exit)
      4. Post a single PR comment via actions/github-script@v7
         with marker `<!-- eval-gate -->` (idempotent comments come later)
```

Permissions: `contents: read`, `pull-requests: write` (for the comment).
The job intentionally always exits 0 in v1 (advisory).

### 3.3 Parser logic (eval-runner.sh)

For each `*.yaml` in the target directory, validate the 7 required
fields exist:

```
id, description, input, expected_steps, forbidden_actions,
acceptance_criteria, priority
```

Output a Markdown table:

```
| ID | Priority | Status |
|---|---|---|
| 001-add-feature-with-spec | P0 | ✅ PASS |
| 003-broken-case           | P1 | ❌ FAIL — missing fields: forbidden_actions |
```

Exit 0 on all-pass, exit 1 on any fail. v1 does **not** validate field
content (only existence) — that is v2 work.

### 3.4 Self-test (003-eval-gate-trigger.yaml)

Adds a regression trajectory describing the canonical "land sub-agent
without eval" failure mode. This case is itself a yaml that must conform
to schema, so the parser validates itself indirectly.

---

## 4. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **False positive noise**: PRs that legitimately don't need eval (e.g. typo fix in CLAUDE.md) get warned | Medium | Advisory mode first. Reviewer can ignore the comment. v2 will allow `[skip-eval-gate]` in commit message. |
| **Parser bug halts harness PRs** | Low (advisory mode) | Workflow always `exit 0` in v1. Even if the parser segfaults, merge is unblocked. |
| **PR comment spam (1 per push)** | Medium | v1 uses `createComment` not `updateComment`. v2 will look up existing `<!-- eval-gate -->` comment and update in place. |
| **Permanent advisory mode** (never enforced) | Medium | SPEC commits to 2-week observation window. After 2026-05-14, run a follow-up issue to flip mode. |
| **Forbidden path double-review skipped** | Low | This SPEC documents the §32 requirement. PR will carry `requires-double-review` label and run codex cross-review. |

---

## 5. Acceptance Criteria

- [ ] `.github/workflows/eval-gate.yml` exists and YAML is valid
- [ ] `scripts/eval-runner.sh` is `chmod +x` and exits 0 on all 5 current
      P0 trajectories under `evals/golden-trajectories/`
- [ ] On a synthetic test PR that touches `.claude/agents/foo.md` without
      `evals/`, the workflow posts a comment containing the warning text
      "without touching evals/"
- [ ] On a synthetic test PR with a malformed yaml (missing
      `acceptance_criteria`), the workflow posts a comment with `❌ FAIL`
- [ ] PR carries `requires-double-review` label
- [ ] Codex cross-review runs and verdict captured in
      `docs/ai-cto/CODEX-REVIEW-LOG.md`
- [ ] Issue #112 closed with backreference to merge SHA

---

## 6. Out of scope (v2 candidates)

- Real Claude API invocation (run trajectories against live Claude, score
  against `expected_steps`)
- `[skip-eval-gate]` commit message escape hatch
- Idempotent PR comment (update-in-place vs append)
- Mutation testing on the parser itself
- Enforce mode (fail PR check on schema errors)
- Per-priority gating (P0 must pass, P1/P2 advisory)

---

## 7. Rollout

| Date | Action |
|---|---|
| 2026-04-30 | Ship advisory v1 (this PR) |
| 2026-05-14 | Review false-positive rate; decide enforce vs stay-advisory |
| 2026-05-21 (if green) | Open follow-up issue: flip workflow to enforce mode + idempotent comments + `[skip-eval-gate]` escape |

---

_End of SPEC._
