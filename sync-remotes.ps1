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
