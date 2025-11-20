<#
push-to-github.ps1

Helper to initialize a git repo, make an initial commit, and push to GitHub.

Usage examples:
  # Create a repo using gh (recommended) with current folder name, public
  .\push-to-github.ps1

  # Create a private repo and force gh usage
  .\push-to-github.ps1 -Private -UseGH

  # Create a repo named my-repo (uses gh if available)
  .\push-to-github.ps1 -RepoName my-repo

Notes:
- This script will not store or transmit credentials itself; if using `gh` or `git push` you'll be prompted to authenticate.
- If you don't have `gh` (GitHub CLI), the script will provide the git commands to run after you create a remote repository on GitHub.
- Run from the project root (where this script lives).
#>

param(
    [string]$RepoName = "",
    [switch]$Private,
    [switch]$UseGH,
    [string]$RemoteUrl = ""
)

try {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
} catch {
    $scriptRoot = Get-Location
}
Set-Location $scriptRoot

function Ensure-Git {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "git is not installed or not on PATH. Install Git from https://git-scm.com/downloads and try again."
        exit 1
    }
}

function In-GitRepo {
    try {
        git rev-parse --is-inside-work-tree > $null 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

Ensure-Git

# Repo name default: folder name
if (-not $RepoName -or $RepoName -eq '') {
    $RepoName = Split-Path -Leaf (Get-Location)
}

# Ensure models/.gitkeep exists so models dir can be committed if needed
$modelsDir = Join-Path $scriptRoot 'models'
if (Test-Path $modelsDir) {
    $keep = Join-Path $modelsDir '.gitkeep'
    if (-not (Test-Path $keep)) {
        New-Item -ItemType File -Path $keep -Force | Out-Null
        Write-Host "Created $keep to allow committing the (ignored) models/ directory as a placeholder."
    }
}

# Initialize repo if needed
if (-not (In-GitRepo)) {
    Write-Host "Initializing a new git repository..."
    git init
} else {
    Write-Host "Repository already initialized."
}

# Create .gitignore if missing (safe-guard) - do not overwrite existing
if (-not (Test-Path (Join-Path $scriptRoot '.gitignore'))) {
    @"
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.env
models/
outputs/
reports/
.vscode/
.idea/
*.log
"@ | Set-Content -Path (Join-Path $scriptRoot '.gitignore') -Encoding UTF8
    Write-Host "Wrote basic .gitignore"
}

# Stage and commit
Write-Host "Staging files..."
git add -A

# Commit only if there are staged changes
$hasChanges = (git status --porcelain) -ne ''
if ($hasChanges) {
    git commit -m "chore: initial commit"
    Write-Host "Committed initial snapshot."
} else {
    Write-Host "No changes to commit."
}

# Try to create remote & push using gh if available (and requested)
$ghAvailable = (Get-Command gh -ErrorAction SilentlyContinue) -ne $null
if ($ghAvailable -and ($UseGH -or -not $UseGH -and $true)) {
    Write-Host "Attempting to create GitHub repo using GitHub CLI (gh)..."
    $visibility = $Private ? '--private' : '--public'
    $createCmd = "gh repo create `"$RepoName`" $visibility --source . --remote origin --push --confirm"
    Write-Host $createCmd
    try {
        iex $createCmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Repository created and pushed to GitHub as '$RepoName'."
                # If a RemoteUrl was provided, still ensure origin points to it
                if ($RemoteUrl -ne '') {
                    git remote remove origin 2>$null
                    git remote add origin $RemoteUrl
                    git push -u origin main
                    Write-Host "Pushed to provided remote: $RemoteUrl"
                }
                exit 0
        } else {
            Write-Warning "gh repo create returned exit code $LASTEXITCODE. Falling back to manual remote setup guidance."
        }
    } catch {
        Write-Warning "gh CLI invocation failed: $_. Falling back to manual remote setup guidance."
    }
} else {
    Write-Host "GitHub CLI (gh) not found or not requested. Will provide manual steps to add a remote."
}

# If we reach here, gh wasn't used successfully. Provide manual steps.
Write-Host "\nManual push instructions:"
Write-Host "1) Create a new empty repository on GitHub (https://github.com/new) named: $RepoName"
Write-Host "2) After creating the repo on GitHub, add the remote and push with the following commands (replace <your-remote-url>):\n"

Write-Host "git remote add origin https://github.com/<your-username>/$RepoName.git"
Write-Host "git branch -M main"
Write-Host "git push -u origin main"

Write-Host "\nIf you'd like, copy-and-paste the remote URL here and I can print the exact commands for you." 
exit 0
