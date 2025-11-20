<#
install-docker.ps1

Helper to install Docker Desktop on Windows using `winget` when available,
otherwise downloads the official Docker Desktop installer and launches it.

Run as Administrator. The script will attempt to re-launch itself as admin when needed.

Usage:
  .\install-docker.ps1

Notes:
- This script cannot run here — run it locally in an elevated PowerShell session.
- Installing Docker Desktop may require a reboot and enabling WSL2/Virtualization.
- For WSL2, modern Windows 10/11 support `wsl --install` which this script suggests.
#>

function Ensure-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Re-launching as administrator..."
        Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        exit
    }
}

function Test-DockerInstalled {
    return (Get-Command docker -ErrorAction SilentlyContinue) -ne $null
}

function Install-With-Winget {
    Write-Host "Attempting to install Docker Desktop using winget..."
    $args = @('install','-e','--id','Docker.DockerDesktop','--accept-package-agreements','--accept-source-agreements')
    $proc = Start-Process -FilePath winget -ArgumentList $args -NoNewWindow -Wait -PassThru
    return $proc.ExitCode -eq 0
}

function Download-And-Run-Installer {
    $url = 'https://desktop.docker.com/win/stable/amd64/Docker%20Desktop%20Installer.exe'
    $tmp = Join-Path $env:TEMP 'DockerDesktopInstaller.exe'
    Write-Host "Downloading Docker Desktop installer to: $tmp"
    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Error "Failed to download installer. Please visit https://www.docker.com/get-started to download manually."
        return $false
    }

    Write-Host "Launching installer (you may need to follow GUI prompts)..."
    try {
        Start-Process -FilePath $tmp -Verb RunAs
        return $true
    } catch {
        Write-Error "Failed to launch installer: $_"
        return $false
    }
}

function Ensure-WSL2 {
    Write-Host "Checking for WSL support and current settings..."
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        try {
            $wslVersion = wsl -l -v 2>&1 | Out-String
            if ($wslVersion -match 'WSL version') {
                Write-Host "WSL available. You can install a distro with: wsl --install"
            }
        } catch {
            Write-Host "WSL exists but could not enumerate distros. You may need to run 'wsl --install' or enable WSL components."
        }
    } else {
        Write-Host "WSL not present. To use WSL2 backend you can run (from an elevated prompt):`n  wsl --install`"
    }
}

# === Script start ===

Write-Host "install-docker.ps1 — Docker Desktop installer helper\n"

# Ensure running as admin
Ensure-Admin

# Quick check: already installed?
if (Test-DockerInstalled) {
    Write-Host "Docker already installed. Version:"
    docker --version
    exit 0
}

# Try winget install path
if (Get-Command winget -ErrorAction SilentlyContinue) {
    $ok = Install-With-Winget
    if ($ok) {
        Write-Host "winget installation attempted. Waiting briefly for Docker to register..."
        Start-Sleep -Seconds 6
        if (Test-DockerInstalled) {
            Write-Host "Docker installed successfully. Version:"
            docker --version
            Ensure-WSL2
            exit 0
        } else {
            Write-Warning "Docker not found after winget install. You may need to restart or run Docker Desktop once."
        }
    } else {
        Write-Warning "winget install failed or was cancelled. Falling back to downloading installer."
    }
} else {
    Write-Host "winget not found on this system — attempting to download the official installer."
}

# Fallback: download and run GUI installer
$dlOk = Download-And-Run-Installer
if (-not $dlOk) {
    Write-Error "Automatic download/install failed. Please manually download Docker Desktop from https://www.docker.com/get-started"
    exit 1
}

Write-Host "Installer launched. After installation completes, please start Docker Desktop and verify with:`n  docker --version`

Ensure-WSL2

Write-Host "If Docker uses WSL2 backend you may need to enable Virtualization in BIOS and reboot." 
Write-Host "Script finished (installer launched)."
exit 0
