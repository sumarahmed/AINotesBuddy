param(
    [string]$Python = "python",
    [string]$Version = "0.1.0",
    [switch]$RequireModels,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$desktopRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $desktopRoot
$outputRoot = Join-Path $desktopRoot "out"
$releaseRoot = Join-Path $desktopRoot "release"
$modelRoot = Join-Path $desktopRoot "models"
$specPath = Join-Path $desktopRoot "NotesBuddyCompanion.spec"

if ($RequireModels) {
    $requiredModels = @(
        (Join-Path $modelRoot "faster-whisper-small"),
        (Join-Path $modelRoot "speaker-diarization-community-1"),
        (Join-Path $modelRoot "MODEL_MANIFEST.json")
    )
    foreach ($requiredModel in $requiredModels) {
        if (-not (Test-Path -LiteralPath $requiredModel)) {
            throw "Required packaged model is missing: $requiredModel"
        }
    }
}

$resolvedDesktopRoot = [System.IO.Path]::GetFullPath($desktopRoot)
$resolvedOutputRoot = [System.IO.Path]::GetFullPath($outputRoot)
if (-not $resolvedOutputRoot.StartsWith(
    $resolvedDesktopRoot + [System.IO.Path]::DirectorySeparatorChar,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Refusing to clean output outside the desktop build directory."
}
if (Test-Path -LiteralPath $resolvedOutputRoot) {
    Remove-Item -LiteralPath $resolvedOutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $resolvedOutputRoot | Out-Null
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $outputRoot "dist") `
    --workpath (Join-Path $outputRoot "work") `
    $specPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$executable = Join-Path $outputRoot "dist\NotesBuddyCompanion\NotesBuddyCompanion.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Packaged companion executable was not created."
}
$selfTestArguments = @("--self-test")
if ($RequireModels) {
    $selfTestArguments += "--require-models"
}
& $executable @selfTestArguments
if ($LASTEXITCODE -ne 0) {
    throw "Packaged companion self-test failed with exit code $LASTEXITCODE."
}

if (-not $SkipInstaller) {
    $innoCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path -LiteralPath $innoCompiler -PathType Leaf)) {
        throw "Inno Setup 6 was not found at $innoCompiler."
    }
    & $innoCompiler `
        "/DMyAppVersion=$Version" `
        "/O$releaseRoot" `
        (Join-Path $desktopRoot "installer\NotesBuddyCompanion.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
}

Write-Host "NotesBuddy companion build completed: $releaseRoot"
