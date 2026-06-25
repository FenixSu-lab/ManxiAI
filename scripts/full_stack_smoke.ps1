# Full-stack HTTP smoke test for local Django and Vite integration.
param(
    [int]$BackendPort = 18000,
    [int]$FrontendPort = 3100,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot 'frontend'
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$logDir = Join-Path $repoRoot 'tmp'

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$backendOut = Join-Path $logDir 'full_stack_backend.out.log'
$backendErr = Join-Path $logDir 'full_stack_backend.err.log'
$frontendOut = Join-Path $logDir 'full_stack_frontend.out.log'
$frontendErr = Join-Path $logDir 'full_stack_frontend.err.log'
Remove-Item -LiteralPath $backendOut, $backendErr, $frontendOut, $frontendErr -ErrorAction SilentlyContinue

function Test-HttpOk {
    param(
        [string]$Url,
        [string]$ContentPattern = ''
    )

    $bodyPath = Join-Path $logDir 'full_stack_http_body.tmp'
    try {
        $status = & curl.exe --max-time 5 --silent --location --output $bodyPath --write-out '%{http_code}' $Url
        if ($status -ne '200') {
            return $false
        }
        if ($ContentPattern) {
            $content = Get-Content -Raw $bodyPath -ErrorAction SilentlyContinue
            if ($content -notmatch $ContentPattern) {
                return $false
            }
        }
        return $true
    } catch {
        return $false
    } finally {
        Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
    }
}

function Test-ExpectedStatus {
    param(
        [string]$Url,
        [int]$ExpectedStatus
    )

    $bodyPath = Join-Path $logDir 'full_stack_http_status.tmp'
    try {
        $status = & curl.exe --max-time 5 --silent --location --output $bodyPath --write-out '%{http_code}' $Url
        return [int]$status -eq $ExpectedStatus
    } catch {
        return $false
    } finally {
        Remove-Item -LiteralPath $bodyPath -ErrorAction SilentlyContinue
    }
}

function Invoke-JsonRequest {
    param(
        [string]$Method,
        [string]$Url,
        [int]$ExpectedStatus,
        [object]$Body = $null,
        [string]$Token = ''
    )

    $requestPath = Join-Path $logDir 'full_stack_request.json'
    $responsePath = Join-Path $logDir 'full_stack_response.json'
    Remove-Item -LiteralPath $requestPath, $responsePath -ErrorAction SilentlyContinue

    $curlArgs = @(
        '--max-time', '20',
        '--silent',
        '--location',
        '--request', $Method,
        '--header', 'Content-Type: application/json'
    )
    if ($Token) {
        $curlArgs += @('--header', "Authorization: Token $Token")
    }
    if ($null -ne $Body) {
        $jsonBody = $Body | ConvertTo-Json -Compress
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($requestPath, $jsonBody, $utf8NoBom)
        $curlArgs += @('--data-binary', "@$requestPath")
    }
    $curlArgs += @('--output', $responsePath, '--write-out', '%{http_code}', $Url)

    try {
        $status = & curl.exe @curlArgs
        $content = Get-Content -Raw $responsePath -ErrorAction SilentlyContinue
        if ([int]$status -ne $ExpectedStatus) {
            throw "Expected $ExpectedStatus from $Method $Url, got $status. Body: $content"
        }
        if ($content) {
            return $content | ConvertFrom-Json
        }
        return $null
    } finally {
        Remove-Item -LiteralPath $requestPath, $responsePath -ErrorAction SilentlyContinue
    }
}

<#
Legacy implementation kept out of the command path for reference:
PowerShell Invoke-WebRequest throws on expected 401 responses and can be
inconsistent with Vite dev-server readiness in non-interactive processes.
#>
function Test-ExpectedStatusWithInvokeWebRequest {
    param(
        [string]$Url,
        [int]$ExpectedStatus
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
        return $response.StatusCode -eq $ExpectedStatus
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        return $status -eq $ExpectedStatus
    }
}

function Test-HttpOkWithInvokeWebRequest {
    param(
        [string]$Url,
        [string]$ContentPattern = ''
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 3
        if ($response.StatusCode -ne 200) {
            return $false
        }
        if ($ContentPattern -and ($response.Content -notmatch $ContentPattern)) {
            return $false
        }
        return $true
    } catch {
        return $false
    }
}

function Wait-HttpReady {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ContentPattern = '',
        [string]$ErrorLog
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk $Url $ContentPattern) {
            return
        }
        Start-Sleep -Milliseconds 500
    }

    $details = Get-Content -Raw $ErrorLog -ErrorAction SilentlyContinue
    if ($Name -eq 'Django backend' -and $details -match 'could not connect to server|OperationalError|Connection timed out') {
        $details = @"
$details

Likely cause: Django started correctly but could not reach the configured database.
Check DB_HOST, DB_PORT, network reachability, PostgreSQL service status, and pg_hba/firewall rules.
If you only want to test frontend build output, run npm run build instead of full-stack smoke.
"@
    }
    throw "$Name did not become ready within $TimeoutSeconds seconds. Error log: $details"
}

