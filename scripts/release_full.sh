#!/usr/bin/env bash
# End-to-end release helper for pandoc-embedz v0.5.0 (via Codex).
#
# Steps handled:
#   1. git add -A && git commit with a detailed message
#   2. git push (source changes)
#   3. Delete any existing v0.5.0 tag locally/remotely, then recreate it
#   4. Push the new tag
#   5. Create a GitHub release with detailed notes
#
# Prereqs:
#   - Working tree contains only the changes you want to ship
#   - gh CLI is authenticated (for release creation)

set -euo pipefail

VERSION="0.5.0"
TAG="v${VERSION}"

notes="$(cat <<'EOF'
Highlights:
- Standalone rendering (`pandoc-embedz --render file.tex`) shares the same config pipeline as the Pandoc filter, so LaTeX/Markdown templates can be rendered without invoking Pandoc first.
- `.embedz` blocks now render even when no `data:` source is provided; simple variable substitutions work out of the box and only named definition blocks stay silent.
- External YAML config files can be referenced via `config:` both in code blocks and the standalone CLI, making it easy to reuse globals/data/preambles across modes.
- README documents LaTeX/Jinja brace handling tips, and tests cover newline preservation plus data-less rendering to keep behavior consistent.

Verification:
- `python -m pytest tests`
- `python -m build`
EOF
)"

git add -A

if git diff --cached --quiet; then
  echo "No staged changes. Aborting."
  exit 1
fi

git commit -m "Prepare release ${VERSION} (via Codex)" -m "$notes"

git push

if git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag -d "$TAG"
fi

if git ls-remote --exit-code --tags origin "$TAG" >/dev/null 2>&1; then
  git push --delete origin "$TAG"
fi

git tag -a "$TAG" -m "Release version ${VERSION} (via Codex)" -m "$notes"

git push
git push --tags

gh release create "$TAG" \
  --title "$TAG" \
  --notes "$notes"
