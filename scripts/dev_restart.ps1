# Restart local Django and Vite development servers with deterministic ports.
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$TimeoutSeconds = 90,
    [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot 'frontend'
$pythonPath = Join-Path $repoRoot 'env\Scripts\python.exe'
$logDir = Join-Path $repoRoot 'tmp'
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$backendOut = Join-Path $logDir 'dev_backend.out.log'
$backendErr = Join-Path $logDir 'dev_backend.err.log'
$frontendOut = Join-Path $logDir 'dev_frontend.out.log'
$frontendErr = Join-Path $logDir 'dev_frontend.err.log'
Remove-Item -LiteralPath $backendOut, $backendErr, $frontendOut, $frontendErr -ErrorAction SilentlyContinue

function Stop-ExistingDevServers {
    # Stop stale Django and Vite processes for this workspace.
    Get-CimInstance Win32_Process |
        Where-Object {
            ($_.CommandLine -like "*$repoRoot*" -and $_.CommandLine -like '*manage.py runserver*') -or
            ($_.CommandLine -like "*$frontendRoot*" -and $_.CommandLine -match 'vite')
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

function Test-HttpStatus {
    param(
        [string]$Url,
        [int]$ExpectedStatus,
        [int]$MaxTimeSeconds = 5
    )

    $bodyPath = Join-Path $logDir 'dev_http_body.tmp'
    try {
        $status = & curl.exe --max-time $MaxTimeSeconds --silent --location --output $bodyPath --write-out '%{http_code}' $Url
        return [int]$status -eq $ExpectedStatus
    } catch {
        return $false
    } finally {
        Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
    }
}

function Wait-HttpStatus {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus,
        [string]$ErrorLog
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpStatus -Url $Url -ExpectedStatus $ExpectedStatus) {
            return
        }
        Start-Sleep -Milliseconds 500
    }

    $details = Get-Content -Raw $ErrorLog -ErrorAction SilentlyContinue
    throw "$Name did not become ready at $Url within $TimeoutSeconds seconds. Error log: $details"
}

if (-not (Test-Path $pythonPath)) {
    throw "Python virtualenv not found at $pythonPath. Create env and install requirements first."
}

Stop-ExistingDevServers

if (-not $SkipChecks) {
    & $pythonPath manage.py check
    & $pythonPath manage.py check_db_latency
    & $pythonPath manage.py smoke_auth_flow
}

$backendProcess = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList @('manage.py', 'runserver', "0.0.0.0:$BackendPort", '--noreload') `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru `
    -WindowStyle Hidden

$frontendProcess = Start-Process `
    -FilePath 'powershell.exe' `
    -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        "`$env:VITE_API_PROXY_TARGET='$backendUrl'; npm.cmd run dev -- --host 0.0.0.0 --port $FrontendPort --strictPort"
    ) `
    -WorkingDirectory $frontendRoot `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -PassThru `
    -WindowStyle Hidden

Wait-HttpStatus -Name 'Django backend' -Url "$backendUrl/api/v1/health/" -ExpectedStatus 200 -ErrorLog $backendErr
Wait-HttpStatus -Name 'Vite frontend' -Url "$frontendUrl/" -ExpectedStatus 200 -ErrorLog $frontendErr
Wait-HttpStatus -Name 'Vite API proxy' -Url "$frontendUrl/api/v1/auth/users/me/" -ExpectedStatus 401 -ErrorLog $frontendErr

Write-Output "Development servers started."
Write-Output "Backend:  $backendUrl"
Write-Output "Frontend: $frontendUrl"
Write-Output "Backend logs:  $backendOut / $backendErr"
Write-Output "Frontend logs: $frontendOut / $frontendErr"
Write-Output "Process IDs: backend=$($backendProcess.Id) frontend_launcher=$($frontendProcess.Id)"
