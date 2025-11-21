#!/usr/bin/env bash
# Release helper for pandoc-embedz v0.5.0 (via Codex).
#
# This script:
#   1. Creates an annotated git tag with a detailed message
#   2. Creates a GitHub release with the same notes
#
# Prereqs:
#   - Build artifacts if you plan to upload them manually (`python -m build`)
#   - gh CLI is authenticated and has permission to create releases

set -euo pipefail

VERSION="0.5.0"
TAG="v${VERSION}"
TITLE="v${VERSION}"

notes="$(cat <<'EOF'
Highlights:
- Standalone rendering (`pandoc-embedz --render file.tex`) shares the same config pipeline as the Pandoc filter, so LaTeX/Markdown templates can be rendered without invoking Pandoc first.
- `.embedz` blocks now render even when no `data:` source is provided; simple variable substitutions work out of the box and only named definition blocks stay silent.
- External YAML config files can be referenced via `config:` both in code blocks and the standalone CLI, making it easy to reuse globals/data/preambles across modes.
- README documents LaTeX/Jinja brace handling tips, and tests cover newline preservation plus data-less rendering to keep behavior consistent.

Verification:
- `python -m pytest tests`
- `python -m build` (rerun with network access before executing this script)
EOF
)"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists; skipping tag creation."
else
  git tag -a "$TAG" -m "Release version ${VERSION} (via Codex)" -m "$notes"
fi

git push
git push --tags

gh release create "$TAG" \
  --title "$TITLE" \
  --notes "$notes"
