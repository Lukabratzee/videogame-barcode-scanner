<#
  sync_origin_to_github.ps1
  Pulls current branch from 'origin' (fast-forward only), then pushes to 'github'.
  - Fails if working tree is dirty
  - Fails if histories are unrelated (asks you to reset once)
  - Sets upstream to origin/<branch> for convenience
#>

param(
  [switch]$IncludeTags  # push tags with --follow-tags
)

function Fail([string]$msg) {
  Write-Host "`nERROR: $msg`n" -ForegroundColor Red
  exit 1
}

function Run-Git {
  param([string[]]$Args, [string]$OnError)
  & git @Args
  if ($LASTEXITCODE -ne 0) { Fail $OnError }
}

# 0) Must be inside a git repo
& git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { Fail "Not a git repository." }

# 1) Clean working tree
& git diff-index --quiet HEAD -- 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Uncommitted changes. Commit or stash first." }

# 2) Identify current branch (not detached)
$branch = (& git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -eq "HEAD" -or [string]::IsNullOrWhiteSpace($branch)) {
  Fail "Detached HEAD. Checkout a branch first."
}

# 3) Ensure remotes exist
$remotes = (& git remote) -split "`n"
if ($null -eq ($remotes | Where-Object { $_ -eq 'origin' })) { Fail "Remote 'origin' not found." }
if ($null -eq ($remotes | Where-Object { $_ -eq 'github' })) { Fail "Remote 'github' not found." }

Write-Host "Fetching from origin and github..." -ForegroundColor Cyan
Run-Git @('fetch','origin','--prune') "Fetch from origin failed."
Run-Git @('fetch','github','--prune') "Fetch from github failed."

# 4) Remote branch must exist on origin
$originRef = "origin/$branch"
$originSha = (& git rev-parse $originRef 2>$null).Trim()
if (-not $originSha) {
  Fail "Remote branch '$originRef' does not exist. Create it on origin or push there first."
}

# 5) Check relationship between local and origin
& git merge-base --is-ancestor $originRef $branch 2>$null
$localContainsOrigin = ($LASTEXITCODE -eq 0)   # local is ahead or equal

& git merge-base --is-ancestor $branch $originRef 2>$null
$originContainsLocal = ($LASTEXITCODE -eq 0)   # origin is ahead or equal

if (-not ($localContainsOrigin -or $originContainsLocal)) {
  Fail "Unrelated histories between '$branch' and '$originRef'.
Run these once to align local with origin:

  git branch backup/$branch-before-reset
  git reset --hard $originRef

Then re-run this script."
}

# 6) If origin is ahead, fast-forward local
if (-not $localContainsOrigin) {
  Write-Host "Fast-forwarding local '$branch' to '$originRef'..." -ForegroundColor Yellow
  Run-Git @('merge','--ff-only',$originRef) "Fast-forward merge failed."
} else {
  Write-Host "Local '$branch' is up to date with '$originRef'." -ForegroundColor Green
}

# 7) Ensure upstream to origin
& git branch --set-upstream-to=$originRef $branch *> $null

# 8) Push to GitHub
Write-Host "Pushing '$branch' to github..." -ForegroundColor Cyan
if ($IncludeTags) {
  Run-Git @('push','github',$branch,'--follow-tags') "Push to github failed."
} else {
  Run-Git @('push','github',$branch) "Push to github failed."
}

Write-Host "`nDone: pulled from origin then pushed to github for '$branch'." -ForegroundColor Green
