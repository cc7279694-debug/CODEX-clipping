# Run only the already-installed OpenFilm CLI, isolating mutable state for this test.
# No npm, downloads, updates or automatic browser opening. All paths are process-only.
$workstationRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$resources = Join-Path $workstationRoot 'OpenFilm\resources'
$cli = Join-Path $resources 'app.asar.unpacked\node_modules\openfilm\bin\openfilm.mjs'
$ffmpeg = Join-Path $resources 'runtime\ffmpeg'
$browsers = Join-Path $resources 'runtime\ms-playwright'
$chromium = Join-Path $browsers 'chromium_headless_shell-1228\chrome-headless-shell-win64\chrome-headless-shell.exe'
$runtime = Join-Path $PSScriptRoot 'runtime'
foreach ($required in @($cli, (Join-Path $ffmpeg 'ffmpeg.exe'), (Join-Path $ffmpeg 'ffprobe.exe'), $chromium, (Join-Path $PSScriptRoot 'examples-offline.json'))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        Write-Error "Required local dependency is missing: $required"
        exit 1
    }
}
if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { Write-Error 'Node.js not found.'; exit 1 }
foreach ($directory in @('state','shared','projects','exports','saved','skills','temp','home','appdata','localappdata','trash','cache')) {
    $target = Join-Path $runtime $directory
    if (-not (Test-Path -LiteralPath $target -PathType Container)) { New-Item -ItemType Directory -Path $target -ErrorAction Stop | Out-Null }
}
$settings = @{
    OPENFILM_HOME = (Join-Path $runtime 'state')
    OPENFILM_SHARED_HOME = (Join-Path $runtime 'shared')
    OPENFILM_LIBRARY = (Join-Path $runtime 'projects')
    OPENFILM_EXPORTS = (Join-Path $runtime 'exports')
    OPENFILM_SAVED = (Join-Path $runtime 'saved')
    OPENFILM_SKILLS = (Join-Path $runtime 'skills')
    OPENFILM_TRASH_DIR = (Join-Path $runtime 'trash')
    OPENFILM_EXAMPLES_INDEX = (Join-Path $PSScriptRoot 'examples-offline.json')
    OPENFILM_NO_UPDATE_CHECK = '1'
    OPENFILM_NO_BROWSER = '1'
    PLAYWRIGHT_BROWSERS_PATH = $browsers
    TEMP = (Join-Path $runtime 'temp')
    TMP = (Join-Path $runtime 'temp')
    HOME = (Join-Path $runtime 'home')
    USERPROFILE = (Join-Path $runtime 'home')
    APPDATA = (Join-Path $runtime 'appdata')
    LOCALAPPDATA = (Join-Path $runtime 'localappdata')
    XDG_CACHE_HOME = (Join-Path $runtime 'cache')
    PATH = ($ffmpeg + [System.IO.Path]::PathSeparator + $env:PATH)
}
$previous = @{}
foreach ($setting in $settings.GetEnumerator()) {
    $previous[$setting.Key] = [Environment]::GetEnvironmentVariable($setting.Key, 'Process')
    [Environment]::SetEnvironmentVariable($setting.Key, $setting.Value, 'Process')
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & node.exe $cli @args
    $result = $LASTEXITCODE
} finally {
    Pop-Location
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
exit $result
