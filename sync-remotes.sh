#!/usr/bin/env bash

# sync-remotes.sh
# Sync one or all local branches to two remotes (default: origin -> github)
# - Ensures clean working tree
# - Fetches/prunes all remotes
# - Verifies fast-forward status against both remotes
# - Pushes to both remotes with tags

set -euo pipefail

PRIMARY_REMOTE="origin"
SECONDARY_REMOTE="github"
TARGET_BRANCH=""
PUSH_ALL_BRANCHES=0
SECONDARY_SPECIFIED=0
SECONDARY_URL=""
FORCE_SECONDARY=0
SNAPSHOT_SECONDARY=0

print_usage() {
  cat <<EOF
Usage: $(basename "$0") [--primary <remote>] [--secondary <remote>] [--branch <name>] [--all]

Options:
  -p, --primary     Primary remote to push to (default: origin)
  -s, --secondary   Secondary remote to mirror to (default: github)
  -b, --branch      Specific branch to sync (default: current branch)
  -a, --all         Sync all local branches
  -h, --help        Show this help

Behavior:
  - Requires clean working tree
  - Fetches/prunes all remotes
  - Fast-forward only: local must be ahead-of or equal-to both remotes
  - Pushes to both remotes with --follow-tags
EOF
}

fail() {
  echo "\nERROR: $*\n" >&2
  exit 1
}

is_ancestor() {
  # usage: is_ancestor <maybe_ancestor> <maybe_descendant>
  git merge-base --is-ancestor "$1" "$2" 2>/dev/null
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--primary)
      [[ $# -ge 2 ]] || fail "--primary requires a value"
      PRIMARY_REMOTE="$2"; shift 2 ;;
    -s|--secondary)
      [[ $# -ge 2 ]] || fail "--secondary requires a value"
      SECONDARY_REMOTE="$2"; SECONDARY_SPECIFIED=1; shift 2 ;;
    --secondary-url)
      [[ $# -ge 2 ]] || fail "--secondary-url requires a value"
      SECONDARY_URL="$2"; shift 2 ;;
    --force-secondary)
      FORCE_SECONDARY=1; shift ;;
    --snapshot-secondary)
      SNAPSHOT_SECONDARY=1; shift ;;
    -b|--branch)
      [[ $# -ge 2 ]] || fail "--branch requires a value"
      TARGET_BRANCH="$2"; shift 2 ;;
    -a|--all)
      PUSH_ALL_BRANCHES=1; shift ;;
    -h|--help)
      print_usage; exit 0 ;;
    *)
      fail "Unknown argument: $1" ;;
  esac
done

# Preconditions
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Not a git repository."

if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  fail "Uncommitted changes. Commit/stash first."
fi

mapfile -t ALL_REMOTES < <(git remote)
declare -A REMOTE_URLS
while read -r name url _; do
  REMOTE_URLS["$name"]="$url"
done < <(git remote -v | awk '{print $1, $2}')

