#!/usr/bin/env bash
# Sincroniza o codigo do HubMktDigital pra instancia EC2 e (re)inicia o bot.
# Repo local nao tem remote git -- por isso rsync direto, nao "git pull" na maquina.
#
# Uso:
#   infra/ec2/deploy.sh <ip-ou-host> [caminho-da-key]
#
# Ex.:
#   infra/ec2/deploy.sh 15.229.178.221 "C:/Users/rezen/.ssh/IF-AWS.pem"

set -euo pipefail

HOST="${1:?uso: deploy.sh <ip> [key]}"
KEY="${2:-C:/Users/rezen/.ssh/IF-AWS.pem}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE_DIR="/opt/hubmktdigital"

echo "==> Sincronizando codigo pra ubuntu@${HOST}:${REMOTE_DIR}"
rsync -az --delete \
  -e "ssh -i \"${KEY}\"" \
  --exclude ".git/" \
  --exclude "**/__pycache__/" \
  --exclude ".pytest_cache/" \
  --exclude "**/.venv/" \
  --exclude ".trae/" \
  --exclude ".trae-server/" \
  --exclude "mydata.md" \
  --exclude ".env" \
  --exclude "*.env" \
  "${REPO_ROOT}/" "ubuntu@${HOST}:${REMOTE_DIR}/"

echo "==> Copiando .env (fora do rsync acima -- segredo, tratado a parte)"
scp -i "${KEY}" "${REPO_ROOT}/.env" "ubuntu@${HOST}:${REMOTE_DIR}/.env"

echo "==> Criando/atualizando venv e instalando dependencias"
ssh -i "${KEY}" "ubuntu@${HOST}" bash -s <<'REMOTE'
set -euxo pipefail
cd /opt/hubmktdigital
python3 -m venv .venv --upgrade-deps
./.venv/bin/pip install -r REDIS/agente-julio/requirements.txt
sudo systemctl restart hubmkt-bot.service
sudo systemctl --no-pager status hubmkt-bot.service
REMOTE

echo "==> Deploy concluido. Logs: ssh -i \"${KEY}\" ubuntu@${HOST} 'journalctl -u hubmkt-bot -f'"
