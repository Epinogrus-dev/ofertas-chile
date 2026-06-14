# Instala el self-hosted runner como SERVICIO de Windows (arranca solo, sobrevive
# reinicios, no depende de tu sesion). Ejecutar UNA vez como ADMINISTRADOR:
#
#   1. Menu inicio -> escribir "PowerShell" -> clic derecho -> "Ejecutar como administrador"
#   2. cd "C:\Users\samir\OneDrive\Escritorio\APP\ofertas-super"
#   3. powershell -ExecutionPolicy Bypass -File .\tools\instalar-runner-servicio.ps1
#
# Reemplaza el lanzador de inicio de sesion (mas fragil) por un servicio real.

$ErrorActionPreference = "Stop"
$RUNNER = "C:\actions-runner"
$REPO   = "https://github.com/Epinogrus-dev/ofertas-chile"

# --- 1. Verificar admin ---
$esAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
            ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $esAdmin) {
    Write-Host "ERROR: hay que ejecutarlo como Administrador (clic derecho -> Ejecutar como administrador)." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$RUNNER\config.cmd")) {
    Write-Host "ERROR: no encuentro el runner en $RUNNER" -ForegroundColor Red
    exit 1
}

# --- 2. Detener el runner que esté corriendo a mano (run.cmd) ---
Write-Host "Deteniendo runner en ejecucion (si lo hay)..."
Get-Process Runner.Listener,Runner.Worker -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# --- 3. Quitar el lanzador de inicio de sesion (lo reemplaza el servicio) ---
$vbs = Join-Path ([Environment]::GetFolderPath('Startup')) "github-runner-ofertas.vbs"
if (Test-Path $vbs) { Remove-Item $vbs -Force; Write-Host "Lanzador de inicio de sesion eliminado." }

# --- 4. Token de registro (via gh, ya autenticado como Epinogrus-dev) ---
Write-Host "Obteniendo token de registro..."
$tok = (gh api -X POST repos/Epinogrus-dev/ofertas-chile/actions/runners/registration-token --jq '.token').Trim()
if (-not $tok) { Write-Host "ERROR: no se obtuvo token (revisa 'gh auth status')." -ForegroundColor Red; exit 1 }

# --- 5. Reconfigurar como servicio (--runasservice instala el servicio Windows) ---
Write-Host "Configurando runner como servicio..."
Push-Location $RUNNER
& "$RUNNER\config.cmd" --url $REPO --token $tok --name "$env:COMPUTERNAME-cl" `
    --labels "self-hosted-cl" --work "_work" --runasservice --unattended --replace
Pop-Location

# --- 6. Verificar el servicio ---
Start-Sleep -Seconds 3
$svc = Get-Service | Where-Object { $_.Name -like "actions.runner.*" } | Select-Object -First 1
if ($svc) {
    Set-Service -Name $svc.Name -StartupType Automatic
    if ($svc.Status -ne "Running") { Start-Service -Name $svc.Name }
    Write-Host ""
    Write-Host "LISTO. Servicio '$($svc.Name)' = $((Get-Service $svc.Name).Status), arranque Automatico." -ForegroundColor Green
} else {
    Write-Host "AVISO: no se detecto el servicio. Revisa la salida de config.cmd arriba." -ForegroundColor Yellow
}
