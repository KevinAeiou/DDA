$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Venv não encontrada. Execute .\scripts\setup_venv.ps1 primeiro."
}

$version = & $python -c "import dungeon_drop_analyzer as d; print(d.__version__)"
$dist = Join-Path $root "dist"
$app = Join-Path $dist "DungeonDropAnalyzer"
$exe = Join-Path $app "DungeonDropAnalyzer.exe"

& $python -m PyInstaller --noconfirm --clean --distpath $dist --workpath (Join-Path $root "build") (Join-Path $root "packaging\dda.spec")
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executável." }

$report = Join-Path $dist "self-check.json"
$dataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("dda-build-check-" + [guid]::NewGuid())
$env:QT_QPA_PLATFORM = "offscreen"
$env:DDA_DATA_DIR = $dataDir
$process = Start-Process -FilePath $exe -ArgumentList @("--self-check", "--output", $report) -Wait -PassThru
Remove-Item Env:QT_QPA_PLATFORM, Env:DDA_DATA_DIR -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
if ($process.ExitCode -ne 0) {
    Get-Content $report -ErrorAction SilentlyContinue
    throw "A autoverificação do executável falhou (código $($process.ExitCode))."
}

$zip = Join-Path $dist "DungeonDropAnalyzer-$version-win64.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $app -DestinationPath $zip
$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Executável: $exe"
Write-Host "Pacote: $zip ($sizeMb MB)"
