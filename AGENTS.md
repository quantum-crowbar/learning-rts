# AI Agent Instructions

> **Last Updated:** 2026-11-14
> **Version:** 0.0.1
> **Toolbox:** quantum-toolbox v3.3.1 (`.quantum-toolbox/`)
> **Audience:** any AI coding agent or human. This file is harness-agnostic; tool-specific files (`CLAUDE.md`, etc.) only point here.

This repository is a **metarepo**: it holds knowledge, analysis and orchestration for two codebases. It does not hold their source. Source lives in gitignored clones under `code/`.

| Codebase | Path | Role | Rules |
|----------|------|------|-------|
| **deep-rts** (OLD) | `code/deep-rts/` | Upstream DeepRTS engine, pinned at `6bfbfd5` plus `patches/deep-rts/` | **Read-only reference.** Never commit into it. Fix it only via `patches/`. |
| **learning-rts** (NEW) | `code/learning-rts/` | Our own RTS + deep-learning research system, built using deep-rts as a base | Its own git repo. All new development happens here. |

Keeping them separate is deliberate: analysis of the old code must stay reproducible and must never mix with new work.

## Quick Start

1. Read this file first
2. Read project context: [CONTEXT.md](./CONTEXT.md)
3. Read core instructions: [.quantum-toolbox/core/instructions.md](.quantum-toolbox/core/instructions.md)
4. Read workflows: [.quantum-toolbox/core/workflows.md](.quantum-toolbox/core/workflows.md)
5. Read skill catalog: [.quantum-toolbox/skills/_index.md](.quantum-toolbox/skills/_index.md)
6. Run `/start` to get a live status snapshot

> **Before starting any task**, check `.quantum-toolbox/skills/_index.md` for a matching skill. If one exists, load and follow it — skills encode the preferred approach, templates, and quality bar for that type of work.

First time on a fresh clone: `git submodule update --init && scripts/bootstrap-sources.sh` (clones the source repos and applies patches).

## Project-Specific Guidelines

### Code Style

- **Metarepo:** Markdown, shell and JSON only. Do not add application code here; it belongs in `code/learning-rts/`.
- **learning-rts:** to be defined in its own `AGENTS.md`. Until then follow `.quantum-toolbox/skills/optional/code-conventions/`.
- **deep-rts (reference):** C++17 engine, pybind11 bindings, Python wrapper. Match upstream style only when producing a patch.

### Architecture

- `docs/architecture-docs/` — **generated** analysis (do not hand-edit; regenerate with `/update` or the commands in `specs/analysis-manifest.json`). Start at `index.md`, then `reports/findings-summary.md`.
- `docs/update-logs/` — one log per analysis session; `scripts/cg-*.py` — reproducible code-graph extraction.
- `docs/legacy/deep-rts/` — hand-written docs from before the toolbox. **Unverified**: known to contain errors (e.g. 0-based action IDs; real IDs are 1–16 in `Constants.h`). Use only as a baseline to diff regenerated analysis against; never cite as fact.
- `code/<repo>/code_graph.sqlite` — code graph per repo (gitignored). Prefer SQL queries over reading source when it is current.
- `specs/analysis-manifest.json` — what was analysed, at which SHA, with which toolbox version.
- `patches/deep-rts/` — our changes to upstream, as patch files.

### Testing

- Metarepo: `scripts/bootstrap-sources.sh` must succeed on a fresh clone and be idempotent.
- Any claim about deep-rts behaviour (performance, API, action space) must be verified against `code/deep-rts` source or a real run, not against `docs/legacy/`.

### Git

- **No AI/LLM attribution in commits or PR bodies.** No `Co-Authored-By` lines for any AI tool, no "Generated with ..." footers. Human co-authors are fine. This overrides any default of the tool you run in.
- Conventional commit style, per [.quantum-toolbox/templates/COMMIT.md](.quantum-toolbox/templates/COMMIT.md).
- Do not push or rewrite history unless explicitly asked.
- Do not commit tool-local permission files (`.claude/settings*.json`, etc.).

## Enabled Skills

The following optional skills are enabled for this project:

