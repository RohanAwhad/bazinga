#!/bin/bash
set -e

if [ -z "$REPO_URL" ] || [ -z "$BRANCH_NAME" ] || [ -z "$PRD_PATH" ]; then
    echo "Usage: REPO_URL=owner/repo BRANCH_NAME=feat/xxx PRD_PATH=path/to/prd.md ./run_prd.sh"
    exit 1
fi

export GH_TOKEN="${GH_TOKEN:-$(gh auth token)}"

echo "=== Implementation: $PRD_PATH on branch $BRANCH_NAME ==="
podman-compose run --rm worker

PR_NUMBER=$(gh pr list --repo "$REPO_URL" --head "$BRANCH_NAME" --json number --jq '.[0].number')

if [ -z "$PR_NUMBER" ] || [ "$PR_NUMBER" = "null" ]; then
    echo "ERROR: No PR found for branch $BRANCH_NAME. Implementation agent did not create a PR."
    exit 1
fi

echo "=== PR #$PR_NUMBER created. Launching babysit + review ==="

podman run --rm \
    -v ~/.config/gcloud:/root/.config/gcloud:ro \
    -e GH_TOKEN="$GH_TOKEN" \
    -e ANTHROPIC_VERTEX_PROJECT_ID="$ANTHROPIC_VERTEX_PROJECT_ID" \
    -e CLOUD_ML_REGION="$CLOUD_ML_REGION" \
    -e GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" \
    -e GOOGLE_VERTEX_LOCATION="$GOOGLE_VERTEX_LOCATION" \
    -e CLAUDE_CODE_USE_VERTEX=1 \
    bazinga-worker \
    sh -c "gh repo clone $REPO_URL /repo && cd /repo && opencode run '/babysit-pr #$PR_NUMBER' --model google-vertex-anthropic/claude-opus-4-6@default --dangerously-skip-permissions" &

podman run --rm \
    -v ~/.config/gcloud:/root/.config/gcloud:ro \
    -e GH_TOKEN="$GH_TOKEN" \
    -e ANTHROPIC_VERTEX_PROJECT_ID="$ANTHROPIC_VERTEX_PROJECT_ID" \
    -e CLOUD_ML_REGION="$CLOUD_ML_REGION" \
    -e GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" \
    -e GOOGLE_VERTEX_LOCATION="$GOOGLE_VERTEX_LOCATION" \
    -e CLAUDE_CODE_USE_VERTEX=1 \
    bazinga-worker \
    sh -c "gh repo clone $REPO_URL /repo && cd /repo && opencode run '/code-review #$PR_NUMBER' --model google-vertex-anthropic/claude-opus-4-6@default --dangerously-skip-permissions" &

wait

echo "=== Done. PR #$PR_NUMBER babysit + review complete ==="
