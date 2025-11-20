<#
run-local.ps1
Single-command PowerShell helper to build and run the API + optional Streamlit using Docker.

Usage:
  .\run-local.ps1          # builds and runs (attached)
  .\run-local.ps1 -Detach  # runs services detached (background)

Notes:
- Requires Docker (and Docker daemon) available on the machine.
- If `docker-compose.yml` exists the script will prefer compose; otherwise it runs the image directly.
- Creates a `models/` directory if missing and writes a README placeholder.
#>

param(
    [switch]
    $Detach,
    [switch]
    $WithDummyModel
)

try {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
} catch {
    $scriptRoot = Get-Location
}

Write-Host "Project root: $scriptRoot"

# Check Docker CLI
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker CLI not found. Install Docker Desktop and ensure 'docker' is on PATH."
    exit 1
}

# Check Docker daemon
Write-Host "Checking Docker daemon..."
try {
    docker info > $null 2>&1
} catch {
    Write-Error "Docker daemon doesn't seem to be running. Start Docker Desktop and try again."
    exit 2
}

# Ensure models dir exists
$modelsDir = Join-Path $scriptRoot 'models'
if (-not (Test-Path $modelsDir)) {
    Write-Host "Creating models directory: $modelsDir"
    New-Item -ItemType Directory -Path $modelsDir | Out-Null
    $readmePath = Join-Path $modelsDir 'README.txt'
    @"
Place your production model files in this directory.
Example filenames expected by the repository:
 - disease_xgb.pkl
 - label_encoder.pkl

If you don't have model files yet, you can run the mock server provided in `mock_predict_server.py` for local testing.
"@ | Set-Content -Path $readmePath -Encoding UTF8
    Write-Host "Wrote placeholder README at: $readmePath"
} else {
    Write-Host "Found existing models directory: $modelsDir"
}

# Optionally create small dummy model files so the app/container can start without production models
if ($WithDummyModel) {
    Write-Host "--with-dummy-model requested: creating small dummy model files in $modelsDir"
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $py = @"
import pickle, pathlib
p_dir = pathlib.Path(r'{0}')
p_dir.mkdir(parents=True, exist_ok=True)
with (p_dir / 'disease_xgb.pkl').open('wb') as f:
    pickle.dump({{'is_dummy': True}}, f)
with (p_dir / 'label_encoder.pkl').open('wb') as f:
    pickle.dump({{'classes': ['dummy']}}, f)
print('dummy-models-written')
"@ -f $modelsDir
        try {
            & python -c $py 2>$null
            Write-Host "Created Python pickled dummy models in: $modelsDir"
        } catch {
            Write-Warning "Python invocation failed while creating pickles. Falling back to text placeholders."
            Set-Content -Path (Join-Path $modelsDir 'disease_xgb.pkl') -Value 'DUMMY_PICKLE' -Encoding ASCII
            Set-Content -Path (Join-Path $modelsDir 'label_encoder.pkl') -Value 'DUMMY_PICKLE' -Encoding ASCII
        }
    } else {
        Write-Warning "Python not found: creating text placeholder model files instead."
        Set-Content -Path (Join-Path $modelsDir 'disease_xgb.pkl') -Value 'DUMMY_PICKLE' -Encoding ASCII
        Set-Content -Path (Join-Path $modelsDir 'label_encoder.pkl') -Value 'DUMMY_PICKLE' -Encoding ASCII
    }
}

# Build docker image
Write-Host "Building Docker image 'mediscan-api:latest'..."
$buildCmd = "docker build -t mediscan-api:latest `"$scriptRoot`""
Write-Host $buildCmd
$buildResult = & docker build -t mediscan-api:latest $scriptRoot
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Compose vs direct run
$composeFile = Join-Path $scriptRoot 'docker-compose.yml'
if (Test-Path $composeFile) {
    Write-Host "Using docker-compose at: $composeFile"
    # prefer 'docker-compose' when available, otherwise use 'docker compose'
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $composeExe = 'docker-compose'
    } else {
        $composeExe = 'docker compose'
    }

    $composeCmd = "$composeExe -f `"$composeFile`" up --build"
    if ($Detach) { $composeCmd += ' -d' }

    Write-Host "Running: $composeCmd"
    iex $composeCmd
} else {
    Write-Host "No docker-compose.yml found — running container directly (mapped ports 8000 -> 8000)."
    $runCmd = "docker run -it --rm -p 8000:8000 -v `"$scriptRoot`":/app -v `"$modelsDir`":/app/models mediscan-api:latest"
    Write-Host "Running: $runCmd"
    iex $runCmd
}

# If not detached, open browser to API docs and Streamlit (if present)
if (-not $Detach) {
    Start-Sleep -Seconds 3
    Write-Host "Opening FastAPI docs at http://localhost:8000/docs (if available)..."
    try { Start-Process "http://localhost:8000/docs" } catch {}

    if (Test-Path (Join-Path $scriptRoot 'streamlit_app.py')) {
        Write-Host "Detected Streamlit app — opening http://localhost:8501"
        try { Start-Process "http://localhost:8501" } catch {}
    }
}

Write-Host "Done. Use Ctrl+C to stop foreground compose run, or 'docker-compose down' to tear down detached services." 
exit 0
