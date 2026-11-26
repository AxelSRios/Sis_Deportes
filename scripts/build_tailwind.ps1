# Compila Tailwind CSS a static/css/tailwind.css (sin Node).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\build_tailwind.ps1
#
# Descarga el binario oficial la primera vez y lo guarda en la carpeta temporal.
# Ejecutar este script cada vez que se agreguen o cambien clases de Tailwind en
# templates/, static/js/ o core/.

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:TEMP 'tailwindcss.exe'
$version = 'v3.4.17'

if (-not (Test-Path $bin)) {
    Write-Host "Descargando Tailwind CSS $version..."
    $url = "https://github.com/tailwindlabs/tailwindcss/releases/download/$version/tailwindcss-windows-x64.exe"
    Invoke-WebRequest -Uri $url -OutFile $bin -UseBasicParsing
}

Push-Location $raiz
try {
    & $bin -c tailwind.config.js -i assets/css/tailwind-input.css -o static/css/tailwind.css --minify
    if ($LASTEXITCODE -ne 0) { throw "Tailwind falló con código $LASTEXITCODE" }
    $tam = (Get-Item 'static/css/tailwind.css').Length
    Write-Host "Listo: static/css/tailwind.css ($tam bytes)"
    Write-Host "Recuerde ejecutar 'python manage.py collectstatic --noinput' antes de desplegar."
}
finally {
    Pop-Location
}
