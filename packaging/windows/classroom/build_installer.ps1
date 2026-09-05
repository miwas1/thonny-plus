[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseVersion,

    [Parameter(Mandatory = $true)]
    [string]$BundlePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($ReleaseVersion -notmatch '^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$') {
    throw "ReleaseVersion must be 1-64 characters containing only letters, digits, dots, underscores, and hyphens."
}

$bundle = (Resolve-Path -LiteralPath $BundlePath).Path
$output = [System.IO.Path]::GetFullPath($OutputPath)
$definition = Join-Path $PSScriptRoot "classroom_installer.iss"

$required = @(
    "thonny\thonny.exe",
    "thonny\python.exe",
    "tutor\llama-server.exe",
    "tutor\qwen-coder-0.5b-q8_0.gguf"
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $bundle $relative) -PathType Leaf)) {
        throw "Installer input is incomplete: missing $relative"
    }
}

New-Item -ItemType Directory -Force -Path $output | Out-Null
if (Get-ChildItem -LiteralPath $output -Force) {
    throw "Refusing to write into non-empty output directory: $output"
}

$programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$isccCandidates = @(
    (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (-not $iscc) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $iscc = $command.Source
    }
}
if (-not $iscc) {
    throw "Inno Setup 6 (ISCC.exe) is required."
}

& $iscc "/DAppVersion=$ReleaseVersion" "/DSourceFolder=$bundle" "/DOutputFolder=$output" $definition
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

$installerName = "thonny-classroom-$ReleaseVersion-windows-x64-setup.exe"
$installer = Join-Path $output $installerName
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "Expected installer was not produced: $installer"
}

$digest = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
"$digest *$installerName" | Set-Content -LiteralPath "$installer.sha256" -Encoding ascii

$componentsSource = Join-Path $bundle "COMPONENTS.json"
Copy-Item -LiteralPath $componentsSource -Destination (Join-Path $output "COMPONENTS.json")

$gitCommit = $env:GITHUB_SHA
if ([string]::IsNullOrWhiteSpace($gitCommit)) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        $gitCommit = (& $git.Source -C $PSScriptRoot rev-parse HEAD 2>$null)
    }
    if ([string]::IsNullOrWhiteSpace($gitCommit)) { $gitCommit = "unknown" }
}
$buildRunId = if ([string]::IsNullOrWhiteSpace($env:GITHUB_RUN_ID)) { "local" } else { $env:GITHUB_RUN_ID }

$metadata = [ordered]@{
    version = $ReleaseVersion
    platform = "windows-x64"
    git_commit = $gitCommit
    build_run_id = $buildRunId
    installer = $installerName
    installer_sha256 = $digest
    installer_size_bytes = (Get-Item -LiteralPath $installer).Length
    created_utc = [DateTime]::UtcNow.ToString("o")
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output "release.json") -Encoding utf8

Write-Output "Built $installer"
Write-Output "SHA-256: $digest"
