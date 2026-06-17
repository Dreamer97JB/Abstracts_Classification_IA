Write-Host "== Host ML Stack Check =="
Write-Host ""

Write-Host "[1] Windows"
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber | Format-List

Write-Host ""
Write-Host "[2] WSL"
try {
    wsl --status
} catch {
    Write-Host "WSL no disponible o no instalado."
}

Write-Host ""
Write-Host "[3] Python .venv"
if (Test-Path ".\.venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe -c "import sys, torch; print('python=' + sys.version.split()[0]); print('torch=' + torch.__version__); print('cuda=' + str(torch.cuda.is_available())); print('devices=' + str(torch.cuda.device_count()))"
} else {
    Write-Host ".venv no encontrada."
}

Write-Host ""
Write-Host "[4] NVIDIA / AMD paths"
Get-ChildItem 'C:\Program Files' -Directory | Where-Object {
    $_.Name -like 'NVIDIA*' -or $_.Name -like '*CUDA*' -or $_.Name -like 'AMD*'
} | Select-Object Name, FullName | Format-Table -AutoSize
