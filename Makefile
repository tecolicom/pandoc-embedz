.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.PHONY: release release-n
.SILENT: release release-n

release:
	DRYRUN="$(strip $(DRYRUN))"
	comment() { printf '# %s\n' "$$*"; }
	warn() { printf '%s\n' "$$*" >&2; }
	die()  { warn "$$@"; exit 1; }
	run() { [ -n "$$DRYRUN" ] && printf '%s\n' "$$1" || eval "$$1"; }
	VERSION=$$(sed -En 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/p' CHANGELOG.md | head -n1)
	[ -n "$$VERSION" ] || die "Error: unable to determine release version from CHANGELOG.md"
	TAG="v$$VERSION"
#	NOTES_CONTENT="$$(awk 'BEGIN { grab=0 } /^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ { if (grab) exit; grab=1 } grab { print }' CHANGELOG.md)"
	NOTES_CONTENT="$$(greple -E '^## \[[0-9]+\.[0-9]+\.[0-9]+\](?s:.*?)(?=\n## )' CHANGELOG.md -m1 --no-color -h | ansifold --autoindent '^-\s+' -s --boundary=space)"
	echo "$$NOTES_CONTENT"

	comment "Ensuring clean main branch"
	CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD)
	[ "$$CURRENT_BRANCH" = "main" ] || die "Error: release must be created from main (current: $$CURRENT_BRANCH)"
	if [[ -z "$(IGNORE_DIRTY)" && -n $$(git status --porcelain) ]]; then
		git status -sb
		die "Error: working tree is dirty"
	fi

	git rev-parse "$$TAG" >/dev/null 2>&1 && die "Error: tag $$TAG already exists"

	comment "Running tests"
	run "python -m pytest tests/"

	comment "Building artifacts"
	run "rm -rf build dist"
	run "python -m build"

	comment "Committing release $$VERSION"
	run "git add CHANGELOG.md pandoc_embedz/__init__.py pyproject.toml AGENTS.md"
	run "git commit -F -" <<< "$$(printf 'Release version %s\n\n%s' "$$VERSION" "$$NOTES_CONTENT")"

	comment "Tagging $$TAG"
	run "git tag -a \"$$TAG\" -m \"Release version $$VERSION\""

	comment "Pushing main and $$TAG"
	run "git push origin main"
	run "git push origin tag \"$$TAG\""

	comment "Creating GitHub release $$TAG"
	run "gh release create \"$$TAG\" --title \"v$$VERSION\" --notes-file -" <<< "$$NOTES_CONTENT"

	run "echo \"Release $$TAG published successfully.\""

release-n:
	+@$(MAKE) DRYRUN=1 IGNORE_DIRTY=1 release
