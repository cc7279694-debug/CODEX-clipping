# Run the installed OpenFilm CLI with process-only workspace settings.
# With no arguments it prints the manual. Project operations use the current folder.
$openfilmRoot = Join-Path $PSScriptRoot 'OpenFilm\resources'
$openfilmCli = Join-Path $openfilmRoot 'app.asar.unpacked\node_modules\openfilm\bin\openfilm.mjs'
$ffmpegDirectory = Join-Path $openfilmRoot 'runtime\ffmpeg'
$browsersDirectory = Join-Path $openfilmRoot 'runtime\ms-playwright'
$workspaceDirectory = Join-Path $PSScriptRoot 'openfilm-workspace'

if (-not (Test-Path -LiteralPath $openfilmCli -PathType Leaf)) {
    Write-Error "OpenFilm CLI not found: $openfilmCli"
    exit 1
}
if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
    Write-Error 'Node.js was not found on PATH.'
    exit 1
}

$settings = @{
    OPENFILM_HOME = (Join-Path $workspaceDirectory 'state')
    OPENFILM_SHARED_HOME = (Join-Path $workspaceDirectory 'shared')
    OPENFILM_LIBRARY = (Join-Path $workspaceDirectory 'projects')
    OPENFILM_EXPORTS = (Join-Path $workspaceDirectory 'exports')
    OPENFILM_SAVED = (Join-Path $workspaceDirectory 'saved')
    OPENFILM_SKILLS = (Join-Path $workspaceDirectory 'skills')
    OPENFILM_NO_UPDATE_CHECK = '1'
    OPENFILM_NO_BROWSER = '1'
    PLAYWRIGHT_BROWSERS_PATH = $browsersDirectory
    PATH = ($ffmpegDirectory + [System.IO.Path]::PathSeparator + $env:PATH)
}
$previous = @{}
foreach ($setting in $settings.GetEnumerator()) {
    $previous[$setting.Key] = [Environment]::GetEnvironmentVariable($setting.Key, 'Process')
    [Environment]::SetEnvironmentVariable($setting.Key, $setting.Value, 'Process')
}
try {
    & node.exe $openfilmCli @args
    $openfilmExitCode = $LASTEXITCODE
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
exit $openfilmExitCode
