<<<<<<< HEAD
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
=======
<#
  sync-remotes.ps1
  Pull from 'origin' (Gitea) then push to 'github' (GitHub) for the current branch.
  - FF-only pull from origin
  - Block push if any tracked file > 100MB
#>

# --- helpers ---
function Fail([string]$msg) {
    Write-Host "`nERROR: $msg`n" -ForegroundColor Red
    exit 1
}

function Run-Git-Command {
    param([string]$Command, [string]$OnError)
    Write-Host "Running: git $Command" -ForegroundColor Yellow
    Invoke-Expression "git $Command"
    if ($LASTEXITCODE -ne 0) { Fail $OnError }
}

# --- preconditions ---
& git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { Fail "Not a git repository." }

& git diff-index --quiet HEAD -- 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Uncommitted changes. Commit or stash first." }

$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -eq "HEAD" -or [string]::IsNullOrWhiteSpace($branch)) {
    Fail "Detached HEAD. Checkout a branch first."
}

$remotes = (& git remote) -split "`n"
if (-not ($remotes -contains "origin")) { Fail "Remote 'origin' (Gitea) not found." }
if (-not ($remotes -contains "github")) { Fail "Remote 'github' (GitHub) not found." }

# --- 1) pull from origin (FF-only) ---
Write-Host "Fetching from origin..." -ForegroundColor Cyan
Run-Git-Command "fetch origin --prune" "Fetch from origin failed."

Write-Host "Pulling from origin/$branch (ff-only)..." -ForegroundColor Cyan
Run-Git-Command "pull --ff-only origin $branch" "Pull from origin failed."

# --- 2) large file guard (>100MB) ---
$largeFiles = @()
$lstree = & git ls-tree -r -l HEAD
foreach ($line in $lstree) {
    $parts = $line -split '\s+'
    if ($parts.Count -ge 4) {
        $size = 0L
        [void][int64]::TryParse($parts[3], [ref]$size)
        if ($size -gt 104857600) { $largeFiles += $line }
    }
}
if ($largeFiles.Count -gt 0) {
    Write-Host "`nERROR: Large tracked files detected (>100MB). Push aborted." -ForegroundColor Red
    $largeFiles | ForEach-Object { Write-Host $_ }
    Fail "Remove these from history (e.g., with 'git filter-repo') before pushing to GitHub."
}

# --- 3) push to github ---
Write-Host "Pushing '$branch' to github..." -ForegroundColor Cyan
Run-Git-Command "push github $branch" "Push to GitHub failed."

Write-Host "`nDone: pulled from origin, pushed to github for '$branch'." -ForegroundColor Green
>>>>>>> 0ca96dda42fddc49b79034afc5c153690d237396
