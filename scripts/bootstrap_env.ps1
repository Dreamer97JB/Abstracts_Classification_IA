param(
    [string]$PythonPath = "",
    [switch]$Gpu,
    [switch]$AllowPython314
)

$ErrorActionPreference = "Stop"

function Get-PythonCandidate {
    param([string]$UserProvided)

    $candidates = @()

    if ($UserProvided) {
        $candidates += $UserProvided
    }

    $candidates += @(
        "C:\Users\PC\AppData\Local\Python\pythoncore-3.11-64\python.exe",
        "C:\Users\PC\AppData\Local\Python\pythoncore-3.12-64\python.exe",
        "C:\Users\PC\AppData\Local\Python\pythoncore-3.14-64\python.exe",
        "C:\Users\PC\AppData\Local\Python\bin\python.exe"
    )

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "No se encontro un Python utilizable. Instala Python 3.11 o pasa -PythonPath."
}

function Get-PythonVersion {
    param([string]$Executable)
    $versionText = & $Executable --version
    return ($versionText -replace "^Python\s+", "").Trim()
}

function Invoke-External {
    param(
        [string]$Description,
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo al $Description."
    }
}

$python = Get-PythonCandidate -UserProvided $PythonPath
$version = Get-PythonVersion -Executable $python

Write-Host "Python seleccionado: $python"
Write-Host "Version detectada: $version"

if ($version.StartsWith("3.14") -and -not $AllowPython314) {
    throw "Se detecto Python 3.14. Para este proyecto se recomienda Python 3.11/3.12. Si quieres continuar igual, usa -AllowPython314."
}

Invoke-External "crear la venv" $python @("-m", "venv", "--without-pip", ".venv")

$venvPython = Join-Path $PWD ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "No se encontro el interprete de la venv en .venv\Scripts\python.exe."
}

Invoke-External "instalar pip y herramientas base" $python @("-m", "pip", "--python", $venvPython, "install", "--upgrade", "pip", "setuptools", "wheel")
Invoke-External "instalar dependencias base" $python @("-m", "pip", "--python", $venvPython, "install", "-r", ".\requirements\base.txt")

if ($Gpu) {
    Invoke-External "instalar PyTorch CUDA 12.1" $python @("-m", "pip", "--python", $venvPython, "install", "--index-url", "https://download.pytorch.org/whl/cu121", "torch", "torchvision", "torchaudio")
} else {
    Invoke-External "instalar PyTorch CPU" $python @("-m", "pip", "--python", $venvPython, "install", "torch", "torchvision", "torchaudio")
}

Invoke-External "instalar stack ML" $python @("-m", "pip", "--python", $venvPython, "install", "-r", ".\requirements\ml-gpu-cu121.txt")
Invoke-External "descargar recursos de NLTK" $venvPython @("-c", "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)")

Write-Host ""
Write-Host "Entorno creado en .venv"
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activalo con:"
    Write-Host ".\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "No se detecto Activate.ps1. Usa directamente:"
    Write-Host ".\.venv\Scripts\python.exe"
}