# Resolve primary remote if missing
if ! printf '%s\n' "${ALL_REMOTES[@]}" | grep -qx "$PRIMARY_REMOTE"; then
  if [[ ${#ALL_REMOTES[@]} -eq 1 ]]; then
    PRIMARY_REMOTE="${ALL_REMOTES[0]}"
    echo "Primary remote 'origin' not found. Using detected remote: $PRIMARY_REMOTE"
  else
    fail "Remote '$PRIMARY_REMOTE' not found. Specify with -p/--primary (available: ${ALL_REMOTES[*]})."
  fi
fi

# Resolve or create secondary remote
if [[ $SECONDARY_SPECIFIED -eq 1 ]]; then
  if ! printf '%s\n' "${ALL_REMOTES[@]}" | grep -qx "$SECONDARY_REMOTE"; then
    if [[ -n "$SECONDARY_URL" ]]; then
      echo "Adding secondary remote '$SECONDARY_REMOTE' => $SECONDARY_URL"
      git remote add "$SECONDARY_REMOTE" "$SECONDARY_URL"
      ALL_REMOTES+=("$SECONDARY_REMOTE")
      REMOTE_URLS["$SECONDARY_REMOTE"]="$SECONDARY_URL"
    else
      echo "Secondary remote '$SECONDARY_REMOTE' not found; will push only to primary. Use --secondary-url to add it." >&2
      SECONDARY_REMOTE=""
    fi
  fi
else
  # Try to auto-detect a GitHub remote by URL
  for r in "${ALL_REMOTES[@]}"; do
    url=${REMOTE_URLS["$r"]}
    if [[ "$r" != "$PRIMARY_REMOTE" && "$url" == *"github.com"* ]]; then
      SECONDARY_REMOTE="$r"
      echo "Auto-detected secondary GitHub remote: $SECONDARY_REMOTE ($url)"
      break
    fi
  done
  # If none found and more than one remote, pick the first non-primary
  if [[ -z "$SECONDARY_REMOTE" && ${#ALL_REMOTES[@]} -ge 2 ]]; then
    for r in "${ALL_REMOTES[@]}"; do
      if [[ "$r" != "$PRIMARY_REMOTE" ]]; then
        SECONDARY_REMOTE="$r"
        echo "Auto-detected secondary remote: $SECONDARY_REMOTE (${REMOTE_URLS["$SECONDARY_REMOTE"]})"
        break
      fi
    done
  fi
fi

echo "Fetching all remotes (prune)…"
git fetch --all --prune >/dev/null

# Determine branches to process
branches=()
if [[ "$PUSH_ALL_BRANCHES" -eq 1 ]]; then
  while IFS= read -r ref; do
    [[ -n "$ref" ]] && branches+=("$ref")
  done < <(git for-each-ref --format='%(refname:short)' refs/heads/)
else
  if [[ -z "$TARGET_BRANCH" ]]; then
    TARGET_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    [[ "$TARGET_BRANCH" != "HEAD" ]] || fail "Detached HEAD. Checkout a branch first."
  fi
  branches=("$TARGET_BRANCH")
fi

for b in "${branches[@]}"; do
  echo -e "\n== $b =="

  # Ensure upstream to PRIMARY if missing
  upstream=""
  set +e
  upstream=$(git rev-parse --abbrev-ref --symbolic-full-name "$b@{upstream}" 2>/dev/null)
  set -e
  if [[ -z "$upstream" ]]; then
    echo "Setting upstream to $PRIMARY_REMOTE/$b"
    git branch --set-upstream-to="$PRIMARY_REMOTE/$b" "$b" >/dev/null 2>&1 || true
  fi

  local_sha=$(git rev-parse "$b")
  p_ref="$PRIMARY_REMOTE/$b"

  set +e
  p_sha=$(git rev-parse "$p_ref" 2>/dev/null)
  set -e

  if [[ -n "${p_sha:-}" ]]; then
    if ! is_ancestor "$p_sha" "$local_sha"; then
      fail "$b is behind $p_ref. Run: git pull --ff-only $PRIMARY_REMOTE $b"
    fi
  fi
  if [[ -n "$SECONDARY_REMOTE" ]]; then
    if [[ $FORCE_SECONDARY -eq 0 && $SNAPSHOT_SECONDARY -eq 0 ]]; then
      set +e
      s_sha=$(git rev-parse "$SECONDARY_REMOTE/$b" 2>/dev/null)
      set -e
      if [[ -n "${s_sha:-}" ]]; then
        if ! is_ancestor "$s_sha" "$local_sha"; then
          fail "$b is behind $SECONDARY_REMOTE/$b. Pass --force-secondary to override or --snapshot-secondary to push a history-free snapshot."
        fi
      fi
    fi
  fi

  echo "Pushing to $PRIMARY_REMOTE…"
  git push "$PRIMARY_REMOTE" "$b" --follow-tags --no-verify

  if [[ -n "$SECONDARY_REMOTE" ]]; then
    if [[ $SNAPSHOT_SECONDARY -eq 1 ]]; then
      echo "Pushing snapshot of $b to $SECONDARY_REMOTE (single commit, no history)…"
      tree=$(git write-tree)
      parent_arg=()
      # No parent -> orphan snapshot
      commit=$(echo "Snapshot sync of $b on $(date -u +%Y-%m-%dT%H:%M:%SZ)" | git commit-tree "$tree" "${parent_arg[@]}")
      git push "$SECONDARY_REMOTE" "$commit:refs/heads/$b" --force --no-verify
      echo "✓ Snapshot pushed to $SECONDARY_REMOTE/$b"
    else
      echo "Pushing to $SECONDARY_REMOTE…"
      if [[ $FORCE_SECONDARY -eq 1 ]]; then
        git push "$SECONDARY_REMOTE" "$b" --force-with-lease --follow-tags --no-verify
      else
        git push "$SECONDARY_REMOTE" "$b" --follow-tags --no-verify
      fi
      echo "✓ Synced $b to $PRIMARY_REMOTE and $SECONDARY_REMOTE"
    fi
  else
    echo "✓ Pushed $b to $PRIMARY_REMOTE (no secondary remote configured)"
  fi
done

echo -e "\nAll done."


