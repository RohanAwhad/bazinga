# Mission

**Bazinga** is a visual, multimodal engineering control plane for software developers working with coding agents.

The goal is to move agent collaboration beyond terminal-only text chat. Developers should be able to explain intent through conversation, diagrams, screen context, audio, and video, then turn approved designs into PRDs, roadmap items, worktree implementations, PRs, and trusted CI-backed merges.

Bazinga starts as a Gemini-powered CLI prototype, but the product direction is a web/IDE-like UI for planning, reviewing, orchestrating, and safely delegating software work to agents.

## What it is

- A developer-facing UI for human-agent software design and implementation
- A multimodal input surface: text first, then screen/audio/video feedback
- A diagram-first planning and approval workflow using C4-style views and sequence diagrams
- An orchestration layer for PRDs, roadmap items, OpenCode worktrees, PR creation, and CI evidence
- A trust layer for guardrails, review policy, and safe automation

## What it is NOT

- Not a replacement for IDEs or terminals
- Not a generic project management tool
- Not an autonomous merge bot without CI and policy gates
- Not a diagram generator where diagrams are disconnected from code, PRDs, tests, or planned work
