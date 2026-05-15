# Features

Bazinga is the meta-project: a developer UI and agent orchestration system used to design, build, test, and ship other software projects.

## Product Thesis

Diagrams should become the approval interface for agentic software development.

Developers should be able to brainstorm with an agent, generate architecture diagrams, revise them with text or show-and-tell feedback, approve the design, and then let agents turn that approved intent into PRDs, roadmap items, worktree implementations, PRs, and CI-backed delivery.

## Core Workflow

| Step | Human action | Agent/system output |
| --- | --- | --- |
| Brainstorm | Chat in sidebar | Feature understanding |
| Visualize | Ask for architecture | C4/Mermaid diagrams |
| Iterate | Give text, audio, video, or screen feedback | Updated diagrams |
| Approve | Approve a diagram or component | Locked implementation intent |
| Specify | Request implementation plan | PRD and roadmap item |
| Build | Start implementation | OpenCode subprocess in a git worktree |
| Verify | Run tests and CI | Evidence report |
| Review | Inspect PR and policy labels | Merge or human review required |

## Capability Areas

### Sidebar Agent

- Chat with an agent while viewing diagrams, PRDs, roadmap items, and implementation status.
- Keep the conversation tied to the current project and selected artifacts.

### Diagram Canvas

- Render agent output as markdown with strong Mermaid support.
- Prefer concise text plus architecture, sequence, and C4-style diagrams.
- Support context, container, component, and code-level views.

### Multimodal Feedback

- Start with explicit screen and microphone recording.
- Let developers explain changes by pointing, speaking, and showing the screen.
- Later, support optional ambient speech detection with clear privacy controls.

### Diagram Approval

- Treat approved diagrams as implementation contracts.
- Keep approved diagrams traceable to conversation, PRDs, roadmap items, files, tests, and PRs.

### PRD And Roadmap

- Generate PRDs from approved diagrams.
- Include behavior, acceptance criteria, test strategy, CI expectations, and rollout constraints.
- Add approved PRDs to a roadmap for implementation.

### OpenCode Worktrees

- Create isolated git worktrees for roadmap items.
- Spawn OpenCode subprocesses with the approved PRD, diagrams, and constraints.
- Track implementation status and changed files.

### PR And Evidence Flow

- Draft commits and PR descriptions from completed work.
- Attach PRD context, diagrams, test commands, and exact outputs.
- Detect deleted tests, sensitive file changes, and risky diffs.

### CI Trust Layer

- Treat CI design as part of feature design.
- Add skills for CI assessment, missing-test detection, Playwright/e2e coverage, API/integration tests, and required check policy.
- Increase agent autonomy only when verification is trustworthy.

### Guardrails And Auto-Merge

- Configure human-review-required policies by path, directory, file, risk type, and test impact.
- Auto-merge only when CI passes, tests were not weakened, and policy gates allow it.

## Phases

### Phase 0: Current CLI Prototype

- Gemini/Vertex-powered multi-turn CLI.
- File tools: list, read, search/replace.
- Text, video, and PDF input.
- Root modules: `main.py`, `llm.py`, `tools.py`.

### Phase 1: Web Shell And Rendering

- Web app skeleton.
- Sidebar chat UI.
- Main content panel.
- Markdown rendering.
- Mermaid rendering.
- Basic project/session state.

### Phase 2: Diagram-First Design

- Generate and revise C4-style diagrams.
- Support context, container, component, and sequence diagrams.
- Add diagram approval action.
- Store approved diagrams as project artifacts.

### Phase 3: Multimodal Input

- Add record button for screen and microphone capture.
- Send recordings to the agent as context.
- Update diagrams from spoken and visual feedback.

### Phase 4: PRD And Roadmap

- Generate PRDs from approved diagrams.
- Link diagrams, PRDs, and roadmap items.
- Include acceptance criteria, test strategy, and CI expectations.

### Phase 5: OpenCode Implementation

- Create a git worktree from a roadmap item.
- Spawn OpenCode in that worktree.
- Pass approved artifacts to the implementation agent.
- Run focused verification commands and collect results.

### Phase 6: PR Creation

- Draft commit messages and PR descriptions.
- Include diagrams, PRD summary, test commands, and exact outputs.
- Label risky changes for human review.

### Phase 7: CI Trust Layer

- Assess CI strength before automation.
- Recommend and implement missing checks.
- Support Playwright/e2e and API/integration tests where relevant.
- Require trusted checks before auto-merge.

### Phase 8: Policy-Based Auto-Merge

- Add guardrail config for sensitive paths and risky changes.
- Block auto-merge on deleted tests, weakened checks, sensitive diffs, or failed CI.
- Allow low-risk PRs to merge automatically.

### Phase 9: Ambient Interaction

- Add optional wake/listen behavior.
- Support automatic speech detection.
- Keep privacy controls and recording indicators explicit.

## MVP

- Sidebar chat.
- Markdown rendering.
- Mermaid rendering.
- Architecture diagram generation.
- Diagram revision through text.
- Diagram approval.
- PRD generation from approved diagrams.

## Trust Principles

- Diagrams must not become pretty hallucinations.
- Approved diagrams must be traceable to conversation, files, PRDs, roadmap items, tests, or PRs.
- CI should be designed alongside features.
- Agent autonomy should increase only as verification improves.
- Risky files and deleted tests should require human review.
- Human approval should happen at intent boundaries, not every tiny code diff.
