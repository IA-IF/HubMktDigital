# Deploy do HubMktDigital na EC2: da push do que esta local, depois
# atualiza e reinicia o bot na instancia via SSH.
# Uso: .\infra\ec2\deploy.ps1

$ErrorActionPreference = "Stop"
$key = "C:/Users/rezen/.ssh/IF-AWS.pem"
$host_ = "ubuntu@54.94.213.217"

git push

# pull + reinstala deps + mata o processo antigo (tudo isso e rapido e sincrono)
$updateCmd = @'
set -e
cd ~/HubMktDigital
git pull
source .venv/bin/activate
export TMPDIR=~/tmp
pip install -q -r AGENTES/julio/requirements.txt
pkill -f main_telegram.py || true
'@
ssh -i $key $host_ $updateCmd

# sobe o processo novo via Start-Process: nao trava o script local esperando
# o SSH fechar a sessao (o processo remoto fica rodando via setsid/nohup,
# so o client ssh daqui demora a perceber que pode fechar a conexao).
$startCmd = "cd ~/HubMktDigital/AGENTES/julio && mkdir -p data && setsid nohup /home/ubuntu/HubMktDigital/.venv/bin/python3 main_telegram.py < /dev/null > data/julio.log 2> data/julio.err.log &"
Start-Process -FilePath "ssh" -ArgumentList "-i", $key, $host_, "`"$startCmd`"" -WindowStyle Hidden

Start-Sleep -Seconds 4
ssh -i $key $host_ "ps aux | grep main_telegram | grep -v grep; echo ---log---; tail -5 ~/HubMktDigital/AGENTES/julio/data/julio.log; echo ---err---; tail -5 ~/HubMktDigital/AGENTES/julio/data/julio.err.log"
