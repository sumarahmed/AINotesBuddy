param(
    [string]$Python = "python",
    [string]$Version = "2026.09.09",
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

# desktop_app.py's own COMPANION_VERSION constant is what the running
# companion reports to itself and to the website (GET /v1/companion,
# the tray window title, etc.) -- entirely separate from the installer's
# own AppVersion/-Version below. A real release shipped with these out of
# sync: the installer correctly said 2026.09.01, but the frozen Python
# code still reported the previous 2026.08.11 forever, since nothing
# updated this constant to match. Patch it into the frozen build here so
# a build's self-reported version always matches what it was built as;
# revert the working copy afterward so this stays a build-time-only
# transformation, not a change to tracked source.
$desktopAppPath = Join-Path $projectRoot "services\transcription\desktop_app.py"
$originalDesktopApp = Get-Content -LiteralPath $desktopAppPath -Raw
$versionPattern = 'COMPANION_VERSION = "[^"]*"'
if ($originalDesktopApp -notmatch $versionPattern) {
    throw "Could not find COMPANION_VERSION in desktop_app.py to synchronise with -Version."
}
$patchedDesktopApp = $originalDesktopApp -replace $versionPattern, "COMPANION_VERSION = `"$Version`""
Set-Content -LiteralPath $desktopAppPath -Value $patchedDesktopApp -NoNewline
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath (Join-Path $outputRoot "dist") `
        --workpath (Join-Path $outputRoot "work") `
        $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
} finally {
    Set-Content -LiteralPath $desktopAppPath -Value $originalDesktopApp -NoNewline
}

$executable = Join-Path $outputRoot "dist\NotesBuddyCompanion\NotesBuddyCompanion.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Packaged companion executable was not created."
}
$selfTestArguments = @("--self-test", "--require-server")
if ($RequireModels) {
    $selfTestArguments += "--require-models"
}
$selfTestStdout = Join-Path $outputRoot "self-test.stdout.log"
$selfTestStderr = Join-Path $outputRoot "self-test.stderr.log"
$selfTestProcess = Start-Process `
    -FilePath $executable `
    -ArgumentList $selfTestArguments `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $selfTestStdout `
    -RedirectStandardError $selfTestStderr
$selfTestCompleted = $selfTestProcess.WaitForExit(300000)
if (-not $selfTestCompleted) {
    Stop-Process -Id $selfTestProcess.Id -Force -ErrorAction SilentlyContinue
    throw "Packaged companion self-test exceeded the five-minute safety limit."
}
$selfTestProcess.WaitForExit()
$selfTestOutput = ""
if (Test-Path -LiteralPath $selfTestStdout) {
    $selfTestOutput = Get-Content -LiteralPath $selfTestStdout -Raw
    Write-Output $selfTestOutput
}
if (Test-Path -LiteralPath $selfTestStderr) {
    Get-Content -LiteralPath $selfTestStderr
}
try {
    $selfTestResult = $selfTestOutput | ConvertFrom-Json
} catch {
    throw "Packaged companion self-test did not return valid JSON."
}
if ($selfTestResult.status -ne "ok") {
    throw "Packaged companion self-test did not report success."
}
if ($null -ne $selfTestProcess.ExitCode -and $selfTestProcess.ExitCode -ne 0) {
    throw (
        "Packaged companion self-test failed with exit code " +
        "$($selfTestProcess.ExitCode)."
    )
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
