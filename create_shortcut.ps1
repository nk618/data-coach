# Creates a "Data Coach" shortcut on the desktop.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$launcher = Join-Path $root "launcher.pyw"

if (-not (Test-Path $pythonw)) {
    Write-Host "Set up the app first: run 'Setup Data Coach.bat'."
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop "Data Coach.lnk"))
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $launcher + '"'
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Data Coach - 21-day data analyst sprint"
$shortcut.Save()

Write-Host "Shortcut created on your Desktop: Data Coach"
