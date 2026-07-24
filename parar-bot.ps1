# Para o Julio (bot Telegram) que foi subido com .\iniciar-bot.ps1
# Uso: .\parar-bot.ps1

$ErrorActionPreference = "Stop"

$raiz = $PSScriptRoot
$arquivoPid = Join-Path $raiz "AGENTES\julio\data\julio.pid"

if (-not (Test-Path $arquivoPid)) {
    Write-Host "Julio nao esta rodando (nenhum $arquivoPid encontrado)."
    exit 0
}

$processId = Get-Content $arquivoPid -ErrorAction SilentlyContinue
$processo = if ($processId) { Get-Process -Id $processId -ErrorAction SilentlyContinue } else { $null }

if (-not $processo) {
    Write-Host "PID $processId nao esta mais ativo. Limpando arquivo."
    Remove-Item $arquivoPid -Force
    exit 0
}

Stop-Process -Id $processId -Force
Remove-Item $arquivoPid -Force
Write-Host "Julio parado (PID $processId)."
