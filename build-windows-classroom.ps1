#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$')]
    [string]$ReleaseVersion,

    [string]$PythonCommand = "python",

    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw "This installer build script must run on Windows."
}
if (-not [Environment]::Is64BitOperatingSystem) {
    throw "A 64-bit Windows server is required."
}

$repository = $PSScriptRoot
$buildsRoot = Join-Path $repository ".classroom-build"
$buildRoot = Join-Path $buildsRoot $ReleaseVersion
$bundle = Join-Path $buildRoot "app"
$output = Join-Path $buildRoot "release"
$cache = Join-Path $repository ".classroom-cache"
$classroomTools = Join-Path $repository "packaging\windows\classroom"
$checksums = Join-Path $buildRoot "checksums.json"
Set-Location -LiteralPath $repository

$resumeStagedBundle = $false
if (Test-Path -LiteralPath $buildRoot) {
    if (-not $Force) {
        $hasStagedBundle = (Test-Path -LiteralPath $bundle -PathType Container) -and (Test-Path -LiteralPath $checksums -PathType Leaf)
        $hasReleaseOutput = Test-Path -LiteralPath $output
        if ($hasStagedBundle -and -not $hasReleaseOutput) {
            $resumeStagedBundle = $true
            Write-Host "Resuming the verified staged bundle in $buildRoot"
        }
        else {
            throw "Build output is incomplete or already contains release output: $buildRoot. Use -Force to rebuild this exact version."
        }
    }
    else {
        $resolvedBuildsRoot = [System.IO.Path]::GetFullPath($buildsRoot).TrimEnd('\')
        $resolvedBuildRoot = [System.IO.Path]::GetFullPath($buildRoot)
        if (-not $resolvedBuildRoot.StartsWith($resolvedBuildsRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean a path outside .classroom-build."
        }
        Remove-Item -LiteralPath $resolvedBuildRoot -Recurse -Force
    }
}

$pythonCommandInfo = Get-Command $PythonCommand -ErrorAction SilentlyContinue
if (-not $pythonCommandInfo) {
    throw "Python 3.13 x64 was not found. Install it and ensure '$PythonCommand' resolves to python.exe."
}
$python = $pythonCommandInfo.Source
$pythonInfo = & $python -c "import json,struct,sys; print(json.dumps({'version': list(sys.version_info[:3]), 'bits': struct.calcsize('P') * 8}))"
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect build Python: $python"
}
$pythonDetails = $pythonInfo | ConvertFrom-Json
if ($pythonDetails.version[0] -ne 3 -or $pythonDetails.version[1] -ne 13 -or $pythonDetails.bits -ne 64) {
    throw "The build requires Python 3.13 x64. Found $($pythonDetails.version -join '.') ($($pythonDetails.bits)-bit)."
}
& $python -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "pip is required in the build Python."
}

$programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$isccCandidates = @(
    (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (-not $iscc -and -not (Get-Command ISCC.exe -ErrorAction SilentlyContinue)) {
    throw "Inno Setup 6 is required. Install it from https://jrsoftware.org/isinfo.php before running this script."
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

Write-Host "[1/5] Running source tests"
& $python -m unittest -v test_classroom.py test_classroom_model.py test_classroom_packaging.py
if ($LASTEXITCODE -ne 0) { throw "Source tests failed." }
& $python -m compileall -q thonny/plugins
if ($LASTEXITCODE -ne 0) { throw "Python compile check failed." }

Write-Host "[2/5] Downloading and checksum-verifying Python and local AI"
if ($resumeStagedBundle) {
    Write-Host "Refreshing application source in the existing staged bundle."
    & $python (Join-Path $classroomTools "stage_bundle.py") --app $bundle --refresh-source
    if ($LASTEXITCODE -ne 0) { throw "Application source refresh failed." }
    Write-Host "Runtime and model downloads are skipped; Python dependencies are refreshed."
}
else {
    & $python (Join-Path $classroomTools "stage_bundle.py") --app $bundle --cache $cache
    if ($LASTEXITCODE -ne 0) { throw "Bundle staging failed." }
}

Write-Host "[3/5] Verifying the complete private bundle"
& $python (Join-Path $classroomTools "verify_release.py") $bundle $checksums
if ($LASTEXITCODE -ne 0) { throw "Bundle verification failed." }

Write-Host "[4/5] Running bundled Python and persistent Qwen smoke tests"
& $python (Join-Path $classroomTools "smoke_bundle.py") $bundle --with-model
if ($LASTEXITCODE -ne 0) { throw "Runtime or Qwen smoke test failed." }

Write-Host "[5/5] Building the Windows installer"
& (Join-Path $classroomTools "build_installer.ps1") `
    -ReleaseVersion $ReleaseVersion `
    -BundlePath $bundle `
    -OutputPath $output
if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }

$installer = Join-Path $output "thonny-classroom-$ReleaseVersion-windows-x64-setup.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "Build completed without the expected installer: $installer"
}

Write-Host ""
Write-Host "Installer created: $installer" -ForegroundColor Green
Write-Host "SHA-256 file: $installer.sha256"
Write-Host "The staged Qwen model and installer are inside Git-ignored build directories."
