# Roadmap

See `features.md` for the full product capability map.

## Done

- [x] Multi-turn CLI chat with Gemini 3.1 Pro (`main.py`)
- [x] Root module split: `main.py`, `llm.py`, `tools.py`
- [x] Tool implementations: `list_files`, `read_file`, `search_replace`
- [x] Video and PDF input support
- [x] Tool-call loop (`handle_tool_calls`)
- [x] Specs: sequence diagram (`001_bazinga.mmd`)
- [x] Specs: architecture diagram (`002_architecture.mmd`)
- [x] Specs: signatures class diagram (`003_signatures.mmd`)
- [x] Doc server (`serve.py`)
- [x] Project constitution
- [x] Product mission reframed around visual, multimodal agent orchestration

## Now

- [ ] Define the first web UI stack and app boundary
- [ ] Build the web shell: sidebar chat, main panel, markdown rendering, Mermaid rendering
- [ ] Preserve the current CLI as the prototype/reference implementation until the web flow exists

## Next

- [ ] Add diagram-first design flow with C4-style views
- [ ] Add diagram approval and artifact persistence
- [ ] Generate PRDs from approved diagrams
- [ ] Add roadmap item creation from PRDs

## Later

- [ ] Add screen and microphone recording for multimodal feedback
- [ ] Spawn OpenCode subprocesses in isolated git worktrees
- [ ] Create PRs with PRD, diagram, and test evidence
- [ ] Build CI assessment and improvement skills
- [ ] Add policy guardrails and human-review-required labeling
- [ ] Add safe auto-merge for low-risk PRs with passing trusted CI
- [ ] Add optional ambient interaction with explicit privacy controls

## Bugs

- [ ] 003 container architecture diagram is hard to read -- too many crossing arrows. Neither `graph TD` nor `graph LR` layout works well. Need a better layout strategy for diagrams with 10+ edges.
- [ ] Need a naming scheme for diagram files -- currently ad-hoc numbering makes it hard to tell which diagrams are static/dynamic views of the same thing, which are tests, and what C4 level they belong to.
