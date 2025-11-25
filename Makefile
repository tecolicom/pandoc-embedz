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
	dryrun() { echo "$${FUNCNAME[1]}$$(printf ' %q' "$$@")"; }
	extract_notes() { greple -E '^## \[[0-9]+\.[0-9]+\.[0-9]+\](?s:.*?)(?=\n## )' -m1 --no-color -h; }
	fold_notes() { ansifold --autoindent '^-\s+' -s --boundary=space; }
	if [ -n "$$DRYRUN" ]; then
		git()    { dryrun "$$@"; }
		gh()     { dryrun "$$@"; }
		python() { dryrun "$$@"; }
		uv()     { dryrun "$$@"; }
		perl()   { dryrun "$$@"; }
	else
		set -x
	fi
	VERSION=$$(command perl -nE 'say $$1 and last if /^## \[([0-9]+\.[0-9]+\.[0-9]+)\]/' CHANGELOG.md)
	TAG="v$${VERSION:?Error: unable to determine release version from CHANGELOG.md}"
	NOTES_CONTENT="$$(extract_notes < CHANGELOG.md)"
	NOTES_CONTENT="$$(fold_notes <<< "$$NOTES_CONTENT")"
	echo "========================================"
	comment "Release notes for $$VERSION"
	echo "========================================"
	echo "$$NOTES_CONTENT"
	echo "========================================"

	comment "Ensuring clean main branch"
	CURRENT_BRANCH=$$(command git rev-parse --abbrev-ref HEAD)
	[ "$$CURRENT_BRANCH" = "main" ] || die "Error: release must be created from main (current: $$CURRENT_BRANCH)"

	if [[ -z "$(IGNORE_TAG_EXISTS)" ]]; then
		command git rev-parse "$$TAG" >/dev/null 2>&1 && die "Error: tag $$TAG already exists"
	fi

	comment "Checking for uncommitted changes"
	if [[ -z "$(IGNORE_DIRTY)" ]]; then
		DIRTY=$$(command git status --porcelain | grep -v "^ M CHANGELOG.md$$" || true)
		[ -z "$$DIRTY" ] || die "Error: working directory has uncommitted changes (except CHANGELOG.md):\n$$DIRTY"
	fi

	comment "Updating version numbers to $$VERSION"
	perl -i -pe "s/^version = .*/version = \"$$VERSION\"/" pyproject.toml
	perl -i -pe "s/__version__ = .*/__version__ = '$$VERSION'/" pandoc_embedz/__init__.py

	comment "Updating uv.lock"
	uv lock

	comment "Running tests"
	uv run pytest tests/

	comment "Committing release $$VERSION"
	git add -u
	git commit -F - <<< "$$(printf 'Release version %s\n\n%s' "$$VERSION" "$$NOTES_CONTENT")"

	comment "Tagging $$TAG"
	git tag -a "$$TAG" --cleanup=whitespace -F - <<< "$$(printf 'Release version %s\n\n%s' "$$VERSION" "$$NOTES_CONTENT")"

	comment "Pushing main and $$TAG"
	git push origin main
	git push origin tag "$$TAG"

	comment "Creating GitHub release $$TAG"
	gh release create "$$TAG" --title "v$$VERSION" --notes-from-tag

	echo "Release $$TAG published successfully."

release-n:
	+@$(MAKE) DRYRUN=1 IGNORE_TAG_EXISTS=1 IGNORE_DIRTY=1 release