$backendProcess = $null
$frontendProcess = $null

function Stop-SmokeProcessTree {
    param(
        [int]$ProcessId,
        [int]$Port
    )

    Get-CimInstance Win32_Process |
        Where-Object {
            ($_.ProcessId -eq $ProcessId) -or
            ($_.CommandLine -match "127\.0\.0\.1:$Port") -or
            ($_.CommandLine -match "--port $Port")
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

try {
    $backendProcess = Start-Process `
        -FilePath (Join-Path $repoRoot 'env\Scripts\python.exe') `
        -ArgumentList @('manage.py', 'runserver', "127.0.0.1:$BackendPort", '--noreload') `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $backendOut `
        -RedirectStandardError $backendErr `
        -PassThru `
        -WindowStyle Hidden

    $frontendProcess = Start-Process `
        -FilePath 'powershell.exe' `
        -ArgumentList @(
            '-NoProfile',
            '-Command',
            "`$env:VITE_API_PROXY_TARGET='$backendUrl'; npm.cmd run dev -- --host 127.0.0.1 --port $FrontendPort"
        ) `
        -WorkingDirectory $frontendRoot `
        -RedirectStandardOutput $frontendOut `
        -RedirectStandardError $frontendErr `
        -PassThru `
        -WindowStyle Hidden

    Wait-HttpReady -Name 'Django backend' -Url "$backendUrl/api/v1/health/" -ContentPattern '"status":"ok"|status.:.ok' -ErrorLog $backendErr

    Wait-HttpReady -Name 'Vite frontend' -Url "$frontendUrl/" -ErrorLog $frontendErr

    if (-not (Test-ExpectedStatus "$frontendUrl/api/v1/knowledge-bases/" 401)) {
        throw 'Expected Vite /api proxy to return 401 for unauthenticated knowledge-base list.'
    }

    $accountSuffix = [guid]::NewGuid().ToString('N').Substring(0, 12)
    $email = "fullstack-smoke-$accountSuffix@example.com"
    $username = "smoke$accountSuffix"
    $password = 'SmokePass123!'

    Invoke-JsonRequest `
        -Method 'POST' `
        -Url "$frontendUrl/api/v1/auth/users/" `
        -ExpectedStatus 201 `
        -Body @{
            email = $email
            username = $username
            password = $password
            confirm_password = $password
        } | Out-Null

    $login = Invoke-JsonRequest `
        -Method 'POST' `
        -Url "$frontendUrl/api/v1/auth/users/login/" `
        -ExpectedStatus 200 `
        -Body @{
            email = $email
            password = $password
        }

    if (-not $login.token) {
        throw 'Login response did not include a DRF token.'
    }

    Invoke-JsonRequest `
        -Method 'GET' `
        -Url "$frontendUrl/api/v1/auth/users/me/" `
        -ExpectedStatus 200 `
        -Token $login.token | Out-Null

    $dashboard = Invoke-JsonRequest `
        -Method 'GET' `
        -Url "$frontendUrl/api/v1/dashboard/summary/" `
        -ExpectedStatus 200 `
        -Token $login.token

    if ($null -eq $dashboard.knowledge_base_count) {
        throw 'Dashboard summary response did not include knowledge_base_count.'
    }

    Invoke-JsonRequest `
        -Method 'GET' `
        -Url "$frontendUrl/api/v1/health/" `
        -ExpectedStatus 200 | Out-Null

    Write-Output "Full-stack HTTP smoke OK. backend=$backendUrl frontend=$frontendUrl email=$email"
} finally {
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-SmokeProcessTree -ProcessId $frontendProcess.Id -Port $FrontendPort
    }
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-SmokeProcessTree -ProcessId $backendProcess.Id -Port $BackendPort
    }
}