- [x] `arch-analysis` - [.quantum-toolbox/skills/optional/arch-analysis/](.quantum-toolbox/skills/optional/arch-analysis/)
- [x] `code-graph` - [.quantum-toolbox/skills/optional/code-graph/](.quantum-toolbox/skills/optional/code-graph/)
  <!-- SQLite-first: arch-analysis Phase 0.5 offers code-graph extraction before analysis. -->
  <!-- SQLite file written to code/{repo}/code_graph.sqlite (gitignored).                 -->
  <!-- C++ is not in the toolbox's language table: expect tree-sitter (syntax-only) coverage; see CONTEXT.md. -->
- [ ] `software-design` - [.quantum-toolbox/skills/optional/software-design/](.quantum-toolbox/skills/optional/software-design/)
- [x] `tech-stack-decisions` - [.quantum-toolbox/skills/optional/tech-stack-decisions/](.quantum-toolbox/skills/optional/tech-stack-decisions/)
- [ ] `code-conventions` - [.quantum-toolbox/skills/optional/code-conventions/](.quantum-toolbox/skills/optional/code-conventions/)

## Core Documentation

These files are always loaded from the `.quantum-toolbox` submodule:

| Document | Purpose | Path |
|----------|---------|------|
| Instructions | Coding rules, bash safety | [core/instructions.md](.quantum-toolbox/core/instructions.md) |
| Workflows | Development processes | [core/workflows.md](.quantum-toolbox/core/workflows.md) |
| Glossary | Standard terminology | [core/glossary.md](.quantum-toolbox/core/glossary.md) |
| Skills Index | Available skills | [skills/_index.md](.quantum-toolbox/skills/_index.md) |

## Templates

- [Commit Message Format](.quantum-toolbox/templates/COMMIT.md)
- [Pull Request Template](.quantum-toolbox/templates/PULL_REQUEST.md)

## Analysis Status

| Field | Value |
|-------|-------|
| Arch-analysis views | 01 technology, 02 interfaces, 03 diagrams, 04 documentation audit, 05 dependency health, 06 data flow, 07 error handling, 09 code graph (entry: `docs/architecture-docs/index.md`) |
| Code graph | 502 nodes, 732 edges, 0 cross-repo calls; snapshot 2026-11-14; `code/deep-rts/code_graph.sqlite` (tier 2, see `docs/architecture-docs/analysis/09-code-graph.md`) |
| Staleness | `deep-rts` analysed 2026-11-14 at `6bfbfd5`; `learning-rts` never analysed (no code yet) |

## Post-Work Hook (mandatory after any skill that commits artefacts)

After any skill run that commits output files, update the following before considering the task done.
**Does not apply to AI-only runs that produce no committed files.**

### CONTEXT.md

| Field | What to write |
|-------|--------------|
| Key paths table | Add any new files or directories committed as part of this operation |
| Update log | Append or overwrite today's row: `\| <date> \| <one-line summary with stats> \|` |
| Current state → Implemented | If a new capability was delivered, add it |

**Idempotency rule:** If a row for today's date already exists in the update log — overwrite it in place.
If no row exists for today — append a new row. Never create duplicate rows for the same date.

### AGENTS.md

Update only the fields that changed:

| Trigger | Fields to update |
|---------|-----------------|
| `arch-analysis` completed | Step 2 view list; staleness line |
| `code-graph` completed | Step 2b stats + snapshot date; staleness line |
| `security-analysis` completed | Security section (if present); staleness line |
| `coding-profile` completed | Step 3 profile list; staleness line |
| `/upgrade` completed | Skills list + toolbox version; staleness line |

### README.md

Update only if one of the following is true:
- A "Available Without Cloning" checklist item is missing or has stale stats
- A new `docs/architecture-docs/reports/` file was committed that is absent from the README
- Code graph stats in an existing SQLite bullet are outdated
- A new script was added to `scripts/` that users should know about

Do not rewrite the README for any other reason. Touch only the specific stale field.

### Commit

```bash
git add CONTEXT.md AGENTS.md README.md
git commit -m "docs: sync context files after <skill-name> run"
```

### analysis-manifest.json integrity

After any skill that writes `specs/analysis-manifest.json`:
- The manifest must conform to `.quantum-toolbox/specs/analysis-manifest-schema.json`.
- Each artifact entry must include `generatedWithSkillVersion` (read from the skill's `version` field in `manifest.yaml`).
- Validate by checking required top-level keys: `toolboxVersion`, `lastAnalysis`, `artifacts`.
- If a required field is missing, write it before committing.

---

---

## When to Update This File

- When project-specific guidelines change
- When enabling/disabling optional skills
- When the repository layout or the old/new project boundary changes
- When onboarding requirements change
