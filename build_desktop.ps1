# Builds the standalone Windows app: dist\DataCoach\DataCoach.exe
# Usage: powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1
# Add -Zip to also produce dist\DataCoach-win64.zip

param(
    [switch]$Zip
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Run 'Setup Data Coach.bat' first."
    exit 1
}

Write-Host "Building DataCoach.exe..."
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean datacoach.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed."
    exit $LASTEXITCODE
}

$exe = Join-Path $root "dist\DataCoach\DataCoach.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but $exe is missing."
    exit 1
}

$size = [math]::Round((Get-ChildItem "dist\DataCoach" -Recurse -File |
    Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "Built: $exe ($size MB)"

if ($Zip) {
    $zipPath = Join-Path $root "dist\DataCoach-win64.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Write-Host "Zipping to $zipPath ..."
    Compress-Archive -Path "dist\DataCoach\*" -DestinationPath $zipPath -CompressionLevel Optimal
    $zipSize = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
    Write-Host "Zip: $zipPath ($zipSize MB)"
}
