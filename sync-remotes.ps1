param(
  [string]$Primary = "origin",      # your Gitea remote
  [string]$Secondary = "github",    # your GitHub remote
  [string]$Branch = "",             # empty = current branch
  [switch]$All                      # push all local branches that exist
)

function Fail($msg) { Write-Host "`nERROR: $msg`n" -ForegroundColor Red; exit 1 }

# 1) Must be clean
git diff-index --quiet HEAD -- 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Uncommitted changes. Commit/stash first." }

# 2) Fetch everything
git fetch --all --prune || Fail "Fetch failed."

# Helper to check fast-forward status
function IsAncestor($maybeAncestor, $maybeDescendant) {
  git merge-base --is-ancestor $maybeAncestor $maybeDescendant 2>$null
  return ($LASTEXITCODE -eq 0)
}

# Determine branches to process
if ($All) {
  $branches = (git for-each-ref --format="%(refname:short)" refs/heads/) -split "`n" | Where-Object { $_ -ne "" }
} else {
  if (-not $Branch) { $Branch = (git rev-parse --abbrev-ref HEAD).Trim() }
  $branches = @($Branch)
}

foreach ($b in $branches) {
  Write-Host "`n== $b ==" -ForegroundColor Cyan

  # Ensure upstream to Primary if missing
  $upstream = (git rev-parse --abbrev-ref --symbolic-full-name $b@{upstream} 2>$null).Trim()
  if (-not $upstream) {
    Write-Host "Setting upstream to $Primary/$b"
    git branch --set-upstream-to="$Primary/$b" $b 2>$null | Out-Null
  }

  # Resolve SHAs (missing remote branch is okay for first push)
  $local = (git rev-parse $b).Trim()
  $pRef = "$Primary/$b"
  $sRef = "$Secondary/$b"
  $pSha = (git rev-parse $pRef 2>$null).Trim()
  $sSha = (git rev-parse $sRef 2>$null).Trim()

  # If remote branch exists, ensure it’s an ancestor of local (fast-forward only)
  if ($pSha -and -not (IsAncestor $pSha $local)) { Fail "$b is behind $pRef. Run: git pull --ff-only $Primary $b" }
  if ($sSha -and -not (IsAncestor $sSha $local)) { Fail "$b is behind $sRef. First bring $Secondary up to date or pull/merge." }

  # Push fast-forward only to both remotes
  Write-Host "Pushing to $Primary…" -ForegroundColor Green
  git push $Primary $b --follow-tags --no-verify || Fail "Push to $Primary failed."

  Write-Host "Pushing to $Secondary…" -ForegroundColor Green
  git push $Secondary $b --follow-tags --no-verify || Fail "Push to $Secondary failed."

  Write-Host "✓ Synced $b to $Primary and $Secondary"
}

Write-Host "`nAll done." -ForegroundColor Green