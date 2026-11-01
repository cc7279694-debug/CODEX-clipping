# Run only in a normal Windows PowerShell session; no administrator rights.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'AI-Video-Workspace\phase3b\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Write-Error 'BLOCKED: independent Python virtual environment was not found.'
    exit 1
}
$check = Get-Item -LiteralPath $python
while ($null -ne $check) {
    if (($check.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Write-Error 'BLOCKED: linked workspace or virtual environment path.'
        exit 1
    }
    if ($check.FullName -eq (Get-Item -LiteralPath $root).FullName) { break }
    $check = Get-Item -LiteralPath (Split-Path -Parent $check.FullName)
}
if ($null -eq $check) { Write-Error 'BLOCKED: invalid venv path.'; exit 1 }
& $python -I -c "import os,sys,pathlib; expected=os.path.normcase(os.path.abspath(os.path.join(sys.argv[1], 'AI-Video-Workspace','phase3b','.venv'))); cfg=pathlib.Path(sys.prefix,'pyvenv.cfg').read_text(encoding='utf-8').lower().replace(' ',''); assert sys.version_info[:3] == (3,12,4) and os.path.normcase(os.path.abspath(sys.prefix)) == expected and sys.prefix != sys.base_prefix and 'include-system-site-packages=false' in cfg" $root
if ($LASTEXITCODE -ne 0) {
    Write-Error 'BLOCKED: expected isolated Python 3.12.4.'
    exit 1
}
# ensurepip uses Python's bundled wheels, and writes to this venv only.
& $python -I -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pip') else 1)"
if ($LASTEXITCODE -ne 0) {
    & $python -I -m ensurepip
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'BLOCKED: could not prepare pip in the independent venv.'
        exit 1
    }
}
& $python -I (Join-Path $PSScriptRoot 'phase3c_prepare.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
