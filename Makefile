.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.PHONY: release release-n
.SILENT: release release-n

release:
	DRYRUN="$(strip $(DRYRUN))"
	comment() { printf '# %s\n' "$$*"; }
	run() {
		if [ -n "$$DRYRUN" ]; then
			printf '%s\n' "$$1"
		else
			eval "$$1"
		fi
	}
	VERSION=$$(sed -En 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/p' CHANGELOG.md | head -n1)
	if [ -z "$$VERSION" ]; then
		echo "Error: unable to determine release version from CHANGELOG.md" >&2
		exit 1
	fi
	TAG="v$$VERSION"
	NOTES_CONTENT="$$(awk 'BEGIN { grab=0 } /^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ { if (grab) exit; grab=1 } grab { print }' CHANGELOG.md)"

	comment "Ensuring clean main branch"
	if [ -z "$$DRYRUN" ]; then
		CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD)
		if [ "$$CURRENT_BRANCH" != "main" ]; then
			echo "Error: release must be created from main (current: $$CURRENT_BRANCH)" >&2
			exit 1
		fi
		if [ -n "$$(git status --porcelain)" ]; then
			echo "Error: working tree is dirty" >&2
			git status -sb
			exit 1
		fi
	else
		run "git rev-parse --abbrev-ref HEAD"
		run "git status -sb"
	fi

	if git rev-parse "$$TAG" >/dev/null 2>&1; then
		if [ -n "$$DRYRUN" ]; then
			comment "tag $$TAG already exists; real run would stop here."
		else
			echo "Error: tag $$TAG already exists" >&2
			exit 1
		fi
	fi

	comment "Running tests"
	run "python -m pytest tests/"

	comment "Building artifacts"
	run "rm -rf build dist"
	run "python -m build"

	comment "Committing release $$VERSION"
	run "git add CHANGELOG.md pandoc_embedz/__init__.py pyproject.toml AGENTS.md"
	run "git commit -m \"Prepare release $$VERSION (via Codex / GPT-5)\" -m \"- bump pyproject + __version__ to $$VERSION\" -m \"- roll CHANGELOG.md into dated $$VERSION section and update comparison links\" -m \"- document release-script expectations in AGENTS.md and ignore local scripts/\" -m \"- rely on local helper workflow instead of tracked scripts\""

	comment "Tagging $$TAG"
	run "git tag -a \"$$TAG\" -m \"Release version $$VERSION (via Codex / GPT-5)\""

	comment "Pushing main and $$TAG"
	run "git push origin main"
	run "git push origin tag \"$$TAG\""

	comment "Creating GitHub release $$TAG"
	run "gh release create \"$$TAG\" dist/* --title \"v$$VERSION\" --notes \"$$NOTES_CONTENT\""

	if [ -n "$$DRYRUN" ]; then
		comment "Release $$TAG sequence complete (no changes made)."
	else
		echo "Release $$TAG published successfully."
	fi

release-n:
	+@$(MAKE) DRYRUN=1 release
