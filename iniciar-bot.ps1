# Sobe o Julio (bot Telegram) em background.
# Uso: .\iniciar-bot.ps1
# Ver logs:  Get-Content REDIS\agente-julio\data\julio.log -Wait -Tail 50
# Parar:     .\parar-bot.ps1

$ErrorActionPreference = "Stop"

$raiz = $PSScriptRoot
$pastaAgente = Join-Path $raiz "AGENTES\julio"
$pastaData = Join-Path $pastaAgente "data"
$arquivoPid = Join-Path $pastaData "julio.pid"
$arquivoLog = Join-Path $pastaData "julio.log"
$arquivoLogErro = Join-Path $pastaData "julio.err.log"

New-Item -ItemType Directory -Force -Path $pastaData | Out-Null

if (Test-Path $arquivoPid) {
    $pidExistente = Get-Content $arquivoPid -ErrorAction SilentlyContinue
    if ($pidExistente -and (Get-Process -Id $pidExistente -ErrorAction SilentlyContinue)) {
        Write-Host "Julio ja esta rodando (PID $pidExistente)."
        exit 0
    }
    Remove-Item $arquivoPid -Force
}

$processo = Start-Process -FilePath "python" `
    -ArgumentList "main_telegram.py" `
    -WorkingDirectory $pastaAgente `
    -RedirectStandardOutput $arquivoLog `
    -RedirectStandardError $arquivoLogErro `
    -WindowStyle Hidden `
    -PassThru

$processo.Id | Out-File -FilePath $arquivoPid -Encoding ascii -NoNewline

Write-Host "Julio subiu (PID $($processo.Id)). Log em $arquivoLog"
