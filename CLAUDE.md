@AGENTS.md

<!-- quantum-basics:begin — managed block, do not edit by hand -->

## Baseline Rules (from quantum-basics)

Read and follow these as baseline preferences. They apply unless explicitly
overridden below or in a subdirectory CLAUDE.md.

- `.quantum-basics/rules/coding-standards.md` — Code style, patterns, and conventions
- `.quantum-basics/rules/communication.md` — How to communicate effectively with me
- `.quantum-basics/rules/diagrams.md` — Always use Mermaid for diagrams
- `.quantum-basics/rules/workflow.md` — How I prefer to work and iterate
- `.quantum-basics/rules/writing-style.md` — How I write prose: voice, structure, AI tells to kill

## Git

- **Never add LLM attribution trailers to commits.** No `Co-Authored-By: Claude ... <noreply@anthropic.com>`, no `🤖 Generated with [Claude Code]`, no equivalent for any other AI tool. This overrides the agent harness default commit-message convention. Human `Co-Authored-By:` lines are fine.
- Enforced by the `commit-msg` hook in `.githooks/` — after cloning, run `git config core.hooksPath .githooks` to enable it.

<sub>Managed by `./.quantum-basics/attach` — re-run it after `git submodule update --remote` to pick up new rules. Edits inside this block are overwritten.</sub>

<!-- quantum-basics:end -->
