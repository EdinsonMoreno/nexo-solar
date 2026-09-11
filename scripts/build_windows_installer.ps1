param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

New-Item -ItemType Directory -Force -Path "dist/installers/windows" | Out-Null

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller --clean --noconfirm main_app.spec

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    $defaultIscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $defaultIscc) {
        $iscc = $defaultIscc
    }
}

if (-not $iscc) {
    throw "Inno Setup Compiler (ISCC.exe) no esta disponible. Instale Inno Setup 6 o use el workflow build-windows."
}

& $iscc "/DNexoSolarVersion=$Version" NexoSolarSetup.iss

$installer = "dist/installers/windows/NexoSolar-Setup-Windows-x64.exe"
if (-not (Test-Path $installer)) {
    throw "No se genero el instalador esperado: $installer"
}

Get-FileHash $installer -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path -Leaf $installer)" } |
    Set-Content "dist/installers/windows/SHA256SUMS.txt" -Encoding ascii

Write-Host "Instalador Windows generado en $installer"
